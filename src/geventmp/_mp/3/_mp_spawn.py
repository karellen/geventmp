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

        prog = 'from gevent import monkey; monkey.patch_all(%s); ' + \
               'from multiprocessing.spawn import spawn_main; ' + \
               'spawn_main(%s);'

        prog %= (', '.join('%s=%r' % item for item in saved["_gevent_saved_patch_all"].items()),
                 ', '.join('%s=%r' % item for item in kwds.items()))
        opts = util._args_from_interpreter_flags()
        return [spawn._python_exe] + opts + ['-c', prog, '--multiprocessing-fork']
