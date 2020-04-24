#   -*- coding: utf-8 -*-
#   Copyright 2019 Karellen, Inc. and contributors
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

from __future__ import print_function

from multiprocessing.process import current_process

from gevent import monkey

if not getattr(current_process(), "_inheriting", False):
    monkey.patch_all()

from unittest import TestCase, main, skip
import trace

from time import sleep
from gevent import spawn
from gevent.util import assert_switches

try:
    from time import monotonic as clock
except ImportError:
    from time import clock

try:
    from unittest import skipIf
except ImportError:
    def _id(obj):
        return obj


    def skipIf(condition, reason):
        """
        Skip a test if the condition is true.
        """
        if condition:
            return skip(reason)
        return _id

from geventmp.monkey import GEVENT_SAVED_MODULE_SETTINGS

import multiprocessing as mp
import _mp_test_gevent
import _mp_test
import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
PY2_SKIP = (PY2, "Not applicable to Python 2")
PY3_SKIP = (PY3, "Not applicable to Python 3")


class TestMonkey(TestCase):
    def setUp(self):
        self.assertTrue(monkey.saved[GEVENT_SAVED_MODULE_SETTINGS].get("geventmp"),
                        "GeventMP patch has not run!")
        self.tearDown()

    def tearDown(self):
        sys.stdout.flush()
        sys.stderr.flush()
        print("=====================")
        sys.stdout.flush()

    @skipIf(*PY3_SKIP)
    def test_mp_queues(self):
        self.run_test_mp_queues_py2(_mp_test_gevent.test_queues)

    @skipIf(*PY3_SKIP)
    def test_mp_no_args_fork_v2(self):
        self.run_test_mp_no_args_py2(_mp_test_gevent.test_no_args)

    @skipIf(*PY2_SKIP)
    def test_mp_queues_fork(self):
        self.run_test_mp_queues("fork", _mp_test_gevent.test_queues)

    @skipIf(*PY2_SKIP)
    def test_mp_queues_spawn(self):
        self.run_test_mp_queues("spawn", _mp_test_gevent.test_queues)

    @skipIf(*PY2_SKIP)
    def test_mp_queues_forkserver(self):
        self.run_test_mp_queues("forkserver", _mp_test.test_queues)

    @skipIf(*PY2_SKIP)
    def test_mp_no_args_fork(self):
        self.run_test_mp_no_args("fork", _mp_test_gevent.test_no_args)

    @skipIf(*PY2_SKIP)
    def test_mp_no_args_spawn(self):
        self.run_test_mp_no_args("spawn", _mp_test_gevent.test_no_args)

    @skipIf(*PY2_SKIP)
    def test_mp_no_args_forkserver(self):
        self.run_test_mp_no_args("forkserver", _mp_test.test_no_args)

    def run_test_mp_no_args_py2(self, func, do_trace=False):
        p = mp.Process(target=func)
        if do_trace:
            trace.Trace(count=0).runfunc(self._test_mp_no_args, p)
        else:
            self._test_mp_no_args(p)

    def run_test_mp_no_args(self, context, func, do_trace=False):
        ctx = mp.get_context(context)
        p = ctx.Process(target=func)
        if do_trace:
            trace.Trace(count=0).runfunc(self._test_mp_no_args, p)
        else:
            self._test_mp_no_args(p)

    def _test_mp_no_args(self, p):
        async_counter = [0]

        def count():
            while True:
                sleep(0.01)
                async_counter[0] += 1

        task = spawn(count)
        p.start()
        self.assertTrue(p.pid > 0)

        with assert_switches():
            start = clock()
            p.join(5)
            end = clock()
            print("Waited for child to die for %f" % (end - start))
        task.kill()

        # This is to ensure a greenlet flip
        sleep(0.001)

        self.assertFalse(p.is_alive())
        self.assertEqual(p.exitcode, 10)
        print("Async counter counted to %d" % async_counter[0])
        self.assertGreater(async_counter[0], 0)

    def run_test_mp_queues_py2(self, func, do_trace=False):
        # mp.log_to_stderr(1)
        r_q = mp.Queue()
        w_q = mp.Queue()
        p = mp.Process(target=func, args=(w_q, r_q))
        if do_trace:
            trace.Trace(count=0).runfunc(self._test_mp_queues, p, r_q, w_q)
        else:
            self._test_mp_queues(p, r_q, w_q)

    def run_test_mp_queues(self, context, func, do_trace=False):
        ctx = mp.get_context(context)
        # ctx.log_to_stderr(1)
        r_q = ctx.Queue()
        w_q = ctx.Queue()
        p = ctx.Process(target=func, args=(w_q, r_q))
        if do_trace:
            trace.Trace(count=0).runfunc(self._test_mp_queues, p, r_q, w_q)
        else:
            self._test_mp_queues(p, r_q, w_q)

    def _test_mp_queues(self, p, r_q, w_q):
        async_counter = [0]

        def count():
            while True:
                sleep(0.01)
                async_counter[0] += 1

        task = spawn(count)

        p.start()
        self.assertTrue(p.pid > 0)
        with assert_switches():
            w_q.put("master", timeout=5)
        with assert_switches():
            self.assertEqual(r_q.get(timeout=5), "test_queues")
        with assert_switches():
            start = clock()
            p.join(5)
            end = clock()
            print("Waited for child to die for %f" % (end - start))
        task.kill()

        # This is to ensure a greenlet flip
        sleep(0.001)

        self.assertEqual(p.exitcode, 10)
        self.assertFalse(p.is_alive())
        print("Async counter counted to %d" % async_counter[0])
        self.assertGreater(async_counter[0], 0)


if __name__ == '__main__':
    main()
