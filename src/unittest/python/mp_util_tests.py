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

from importlib import import_module
from unittest import TestCase, main

from gevent.monkey import saved

from geventmp.monkey import GEVENT_SAVED_MODULE_SETTINGS

_mp_util = import_module("geventmp._mp.3._mp_util")

# The command CPython hands to the interpreter to bring up a forkserver. Up to 3.13.12 and
# 3.14.3 it was passed verbatim; gh-144503 (3.13.13, 3.14.4, 3.15) prefixed it with
# `import sys; sys.argv = ...` and appended the parent's argv after it.
LEGACY_CMD = "from multiprocessing.forkserver import main; main(11, 12, ['fork'], **{})"
NEW_CMD = ("import sys; sys.argv = ['/some/prog', '--flag']; "
           "from multiprocessing.forkserver import main; main(11, 12, ['fork'], **{}); "
           "sys.exit(0)")

# Same entry point, different children: these must never be rewritten.
TRACKER_CMD = "from multiprocessing.resource_tracker import main;main(13)"
SPAWN_CMD = "from multiprocessing.spawn import spawn_main; spawn_main(tracker_fd=13, pipe_handle=14)"

PREAMBLE_START = "from gevent import monkey; monkey.patch_all("


class SpawnvPassfdsTest(TestCase):
    def setUp(self):
        self.spawned = []
        self.watched = []
        self._real_spawn = _mp_util._spawnv_passfd
        self._real_watch = _mp_util._watch_child
        _mp_util._spawnv_passfd = lambda path, args, passfds: self.spawned.append((path, args, passfds)) or 4242
        _mp_util._watch_child = self.watched.append

        # The preamble is built from what `patch_all` was called with, which is only
        # populated once gevent has patched. Unit tests never patch, so supply it.
        self._had_settings = GEVENT_SAVED_MODULE_SETTINGS in saved
        self._old_settings = saved.get(GEVENT_SAVED_MODULE_SETTINGS)
        saved[GEVENT_SAVED_MODULE_SETTINGS] = {"geventmp": True, "socket": False, "thread": True}

    def tearDown(self):
        _mp_util._spawnv_passfd = self._real_spawn
        _mp_util._watch_child = self._real_watch
        if self._had_settings:
            saved[GEVENT_SAVED_MODULE_SETTINGS] = self._old_settings
        else:
            del saved[GEVENT_SAVED_MODULE_SETTINGS]

    def spawn(self, args):
        """Runs the real `spawnv_passfds` and returns the argv it would have executed."""
        passfds = (7, 8)
        self.assertEqual(_mp_util.spawnv_passfds("/usr/bin/python", args, passfds), 4242)
        self.assertEqual(len(self.spawned), 1)
        path, spawned_args, spawned_passfds = self.spawned[0]
        self.assertEqual(path, "/usr/bin/python")
        self.assertEqual(spawned_passfds, passfds)
        self.assertEqual(self.watched, [4242])
        return spawned_args

    def assert_patched(self, args, expected_index, expected_cmd):
        result = self.spawn(list(args))

        self.assertEqual(len(result), len(args))
        patched = result[expected_index]
        self.assertTrue(patched.startswith(PREAMBLE_START),
                        "preamble missing from %r" % patched)
        self.assertTrue(patched.endswith(expected_cmd),
                        "original command not preserved in %r" % patched)

        # Everything else must be passed through byte for byte, and the command must be
        # rewritten exactly once.
        for i, (before, after) in enumerate(zip(args, result)):
            if i != expected_index:
                self.assertEqual(before, after, "argument %d was modified" % i)

    def assert_untouched(self, args):
        self.assertEqual(self.spawn(list(args)), list(args))

    def test_no_interpreter_flags(self):
        self.assert_patched(["/usr/bin/python", "-c", LEGACY_CMD], 2, LEGACY_CMD)

    def test_interpreter_flags_shift_the_command(self):
        self.assert_patched(["/usr/bin/python", "-E", "-s", "-c", LEGACY_CMD], 4, LEGACY_CMD)

    def test_dash_x_dash_c_injects_a_decoy(self):
        # `python -X -c` makes `_args_from_interpreter_flags()` emit ['-X', '-c'], putting a
        # literal '-c' ahead of the real one. Locating the command by index silently skips it.
        args = ["/usr/bin/python", "-X", "-c", "-c", LEGACY_CMD]
        self.assertEqual(args.index("-c"), 2, "the decoy must precede the real -c")
        self.assert_patched(args, 4, LEGACY_CMD)

    def test_dash_x_dash_c_with_other_flags(self):
        self.assert_patched(["/usr/bin/python", "-E", "-X", "-c", "-s", "-c", LEGACY_CMD], 6, LEGACY_CMD)

    def test_new_style_command_with_sys_argv(self):
        # gh-144503 both prefixes and suffixes the command, so anchored matching fails here.
        self.assertFalse(NEW_CMD.startswith("from multiprocessing.forkserver import main"))
        self.assert_patched(["/usr/bin/python", "-c", NEW_CMD], 2, NEW_CMD)

    def test_new_style_command_with_flags(self):
        self.assert_patched(["/usr/bin/python", "-I", "-E", "-c", NEW_CMD], 4, NEW_CMD)

    def test_warning_filter_containing_the_sentinel_is_not_the_command(self):
        # `-W` folds its whole filter into one argument, so a filter mentioning the
        # forkserver entry point looks exactly like the command. Only the argument
        # immediately following `-c` is the command CPython is about to execute.
        self.assert_patched(["/usr/bin/python", "-Wignore:" + LEGACY_CMD, "-c", LEGACY_CMD], 3, LEGACY_CMD)

    def test_x_option_value_containing_the_sentinel_is_not_the_command(self):
        self.assert_patched(["/usr/bin/python", "-X", "opt=" + LEGACY_CMD, "-c", NEW_CMD], 4, NEW_CMD)

    def test_resource_tracker_is_not_patched(self):
        self.assert_untouched(["/usr/bin/python", "-E", "-c", TRACKER_CMD])

    def test_spawn_is_not_patched(self):
        self.assert_untouched(["/usr/bin/python", "-c", SPAWN_CMD, "--multiprocessing-fork"])

    def test_non_string_arguments_are_skipped(self):
        self.assert_patched(["/usr/bin/python", b"-c", "-c", LEGACY_CMD], 3, LEGACY_CMD)

    def test_only_the_first_command_is_patched(self):
        args = ["/usr/bin/python", "-c", LEGACY_CMD, LEGACY_CMD]
        result = self.spawn(list(args))
        self.assertTrue(result[2].startswith(PREAMBLE_START))
        self.assertEqual(result[3], LEGACY_CMD)


class CommandLineGeventPreambleTest(TestCase):
    def setUp(self):
        self._had_settings = GEVENT_SAVED_MODULE_SETTINGS in saved
        self._old_settings = saved.get(GEVENT_SAVED_MODULE_SETTINGS)
        self.settings = {"geventmp": True, "socket": False, "thread": True}
        saved[GEVENT_SAVED_MODULE_SETTINGS] = self.settings

    def tearDown(self):
        if self._had_settings:
            saved[GEVENT_SAVED_MODULE_SETTINGS] = self._old_settings
        else:
            del saved[GEVENT_SAVED_MODULE_SETTINGS]

    def test_preamble_is_executable_and_carries_the_patch_settings(self):
        prog, args = _mp_util.get_command_line_gevent_preamble()
        preamble = prog % args

        compile(preamble, "<preamble>", "exec")
        self.assertIn(repr(self.settings), preamble)

    def test_preamble_excludes_importable_settings(self):
        from gevent import config
        from gevent._config import ImportableSetting

        prog, args = _mp_util.get_command_line_gevent_preamble()
        config_args = args[1]

        importable = [k for k in dir(config) if isinstance(config.settings[k], ImportableSetting)]
        self.assertGreater(len(importable), 1)
        for k in importable:
            # These hold live objects that cannot survive a repr() round trip.
            self.assertNotIn(k, config_args)
        self.assertGreater(len(config_args), 1)


if __name__ == "__main__":
    main()
