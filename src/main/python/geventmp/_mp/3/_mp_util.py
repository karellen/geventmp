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

from multiprocessing.util import spawnv_passfds as _spawnv_passfd, register_after_fork

from gevent.os import _watch_child
from gevent.threading import local

__implements__ = ["spawnv_passfds", "ForkAwareLocal", "get_command_line_gevent_preamble"]
__target__ = "multiprocessing.util"


def get_command_line_gevent_preamble():
    from gevent.monkey import saved
    from gevent import config
    from gevent._config import ImportableSetting
    from geventmp.monkey import GEVENT_SAVED_MODULE_SETTINGS

    prog = 'from gevent import monkey; monkey.patch_all(**%r); ' + \
           'from gevent import config; [setattr(config, k, v) for k, v in %r.items()]; '

    args = (saved[GEVENT_SAVED_MODULE_SETTINGS],
            {k: getattr(config, k) for k in dir(config)
             if not isinstance(config.settings[k], ImportableSetting)})

    return prog, args


def spawnv_passfds(path, args, passfds):
    launch_args = args[2] if len(args) >= 3 else None
    if launch_args and launch_args.startswith("from multiprocessing.forkserver import main;"):
        prog, prog_args = get_command_line_gevent_preamble()
        prog += "%s"
        launch_args = prog % (prog_args + (launch_args,))
        args[2] = launch_args

    cpid = _spawnv_passfd(path, args, passfds)
    _watch_child(cpid)
    return cpid


class ForkAwareLocal(local):
    def __init__(self):
        register_after_fork(self, lambda obj: obj.__dict__.clear())

    def __reduce__(self):
        return type(self), ()
