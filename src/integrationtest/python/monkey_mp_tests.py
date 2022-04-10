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

from multiprocessing.process import current_process

from gevent import monkey

if not getattr(current_process(), "_inheriting", False):
    monkey.patch_all()

# from multiprocessing.util import log_to_stderr
# log_to_stderr(1)

from unittest import TestCase, main
import trace

from time import sleep, monotonic as clock
from gevent import spawn, idle
from gevent.util import assert_switches

from geventmp.monkey import GEVENT_SAVED_MODULE_SETTINGS

import multiprocessing as mp
from multiprocessing.util import get_logger
import _mp_test_gevent
import _mp_test
import sys

logger = get_logger()


class TestMonkey(TestCase):
    def setUp(self):
        self.assertTrue(monkey.saved[GEVENT_SAVED_MODULE_SETTINGS].get("geventmp"),
                        "GeventMP patch has not run!")
        self.tearDown()

    def tearDown(self):
        sys.stdout.flush()
        sys.stderr.flush()
        logger.info("=====================")
        sys.stdout.flush()

    def test_mp_queues_fork(self):
        self.run_test_mp_queues("fork", _mp_test_gevent.test_queues)

    def test_mp_queues_spawn(self):
        self.run_test_mp_queues("spawn", _mp_test_gevent.test_queues)

    def test_mp_jqueues_fork(self):
        self.run_test_mp_jqueues("fork", _mp_test_gevent.test_queues)

    def test_mp_jqueues_spawn(self):
        self.run_test_mp_jqueues("spawn", _mp_test_gevent.test_queues)

    def test_mp_no_args_fork(self):
        self.run_test_mp_no_args("fork", _mp_test_gevent.test_no_args)

    def test_mp_no_args_spawn(self):
        self.run_test_mp_no_args("spawn", _mp_test_gevent.test_no_args)

    def test_mp_no_args_forkserver(self):
        self.run_test_mp_no_args("forkserver", _mp_test.test_no_args)

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
                idle()
                async_counter[0] += 1
                sleep(0.001)

        task = spawn(count)
        p.start()
        self.assertTrue(p.pid > 0)

        with assert_switches():
            start = clock()
            p.join(15)
            end = clock()
            logger.info("Waited for child to die for %f" % (end - start))
        task.kill()

        # This is to ensure a greenlet flip
        sleep(0.001)

        logger.info(f"checking {p} is alive")
        self.assertFalse(p.is_alive())
        self.assertEqual(p.exitcode, 10)
        logger.info("Async counter counted to %d" % async_counter[0])
        self.assertGreater(async_counter[0], 0)

    def run_test_mp_queues(self, context, func, do_trace=False):
        ctx = mp.get_context(context)
        r_q = ctx.Queue()
        w_q = ctx.Queue()
        p = ctx.Process(target=func, args=(w_q, r_q))
        if do_trace:
            trace.Trace(count=0).runfunc(self._test_mp_queues, p, r_q, w_q)
        else:
            self._test_mp_queues(p, r_q, w_q)

    def run_test_mp_jqueues(self, context, func, do_trace=False):
        ctx = mp.get_context(context)
        r_q = ctx.JoinableQueue()
        w_q = ctx.JoinableQueue()
        p = ctx.Process(target=func, args=(w_q, r_q))
        if do_trace:
            trace.Trace(count=0).runfunc(self._test_mp_jqueues, p, r_q, w_q)
        else:
            self._test_mp_jqueues(p, r_q, w_q)

    def _test_mp_queues(self, p, r_q, w_q):
        async_counter = [0]

        def count():
            while True:
                idle()
                async_counter[0] += 1
                sleep(0.001)

        task = spawn(count)

        p.start()
        self.assertTrue(p.pid > 0)
        with assert_switches():
            w_q.put("master", timeout=5)
        with assert_switches():
            self.assertEqual(r_q.get(timeout=5), "test_queues")
        with assert_switches():
            start = clock()
            p.join(15)
            end = clock()
            logger.info("Waited for child to die for %f" % (end - start))
        task.kill()

        # This is to ensure a greenlet flip
        sleep(0.001)

        logger.info(f"checking {p} is alive")
        self.assertFalse(p.is_alive())
        self.assertEqual(p.exitcode, 10)
        logger.info("Async counter counted to %d" % async_counter[0])
        self.assertGreater(async_counter[0], 0)

    def _test_mp_jqueues(self, p, r_q, w_q):
        async_counter = [0]

        def count():
            while True:
                idle()
                async_counter[0] += 1
                sleep(0.001)

        task = spawn(count)

        p.start()
        self.assertTrue(p.pid > 0)

        with assert_switches():
            w_q.put("master", timeout=5)
        with assert_switches():
            self.assertEqual(r_q.get(timeout=5), "test_queues")
        r_q.task_done()

        with assert_switches():
            start = clock()
            p.join(15)
            end = clock()
            logger.info("Waited for child to die for %f" % (end - start))
        task.kill()

        # This is to ensure a greenlet flip
        sleep(0.001)

        logger.info(f"checking {p} is alive")
        self.assertFalse(p.is_alive())
        self.assertEqual(p.exitcode, 10)
        logger.info("Async counter counted to %d" % async_counter[0])
        self.assertGreater(async_counter[0], 0)


if __name__ == '__main__':
    main()
