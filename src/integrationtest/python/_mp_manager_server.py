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

import threading
import trace
from multiprocessing.connection import Listener, Connection
from multiprocessing.managers import SyncManager, Server
from queue import Queue
from time import sleep

from gevent import spawn, monkey
from gevent.hub import wait, idle, get_hub
from gevent.util import format_run_info
from multiprocessing.util import get_logger

from geventmp.monkey import GEVENT_SAVED_MODULE_SETTINGS

REQUEST_COUNT = 10
QUEUE_SIZE = 3
QUEUE_DEPTH = 10


def idle_watcher():
    return
    logger = get_logger()
    prev = None
    while True:
        idle()
        current = format_run_info()
        if prev != current:
            prev = current
            logger.warning("\n".join(current))
            sleep(0.01)


def instrument_conn(conn):
    _old_send = conn.send
    _old_recv = conn.recv

    logger = get_logger()
    thread_name = threading.current_thread().name

    def new_send(obj):
        logger.info("%s: %s: sending %r", thread_name, conn.fileno(), obj)
        return _old_send(obj)

    def new_recv():
        obj = _old_recv()
        logger.info("%s: %s: received %r", thread_name, conn.fileno(), obj)
        return obj

    conn.send = new_send
    conn.recv = new_recv

    return conn


class TestServer(Server):
    def serve_client(self, conn):
        return super().serve_client(instrument_conn(conn))


class TestSyncManager(SyncManager):
    _Server = TestServer


def manager_init():
    spawn(idle_watcher)


def manager_process(addr, do_trace=False):
    if not monkey.saved[GEVENT_SAVED_MODULE_SETTINGS].get("geventmp"):
        raise RuntimeError("GeventMP patch has not run!")

    if do_trace:
        trace.Trace(count=0).runfunc(_manager_process, addr)
    else:
        _manager_process(addr)


def _manager_process(addr):
    logger = get_logger()
    spawn(idle_watcher)
    try:
        listener: Listener = Listener(addr, "AF_UNIX")

        with listener:
            manager = SyncManager()
            manager.start(manager_init)
            try:
                def process_queue(q: Queue, idx: int):
                    for val_idx in range(0, QUEUE_DEPTH):
                        put_string = f"Request #{idx}, Value #{val_idx}"
                        logger.info(f"**** Sending {put_string} on {q._id}")
                        q.put(put_string)
                        logger.info(f"**** Sent {put_string} on {q._id}")
                        sleep(0.05)

                    logger.info(f"**** Putting None in queue request #{idx} to empty on {q._id}")
                    q.put(None)
                    logger.info(f"**** Waiting for queue request #{idx} to empty on {q._id}")
                    q.join()
                    logger.info(f"**** All done with request #{idx} on {q._id}")

                def process_conn(conn: Connection, idx: int):
                    with conn:
                        logger.info(f"**** Accepted request #{idx}")
                        q: Queue = manager.Queue(QUEUE_SIZE)
                        logger.info(f"**** Passing request #{idx} queue {q._id}")
                        conn.send(q)
                        logger.info(f"**** Passed request #{idx} queue {q._id}")

                    spawn(process_queue, q, idx)

                for i in range(0, REQUEST_COUNT):
                    spawn(process_conn, listener.accept(), i)

                wait(timeout=60)
                # logger.warning("\n".join(format_run_info()))
            finally:
                manager.shutdown()
    finally:
        get_hub().destroy()
