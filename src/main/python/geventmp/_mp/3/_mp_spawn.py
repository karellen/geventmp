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

import sys
from multiprocessing import spawn, util

__implements__ = ["get_command_line"]
__target__ = "multiprocessing.spawn"


def get_command_line(**kwds):
    '''
    Returns prefix of command line used for spawning a child process
    '''
    if getattr(sys, 'frozen', False):
        return ([sys.executable, '--multiprocessing-fork'] +
                ['%s=%r' % item for item in kwds.items()])
    else:
        from gevent.monkey import saved
        from gevent import config
        from gevent._config import ImportableSetting
        from geventmp.monkey import GEVENT_SAVED_MODULE_SETTINGS

        prog = 'from gevent import monkey; monkey.patch_all(**%r); ' + \
               'from gevent import config; [setattr(config, k, v) for k, v in %r.items()]; ' + \
               'from multiprocessing.spawn import spawn_main; ' + \
               'spawn_main(%s);'

        prog %= (saved[GEVENT_SAVED_MODULE_SETTINGS],
                 {k: getattr(config, k) for k in dir(config)
                  if not isinstance(config.settings[k], ImportableSetting)},
                 ', '.join('%s=%r' % item for item in kwds.items()))

        opts = util._args_from_interpreter_flags()
        return [spawn._python_exe] + opts + ['-c', prog, '--multiprocessing-fork']
