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
    # from gevent import config

    # config.monitor_thread = False
    # config.max_blocking_time = 0.05

    # from gevent import get_hub

    # get_hub().start_periodic_monitoring_thread()

from unittest import TestCase, main

from geventmp.monkey import GEVENT_SAVED_MODULE_SETTINGS

import trace

from gevent import spawn
from gevent.hub import wait, get_hub
from time import sleep
import multiprocessing as mp
from tempfile import mktemp
import sys
from _mp_manager_server import QUEUE_DEPTH, REQUEST_COUNT, manager_process, idle_watcher  # , instrument_conn

from queue import Queue
from multiprocessing.connection import Client
from multiprocessing.util import get_logger
import threading


class TestSyncManager(TestCase):
    def setUp(self):
        self.assertTrue(monkey.saved[GEVENT_SAVED_MODULE_SETTINGS].get("geventmp"),
                        "GeventMP patch has not run!")
        self.tearDown()
        self.addr = mktemp()

    def tearDown(self):
        get_hub().destroy()
        sys.stdout.flush()
        sys.stderr.flush()
        print("=====================")
        sys.stdout.flush()

    def test_manager_spawn(self):
        self.run_manager_test("spawn")

    def run_manager_test(self, context, do_trace=False, remote_trace=False):
        ctx = mp.get_context(context)
        # ctx.log_to_stderr(1)
        self.logger = get_logger()
        if do_trace:
            trace.Trace(count=0).runfunc(self._test_manager, ctx, remote_trace)
        else:
            self._test_manager(ctx, remote_trace)

    def _test_manager(self, ctx, remote_trace):
        p = ctx.Process(target=manager_process, args=(self.addr, remote_trace))
        p.start()

        sleep(3)

        results = []
        for i in range(0, REQUEST_COUNT):
            spawn(self.manager_client, results)

        spawn(idle_watcher)

        p.join(60)
        wait(timeout=5)

        self.assertFalse(p.is_alive())
        self.assertEqual(p.exitcode, 0)

        for result in results:
            self.assertIsInstance(result, str)
            self.assertRegex(result, r"Request #\d+, Value #\d+")

        self.assertEqual(len(results), QUEUE_DEPTH * REQUEST_COUNT)

    def manager_client(self, results):
        thread_name = threading.current_thread().name
        try:
            with Client(self.addr, "AF_UNIX") as client:
                queue: Queue = client.recv()
                self.logger.info(f"**** {thread_name}: received client queue {queue._id}")
                # queue.empty()
                # instrument_conn(queue._tls.connection)

            while True:
                self.logger.info(f"**** {thread_name}: receiving data on queue {queue._id}")
                data = queue.get()
                self.logger.info(f"**** {thread_name}: received data on queue {queue._id}: {data}")
                queue.task_done()
                self.logger.info(f"**** {thread_name}: task done on queue {queue._id}: {data}")
                if data is None:
                    return
                results.append(data)

        except Exception as e:
            results.append(e)


if __name__ == '__main__':
    main()
