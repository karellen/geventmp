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
import sys
from multiprocessing import context
from multiprocessing import reduction
from multiprocessing import util
from multiprocessing.synchronize import SemLock as _SemLock, \
    Semaphore as _Semaphore, \
    BoundedSemaphore as _BoundedSemaphore, \
    Lock as _Lock, \
    RLock as _RLock, \
    SEMAPHORE, SEM_VALUE_MAX
from threading import get_ident

from gevent.hub import _get_hub_noargs as get_hub
from gevent.os import nb_read, nb_write, _read, ignored_errors
from gevent.timeout import with_timeout, Timeout

__implements__ = ["SemLock", "Semaphore", "BoundedSemaphore", "Lock", "RLock"]
__target__ = "multiprocessing.synchronize"

_BUF_ONE = (1).to_bytes(8, sys.byteorder, signed=False)


class SemLockEventFd:
    def __init__(self, kind, value, maxvalue, *, ctx=None):
        self.kind = kind
        self.maxvalue = maxvalue
        self.fd = os.eventfd(value, os.EFD_CLOEXEC | os.EFD_NONBLOCK | os.EFD_SEMAPHORE)
        util.debug(f"created semlock with fd {self.fd}")
        self._reset()

    def _reset(self):
        self._fd_path = f"/proc/{os.getpid()}/fdinfo/{self.fd}"
        self._semlock = self
        self.count = 0
        self.tid = None

    def __del__(self):
        try:
            os.close(self.fd)
        except OSError:
            pass

    def acquire(self, block=True, timeout=None):
        if self.kind != SEMAPHORE and self._is_mine():
            self.count += 1
            return True

        if block:
            if timeout is not None:
                try:
                    with_timeout(timeout, nb_read, self.fd, 8)
                except Timeout:
                    return False
            else:
                nb_read(self.fd, 8)
        else:
            try:
                _read(self.fd, 8)
            except OSError as e:
                if e.errno not in ignored_errors:
                    raise
                return False

        self.count += 1
        self.tid = get_ident()
        return True

    def release(self):
        if self.kind != SEMAPHORE:
            if not self._is_mine():
                raise AssertionError("attempt to release recursive lock not owned by thread")

            if self.count > 1:
                self.count -= 1
                return
        elif self.maxvalue != SEM_VALUE_MAX:
            count = self._get_value()
            if count >= self.maxvalue:
                raise ValueError("semaphore or lock released too many times")

        nb_write(self.fd, _BUF_ONE)
        self.count -= 1

    def _get_value(self):
        with open(self._fd_path, "rb") as f:
            for line in f:
                if line.startswith(b"eventfd-count:"):
                    return int(line[14:].strip())

    def _count(self):
        return self.count

    def _is_mine(self):
        return self.count > 0 and self.tid == get_ident()

    def _is_zero(self):
        return self._get_value() == 0

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *args):
        self.release()

    def __getstate__(self):
        context.assert_spawning(self)
        df = reduction.DupFd(self.fd)
        return df, self.kind, self.maxvalue

    def __setstate__(self, state):
        df, kind, maxvalue = state
        fd = df.detach()
        util.debug(f'recreated blocker with fd {fd}')
        self.kind = kind
        self.maxvalue = maxvalue
        self.fd = fd
        self._reset()


class SemLockSem(_SemLock):
    def _make_methods(self):
        self._acquire = self._semlock.acquire
        self._release = self._semlock.release

    def acquire(self, *args, **kwargs):
        if self._semlock.kind != SEMAPHORE:
            return self._acquire(*args, **kwargs)
        return get_hub().threadpool.apply(self._acquire, args, kwargs)

    def release(self, *args, **kwargs):
        self._release(*args, **kwargs)

    def __enter__(self):
        if self._semlock.kind != SEMAPHORE:
            return super().__enter__()
        return get_hub().threadpool.apply(super().__enter__)


try:
    os.eventfd
    SemLock = SemLockEventFd
except AttributeError:
    SemLock = SemLockSem

Semaphore = type("Semaphore", (SemLock,), dict(_Semaphore.__dict__))
BoundedSemaphore = type("BoundedSemaphore", (Semaphore,), dict(_BoundedSemaphore.__dict__))
Lock = type("Lock", (SemLock,), dict(_Lock.__dict__))
RLock = type("RLock", (SemLock,), dict(_RLock.__dict__))
