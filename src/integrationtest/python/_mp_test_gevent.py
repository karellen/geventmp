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
from time import sleep

from gevent import spawn
from gevent.util import assert_switches


def test_no_args():
    print(test_no_args.__name__)

    def count():
        while True:
            sleep(0.01)

    task = spawn(count)
    task.start()

    with assert_switches():
        sleep(1)

    task.kill()

    sys.exit(10)


def test_queues(r_q, w_q):
    def count():
        while True:
            sleep(0.01)

    task = spawn(count)
    task.start()

    with assert_switches():
        sleep(1)

    with assert_switches():
        print(r_q.get(timeout=5))

    with assert_switches():
        sleep(1)

    with assert_switches():
        w_q.put(test_queues.__name__, timeout=5)

    with assert_switches():
        sleep(1)

    task.kill()
    sys.exit(10)
