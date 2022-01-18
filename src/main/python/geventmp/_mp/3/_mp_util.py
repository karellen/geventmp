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

from gevent.hub import _get_hub_noargs as get_hub
from gevent.threading import local
from multiprocessing.util import spawnv_passfds as _spawnv_passfd, register_after_fork

__implements__ = ["spawnv_passfds", "ForkAwareLocal"]
__target__ = "multiprocessing.util"


def spawnv_passfds(path, args, passfds):
    return get_hub().threadpool.apply(_spawnv_passfd, (path, args, passfds))


class ForkAwareLocal(local):
    def __init__(self):
        register_after_fork(self, lambda obj: obj.__dict__.clear())

    def __reduce__(self):
        return type(self), ()
