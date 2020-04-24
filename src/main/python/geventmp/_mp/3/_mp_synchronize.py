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

from multiprocessing.synchronize import SemLock as _SemLock, \
    Semaphore as _Semaphore, \
    BoundedSemaphore as _BoundedSemaphore, \
    Lock as _Lock, \
    RLock as _RLock

from gevent.hub import _get_hub_noargs as get_hub

__implements__ = ["SemLock", "Semaphore", "BoundedSemaphore", "Lock", "RLock"]
__target__ = "multiprocessing.synchronize"


class SemLock(_SemLock):
    def _make_methods(self):
        self._acquire = self._semlock.acquire
        self._release = self._semlock.release

    def acquire(self, *args, **kwargs):
        return get_hub().threadpool.apply(self._acquire, args, kwargs)

    def release(self, *args, **kwargs):
        self._release(*args, **kwargs)

    def __enter__(self):
        return get_hub().threadpool.apply(super().__enter__)


Semaphore = type("Semaphore", (SemLock,), dict(_Semaphore.__dict__))
BoundedSemaphore = type("BoundedSemaphore", (Semaphore,), dict(_BoundedSemaphore.__dict__))
Lock = type("Lock", (SemLock,), dict(_Lock.__dict__))
RLock = type("RLock", (SemLock,), dict(_RLock.__dict__))
