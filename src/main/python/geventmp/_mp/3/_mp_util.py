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

_FORKSERVER_MAIN = "from multiprocessing.forkserver import main"


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
    # Every CPython that launches a forkserver does so as `[..., "-c", cmd]`, so the
    # command is whatever directly follows a bare `-c`. Its index is not dependable:
    # the interpreter flags preceding it vary (`-X -c` even emits a literal `-c` of its
    # own ahead of the real one), and gh-144503 (3.13.13, 3.14.4, 3.15) both prefixed the
    # command with `import sys; ` and appended sys.argv after it. Matching on content
    # alone is not enough either, since `-W` folds its whole filter into a single
    # argument that may quote the entry point. Failing here would silently leave the
    # forkserver unpatched, so require both the anchor and the content.
    for cmd_idx in range(1, len(args)):
        launch_args = args[cmd_idx]
        if args[cmd_idx - 1] == "-c" and isinstance(launch_args, str) and _FORKSERVER_MAIN in launch_args:
            prog, prog_args = get_command_line_gevent_preamble()
            prog += "%s"
            args[cmd_idx] = prog % (prog_args + (launch_args,))
            break

    cpid = _spawnv_passfd(path, args, passfds)
    _watch_child(cpid)
    return cpid


class ForkAwareLocal(local):
    def __init__(self):
        register_after_fork(self, lambda obj: obj.__dict__.clear())

    def __reduce__(self):
        return type(self), ()
