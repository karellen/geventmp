#   -*- coding: utf-8 -*-
#   Copyright 2022 Karellen, Inc. and contributors
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

from geventmp.monkey import GEVENT_SAVED_MODULE_SETTINGS

import multiprocessing as mp
from multiprocessing.util import get_logger
import sys
from time import monotonic

logger = get_logger()


class TestSynchronizers(TestCase):
    def setUp(self):
        self.assertTrue(monkey.saved[GEVENT_SAVED_MODULE_SETTINGS].get("geventmp"),
                        "GeventMP patch has not run!")
        self.tearDown()

    def tearDown(self):
        sys.stdout.flush()
        sys.stderr.flush()
        logger.info("=====================")
        sys.stdout.flush()

    def test_semaphore_fork(self):
        self._test_semaphore("fork")

    def test_semaphore_spawn(self):
        self._test_semaphore("spawn")

    def test_semaphore_forkserver(self):
        self._test_semaphore("forkserver")

    def test_bounded_semaphore_fork(self):
        self._test_bounded_semaphore("fork")

    def test_bounded_semaphore_spawn(self):
        self._test_bounded_semaphore("spawn")

    def test_bounded_semaphore_forkserver(self):
        self._test_bounded_semaphore("forkserver")

    def _test_semaphore(self, ctx_name):
        ctx = mp.get_context(ctx_name)
        s = ctx.Semaphore()
        self.assertEqual(s.get_value(), 1)
        self.assertEqual(s._semlock._count(), 0)
        repr(s)

        s.release()
        self.assertEqual(s.get_value(), 2)
        self.assertEqual(s._semlock._count(), -1)
        repr(s)

        self.assertTrue(s.acquire())
        self.assertEqual(s.get_value(), 1)
        self.assertEqual(s._semlock._count(), 0)
        repr(s)

        self.assertTrue(s.acquire())
        self.assertEqual(s.get_value(), 0)
        self.assertEqual(s._semlock._count(), 1)
        repr(s)

        self.assertFalse(s.acquire(block=False))
        self.assertEqual(s.get_value(), 0)
        self.assertEqual(s._semlock._count(), 1)
        repr(s)

        start = monotonic()
        self.assertFalse(s.acquire(timeout=1))
        duration = monotonic() - start
        self.assertGreater(duration, 1)
        self.assertLess(duration, 3)
        s.release()
        self.assertEqual(s.get_value(), 1)
        self.assertEqual(s._semlock._count(), 0)

    def _test_bounded_semaphore(self, ctx_name):
        ctx = mp.get_context(ctx_name)
        s = ctx.BoundedSemaphore(2)
        repr(s)

        self.assertEqual(s.get_value(), 2)
        self.assertEqual(s._semlock._count(), 0)

        self.assertTrue(s.acquire())
        self.assertEqual(s.get_value(), 1)
        self.assertEqual(s._semlock._count(), 1)
        repr(s)

        self.assertTrue(s.acquire())
        self.assertEqual(s.get_value(), 0)
        self.assertEqual(s._semlock._count(), 2)
        repr(s)

        self.assertFalse(s.acquire(block=False))
        self.assertEqual(s.get_value(), 0)
        self.assertEqual(s._semlock._count(), 2)
        repr(s)

        start = monotonic()
        self.assertFalse(s.acquire(timeout=1))
        duration = monotonic() - start
        self.assertGreater(duration, 1)
        self.assertLess(duration, 3)
        s.release()
        self.assertEqual(s.get_value(), 1)
        self.assertEqual(s._semlock._count(), 1)
        s.release()
        self.assertEqual(s.get_value(), 2)
        self.assertEqual(s._semlock._count(), 0)
        with self.assertRaises(ValueError):
            s.release()


if __name__ == '__main__':
    main()
