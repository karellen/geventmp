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

from gevent.os import _watch_child
from gevent.threading import local
from multiprocessing.util import spawnv_passfds as _spawnv_passfd, register_after_fork

__implements__ = ["spawnv_passfds", "ForkAwareLocal"]
__target__ = "multiprocessing.util"


def spawnv_passfds(path, args, passfds):
    cpid = _spawnv_passfd(path, args, passfds)
    _watch_child(cpid)
    return cpid


class ForkAwareLocal(local):
    def __init__(self):
        register_after_fork(self, lambda obj: obj.__dict__.clear())

    def __reduce__(self):
        return type(self), ()
