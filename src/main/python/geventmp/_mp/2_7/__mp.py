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

import _multiprocessing as _mp
import multiprocessing.reduction as mp_r
import sys

from gevent.hub import _get_hub_noargs as get_hub


def recvfd(sockfd):
    return get_hub().threadpool.apply(_mp.recvfd, (sockfd,))


def sendfd(sockfd, fd):
    return get_hub().threadpool.apply(_mp.sendfd, (sockfd, fd))


SemLock = _mp.SemLock
address_of_buffer = _mp.address_of_buffer
flags = _mp.flags


class Connection():
    def __init__(self, handle, readable=True, writable=True):
        self._conn = _mp.Connection(handle, readable, writable)

    def poll(self, *args, **kwargs):
        return get_hub().threadpool.apply(self._conn.poll, args, kwargs)

    def recv(self):
        return get_hub().threadpool.apply(self._conn.recv)

    def recv_bytes(self, *args, **kwargs):
        return get_hub().threadpool.apply(self._conn.recv_bytes, args, kwargs)

    def recv_bytes_into(self, *args, **kwargs):
        return get_hub().threadpool.apply(self._conn.recv_bytes_into, args, kwargs)

    def send(self, *args, **kwargs):
        return get_hub().threadpool.apply(self._conn.send, args, kwargs)

    def send_bytes(self, *args, **kwargs):
        return get_hub().threadpool.apply(self._conn.send_bytes, args, kwargs)

    def close(self):
        return get_hub().threadpool.apply(self._conn.close)

    def fileno(self):
        return self._conn.fileno()

    def __repr__(self):
        return self._conn.__repr__()

    @property
    def closed(self):
        return self._conn.closed

    @property
    def readable(self):
        return self._conn.readable

    @property
    def writable(self):
        return self._conn.writable


if sys.platform == 'win32':
    PipeConnection = type("PipeConnection", (object,), dict(Connection.__dict__))
    del Connection
    mp_r.ForkingPickler.register(PipeConnection, mp_r.reduce_pipe_connection)
else:
    mp_r.ForkingPickler.register(Connection, mp_r.reduce_connection)
