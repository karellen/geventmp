#   -*- coding: utf-8 -*-
#   Copyright 2026 Karellen, Inc. and contributors
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

from multiprocessing.process import current_process

from gevent import monkey

if not getattr(current_process(), "_inheriting", False):
    monkey.patch_all(geventmp=False)

import sys
from unittest import TestCase, main

import multiprocessing.connection
import multiprocessing.forkserver
import multiprocessing.popen_fork
import multiprocessing.popen_forkserver
import multiprocessing.popen_spawn_posix
import multiprocessing.resource_tracker
import multiprocessing.spawn
import multiprocessing.synchronize
import multiprocessing.util

from gevent.monkey import saved

from geventmp.monkey import GEVENT_SAVED_MODULE_SETTINGS

# Every module geventmp patches, paired with a name it replaces there.
PATCH_TARGETS = [
    (multiprocessing.resource_tracker, "ResourceTracker"),
    (multiprocessing.util, "spawnv_passfds"),
    (multiprocessing.spawn, "get_command_line"),
    (multiprocessing.connection, "Connection"),
    (multiprocessing.synchronize, "SemLock"),
    (multiprocessing.popen_fork, "Popen"),
    (multiprocessing.popen_forkserver, "Popen"),
    (multiprocessing.popen_spawn_posix, "Popen"),
    (multiprocessing.forkserver, "ForkServer"),
]


class GeventMpDisabledTest(TestCase):
    """`patch_all(geventmp=False)` has to actually opt out.

    `geventmp` is not one of gevent's own module names, so it arrives in
    `patch_all_kwargs`; `will_patch_module` only ever consults
    `patch_all_arguments` and so reported `None` for it either way.
    """

    def test_no_patch_module_is_even_imported(self):
        self.assertEqual(sorted(m for m in sys.modules if m.startswith("geventmp._mp")), [])

    def test_multiprocessing_is_left_alone(self):
        self.assertGreater(len(PATCH_TARGETS), 1)
        for module, name in PATCH_TARGETS:
            with self.subTest(target="%s.%s" % (module.__name__, name)):
                self.assertEqual(getattr(module, name).__module__, module.__name__)

    def test_children_inherit_the_opt_out(self):
        # This dict is replayed as `patch_all(**...)` in spawned children.
        self.assertIs(saved[GEVENT_SAVED_MODULE_SETTINGS]["geventmp"], False)


if __name__ == '__main__':
    main()
