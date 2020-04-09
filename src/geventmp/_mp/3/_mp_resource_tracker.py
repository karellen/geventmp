from multiprocessing.resource_tracker import ResourceTracker as _ResourceTracker

from gevent.os import make_nonblocking, nb_write

__implements__ = ["ResourceTracker", "_resource_tracker", "ensure_running",
                  "register", "unregister", "getfd"]
__target__ = "multiprocessing.resource_tracker"


class ResourceTracker(_ResourceTracker):
    def ensure_running(self):
        super().ensure_running()
        make_nonblocking(self._fd)

    def _send(self, cmd, name):
        self.ensure_running()
        msg = '{0}:{1}\n'.format(cmd, name).encode('ascii')
        if len(name) > 512:
            # posix guarantees that writes to a pipe of less than PIPE_BUF
            # bytes are atomic, and that PIPE_BUF >= 512
            raise ValueError('name too long')
        nbytes = nb_write(self._fd, msg)
        assert nbytes == len(msg)


_resource_tracker = ResourceTracker()
ensure_running = _resource_tracker.ensure_running
register = _resource_tracker.register
unregister = _resource_tracker.unregister
getfd = _resource_tracker.getfd
