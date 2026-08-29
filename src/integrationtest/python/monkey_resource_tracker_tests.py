#   -*- coding: utf-8 -*-
#   Copyright 2026 Karellen, Inc. and contributors
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

from multiprocessing.process import current_process

from gevent import monkey

if not getattr(current_process(), "_inheriting", False):
    monkey.patch_all()

import os
from unittest import TestCase, main, skipUnless

from gevent import joinall, sleep, spawn

from multiprocessing.resource_tracker import _resource_tracker

# Only these interpreters hold the tracker lock across the write; older ones do the
# `nb_write` from `_send`, outside the lock, and cannot exhibit the problem.
HAS_WRITE = hasattr(_resource_tracker, "_write")

PIPE_FILLER = b"x" * 4096


def fill(fd):
    """Fill a pipe so that the next write to it has to park in the hub."""
    written = 0
    while True:
        try:
            written += os.write(fd, PIPE_FILLER)
        except BlockingIOError:
            return written


def drain(fd):
    """Empty a non-blocking pipe so a parked write can make progress."""
    while True:
        try:
            if not os.read(fd, 65536):
                return
        except BlockingIOError:
            return


@skipUnless(HAS_WRITE, "interpreter does not write under the resource tracker lock")
class ResourceTrackerLockTest(TestCase):
    def test_lock_is_greenlet_aware(self):
        # A native RLock is owned per OS thread, so a second greenlet would acquire it
        # rather than wait, and every reentrancy check upstream makes would misfire.
        lock = _resource_tracker._lock
        order = []
        observed = []

        def holder():
            with lock:
                sleep(0.05)
                order.append("holder")

        def contender():
            sleep(0.01)
            observed.append(lock._recursion_count())
            with lock:
                order.append("contender")

        joinall([spawn(holder), spawn(contender)], timeout=10, raise_error=True)

        self.assertEqual(observed, [0], "lock appeared held by the contending greenlet")
        self.assertEqual(order, ["holder", "contender"])

    @skipUnless(hasattr(_resource_tracker, "_after_fork_in_child"),
                "interpreter has no ResourceTracker._after_fork_in_child")
    def test_swapped_lock_survives_a_fork(self):
        # The at-fork hook geventmp registers reads `_lock` at call time, so it has to
        # cope with the greenlet-aware lock installed after patching rather than the
        # native one the tracker was built with.
        lock = _resource_tracker._lock
        with lock:
            with lock:
                self.assertEqual(lock._recursion_count(), 2)
                pid = os.fork()
                if pid == 0:
                    try:
                        os._exit(0 if lock._recursion_count() == 0 else 1)
                    except BaseException:
                        os._exit(99)
            _, status = os.waitpid(pid, 0)

        self.assertEqual(os.waitstatus_to_exitcode(status), 0,
                         "at-fork hook did not reinitialize the greenlet-aware lock")

    def test_parked_write_does_not_break_a_concurrent_probe(self):
        # `_write` yields while `_ensure_running_and_write` holds the lock. With a
        # native lock the probing greenlet re-enters instead of waiting, sees
        # `_recursion_count() > 1` and takes a ReentrantCallError.
        r, w = os.pipe()
        original_fd = _resource_tracker._fd
        try:
            os.set_blocking(w, False)
            os.set_blocking(r, False)
            self.assertGreater(fill(w), 0)
            _resource_tracker._fd = w

            errors = []
            finished = []

            def writer():
                try:
                    _resource_tracker._send("REGISTER", "/psm_parked", "shared_memory")
                    finished.append("writer")
                except BaseException as e:
                    errors.append(("writer", repr(e)))

            def prober():
                sleep(0.05)
                try:
                    _resource_tracker.ensure_running()
                    finished.append("prober")
                except BaseException as e:
                    errors.append(("prober", repr(e)))

            greenlets = [spawn(writer), spawn(prober)]
            sleep(0.2)
            drain(r)
            joinall(greenlets, timeout=10)

            self.assertEqual(errors, [])
            self.assertEqual(sorted(finished), ["prober", "writer"])
        finally:
            _resource_tracker._fd = original_fd
            os.close(r)
            os.close(w)


if __name__ == '__main__':
    main()
