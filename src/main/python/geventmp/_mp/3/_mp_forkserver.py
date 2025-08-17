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

import os
import signal
from multiprocessing.forkserver import ForkServer as _ForkServer, SIGNED_STRUCT

from gevent.os import make_nonblocking, nb_read, nb_write

__implements__ = ["ForkServer", "_forkserver", "ensure_running", "_serve_one",
                  "get_inherited_fds", "connect_to_new_process",
                  "set_forkserver_preload", "read_signed", "write_signed"]
__target__ = "multiprocessing.forkserver"


class ForkServer(_ForkServer):
    def connect_to_new_process(self, fds):
        parent_r, parent_w = super().connect_to_new_process(fds)
        make_nonblocking(parent_r)
        make_nonblocking(parent_w)
        return parent_r, parent_w

    def ensure_running(self):
        super().ensure_running()
        make_nonblocking(self._forkserver_alive_fd)


def read_signed(fd):
    data = b''
    length = SIGNED_STRUCT.size
    while len(data) < length:
        s = nb_read(fd, length - len(data))
        if not s:
            raise EOFError('unexpected EOF')
        data += s
    return SIGNED_STRUCT.unpack(data)[0]


def write_signed(fd, n):
    msg = SIGNED_STRUCT.pack(n)
    while msg:
        nbytes = nb_write(fd, msg)
        if nbytes == 0:
            raise RuntimeError('should not get here')
        msg = msg[nbytes:]


def _serve_one(child_r, fds, unused_fds, handlers):
    from multiprocessing import resource_tracker, spawn
    # close unnecessary stuff and reset signal handlers
    signal.set_wakeup_fd(-1)
    for sig, val in handlers.items():
        signal.signal(sig, val)
    for fd in unused_fds:
        os.close(fd)

    (_forkserver._forkserver_alive_fd,
     resource_tracker._resource_tracker._fd,
     *_forkserver._inherited_fds) = fds
    make_nonblocking(_forkserver._forkserver_alive_fd)
    make_nonblocking(resource_tracker._resource_tracker._fd)
    for ifd in _forkserver._inherited_fds:
        make_nonblocking(ifd)

    # Run process object received over pipe
    parent_sentinel = os.dup(child_r)
    make_nonblocking(child_r)
    make_nonblocking(parent_sentinel)
    code = spawn._main(child_r, parent_sentinel)

    return code


_forkserver = ForkServer()
ensure_running = _forkserver.ensure_running
get_inherited_fds = _forkserver.get_inherited_fds
connect_to_new_process = _forkserver.connect_to_new_process
set_forkserver_preload = _forkserver.set_forkserver_preload
