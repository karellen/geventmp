#   -*- coding: utf-8 -*-
#   Copyright 2020 Karellen, Inc. and contributors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
from importlib import import_module
from multiprocessing.resource_tracker import ResourceTracker as _ResourceTracker
from unittest import TestCase, main, skipUnless

from geventmp.monkey import _patch_mp_done

_mp_resource_tracker = import_module("geventmp._mp.3._mp_resource_tracker")

ResourceTracker = _mp_resource_tracker.ResourceTracker

# 3.13.7, 3.14.1 and 3.15 routed every tracker write through `_write`, at which point
# `_send` grew JSON/base64 name encoding and reentrant-call queueing that must not be
# reimplemented here. Older interpreters have neither.
HAS_WRITE = hasattr(_ResourceTracker, "_write")

NAMES = ["/psm_plain", "/psm_ünïcode", "/psm_with\nnewline"]


class TrackerOverrideShapeTest(TestCase):
    def test_detection_matches_the_running_interpreter(self):
        self.assertEqual(_mp_resource_tracker._HAS_WRITE, HAS_WRITE)

    def test_ensure_running_is_always_overridden(self):
        self.assertIn("ensure_running", ResourceTracker.__dict__)

    @skipUnless(HAS_WRITE, "interpreter has no ResourceTracker._write")
    def test_only_the_write_chokepoint_is_replaced(self):
        self.assertIn("_write", ResourceTracker.__dict__)

        # `_launch` needs no override: everything it triggers is written through
        # `_write`, which conditions the descriptor itself.
        self.assertNotIn("_launch", ResourceTracker.__dict__)

        # Overriding `_send` here would discard the name encoding CPython does above it.
        self.assertNotIn("_send", ResourceTracker.__dict__)
        self.assertIs(ResourceTracker._send, _ResourceTracker._send)

    @skipUnless(not HAS_WRITE, "interpreter has ResourceTracker._write")
    def test_legacy_interpreters_replace_send(self):
        self.assertIn("_send", ResourceTracker.__dict__)
        self.assertNotIn("_write", ResourceTracker.__dict__)


@skipUnless(HAS_WRITE, "interpreter has no ResourceTracker._write")
class TrackerWriteTest(TestCase):
    def test_write_makes_a_blocking_fd_nonblocking(self):
        # `nb_write` requires a non-blocking descriptor. On these interpreters `_send`
        # reaches `_write` through `_ensure_running_and_write`, never through our
        # `ensure_running`, so a tracker fd inherited from a non-gevent ancestor would
        # otherwise stay blocking and stall the hub once the pipe filled.
        r, w = os.pipe()
        try:
            self.assertTrue(os.get_blocking(w))

            tracker = ResourceTracker()
            tracker._fd = w
            tracker._write(b"REGISTER:/psm_plain:shared_memory\n")

            self.assertFalse(os.get_blocking(w))
            self.assertEqual(os.read(r, 4096), b"REGISTER:/psm_plain:shared_memory\n")
        finally:
            os.close(r)
            os.close(w)


class TrackerSendTest(TestCase):
    """Whatever the running CPython makes of a name, geventmp must make of it too."""

    def send(self, tracker, name):
        r, w = os.pipe()
        try:
            os.set_blocking(w, False)
            tracker._fd = w
            tracker.ensure_running = lambda: None
            try:
                tracker._send("REGISTER", name, "shared_memory")
            except Exception as e:
                return type(e), None
            return None, os.read(r, 4096)
        finally:
            os.close(r)
            os.close(w)

    def test_send_is_byte_identical_to_cpython(self):
        self.assertGreater(len(NAMES), 1)
        for name in NAMES:
            with self.subTest(name=name):
                expected_exc, expected_msg = self.send(_ResourceTracker(), name)
                actual_exc, actual_msg = self.send(ResourceTracker(), name)

                self.assertEqual(actual_exc, expected_exc)
                self.assertEqual(actual_msg, expected_msg)

    def test_plain_names_are_actually_written(self):
        exc, msg = self.send(ResourceTracker(), "/psm_plain")

        self.assertIsNone(exc)
        self.assertIn(b"REGISTER", msg)
        self.assertTrue(msg.endswith(b"\n"))


class PatchMpDoneTest(TestCase):
    def test_hook_leaves_a_tracker_it_did_not_install_alone(self):
        # This process never called `patch_all`, so `multiprocessing` still holds
        # CPython's tracker. Swapping the lock on a tracker geventmp did not install
        # would be reaching into a stranger's object.
        import multiprocessing.resource_tracker as stock

        self.assertIsNot(stock._resource_tracker, _mp_resource_tracker._resource_tracker)

        stock_lock = stock._resource_tracker._lock
        ours_lock = _mp_resource_tracker._resource_tracker._lock

        _patch_mp_done(None)

        self.assertIs(stock._resource_tracker._lock, stock_lock)
        self.assertIs(_mp_resource_tracker._resource_tracker._lock, ours_lock)


@skipUnless(hasattr(_ResourceTracker, "_after_fork_in_child"),
            "interpreter has no ResourceTracker._after_fork_in_child")
class TrackerAfterForkTest(TestCase):
    def test_our_tracker_lock_is_reinitialized_in_the_child(self):
        # gh-146313 registers the at-fork hook against the tracker instance that geventmp
        # replaces. Unless it is re-registered for ours, a child forked while the lock is
        # held inherits it held, and the next tracker write deadlocks or bails out as a
        # reentrant call.
        tracker = _mp_resource_tracker._resource_tracker
        lock = tracker._lock
        self.assertTrue(hasattr(lock, "_recursion_count"))

        with lock:
            with lock:
                self.assertEqual(lock._recursion_count(), 2)
                pid = os.fork()
                if pid == 0:
                    os._exit(0 if lock._recursion_count() == 0 else 1)
            _, status = os.waitpid(pid, 0)

        self.assertEqual(os.waitstatus_to_exitcode(status), 0,
                         "at-fork hook did not reinitialize the geventmp tracker lock")


if __name__ == "__main__":
    main()
