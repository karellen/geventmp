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

from multiprocessing.semaphore_tracker import SemaphoreTracker as _SemaphoreTracker

from gevent.os import make_nonblocking, nb_write

__implements__ = ["SemaphoreTracker", "_semaphore_tracker", "ensure_running",
                  "register", "unregister", "getfd"]
__target__ = "multiprocessing.semaphore_tracker"


class SemaphoreTracker(_SemaphoreTracker):
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


_semaphore_tracker = SemaphoreTracker()
ensure_running = _semaphore_tracker.ensure_running
register = _semaphore_tracker.register
unregister = _semaphore_tracker.unregister
getfd = _semaphore_tracker.getfd
