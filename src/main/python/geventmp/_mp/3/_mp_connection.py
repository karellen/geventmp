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

from io import BytesIO
from multiprocessing.connection import (reduce_connection,
                                        _ConnectionBase as __ConnectionBase,
                                        Connection as _Connection)

import multiprocessing.reduction
from gevent.os import make_nonblocking, nb_read, nb_write
from gevent.selectors import GeventSelector

__implements__ = ["_ConnectionBase", "Connection", "_WaitSelector"]
__target__ = "multiprocessing.connection"


class _ConnectionBase(__ConnectionBase):
    def __init__(self, handle, readable=True, writable=True):
        super(_ConnectionBase, self).__init__(handle, readable, writable)
        make_nonblocking(handle)


class Connection(_ConnectionBase, _Connection):
    _write = nb_write
    _read = nb_read

    def _send(self, buf, write=_write):
        return super()._send(buf, write)

    def _recv(self, size, read=_read):
        return super()._recv(size, read)


def dump(obj, file, protocol=None):
    from pickletools import dis, optimize
    import sys
    import traceback
    from multiprocessing.util import get_logger

    out = BytesIO()
    multiprocessing.reduction.ForkingPickler(out, protocol).dump(obj)
    out_bytes = bytes(out.getbuffer())
    out_bytes = optimize(out_bytes)
    file.write(out_bytes)

    logger = get_logger()

    for h in logger.handlers:
        h.flush()

    dis(out_bytes, out=sys.stderr)
    logger.debug("".join(traceback.format_stack()))


# multiprocessing.reduction.dump = dump
multiprocessing.reduction.register(Connection, reduce_connection)
_WaitSelector = GeventSelector
