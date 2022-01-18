#   -*- coding: utf-8 -*-
#   Copyright 2022 Karellen, Inc. and contributors
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

from gevent.os import make_nonblocking
from multiprocessing.popen_fork import Popen as _Popen

__implements__ = ["Popen"]
__target__ = "multiprocessing.popen_fork"


class Popen(_Popen):
    def _launch(self, process_obj):
        self.sentinel = None
        try:
            super()._launch(process_obj)
        finally:
            if self.sentinel is not None:
                make_nonblocking(self.sentinel)
