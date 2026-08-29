#   -*- coding: utf-8 -*-
#   Copyright 2020 Karellen, Inc. and contributors
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
from multiprocessing.resource_tracker import ResourceTracker as _ResourceTracker

from gevent.os import make_nonblocking, nb_write

__implements__ = ["ResourceTracker", "_resource_tracker", "ensure_running",
                  "register", "unregister", "getfd"]
__target__ = "multiprocessing.resource_tracker"


# Newer CPythons funnel every tracker write through `_write`, while `_send` gained
# JSON/base64 name encoding and reentrant-call queueing. Hooking `_write` there keeps
# all of that and only replaces the blocking write. This landed mid-series (3.13.7,
# 3.14.1, 3.15), so it must be detected by feature, never by version.
_HAS_WRITE = hasattr(_ResourceTracker, "_write")


class ResourceTracker(_ResourceTracker):
    def ensure_running(self):
        super().ensure_running()
        make_nonblocking(self._fd)

    if _HAS_WRITE:
        def _write(self, msg):
            # `nb_write` requires a non-blocking descriptor, and nothing else on this
            # path guarantees one: upstream reaches `_write` through
            # `_ensure_running_and_write`, which bypasses `ensure_running` above. The fd
            # may be freshly launched, or inherited blocking from a non-gevent ancestor.
            # Every write funnels through here, so conditioning it here covers them all.
            make_nonblocking(self._fd)
            nbytes = nb_write(self._fd, msg)
            assert nbytes == len(msg), "nbytes {0:n} but len(msg) {1:n}".format(
                nbytes, len(msg))
    else:
        def _send(self, cmd, name, rtype):
            self.ensure_running()
            msg = '{0}:{1}:{2}\n'.format(cmd, name, rtype).encode('ascii')
            if len(name) > 512:
                # posix guarantees that writes to a pipe of less than PIPE_BUF
                # bytes are atomic, and that PIPE_BUF >= 512
                raise ValueError('name too long')
            nbytes = nb_write(self._fd, msg)
            assert nbytes == len(msg), "nbytes {0:n} but len(msg) {1:n}".format(
                nbytes, len(msg))


_resource_tracker = ResourceTracker()
ensure_running = _resource_tracker.ensure_running
register = _resource_tracker.register
unregister = _resource_tracker.unregister
getfd = _resource_tracker.getfd

if hasattr(_resource_tracker, "_after_fork_in_child") and hasattr(os, "register_at_fork"):
    # gh-146313 (3.13.14, 3.14.5, 3.15) registers this hook against the instance we
    # are replacing, so without re-registering it ours would never have its lock
    # reinitialized after a fork. Gated separately from `_write`: there are releases
    # that have one and not the other.
    os.register_at_fork(after_in_child=_resource_tracker._after_fork_in_child)
