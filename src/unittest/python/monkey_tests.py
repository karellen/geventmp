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

from unittest import TestCase, main

from gevent.events import GeventWillPatchAllEvent
from gevent.monkey import saved

from geventmp.monkey import GEVENT_SAVED_MODULE_SETTINGS, _patch_mp

# What `patch_all(geventmp=False, thread=True, ...)` hands the subscriber: gevent's own
# module names are resolved into the arguments, everything else stays in the kwargs.
PATCH_ALL_ARGUMENTS = {"os": True, "thread": True, "socket": True}
PATCH_ALL_KWARGS = {"geventmp": False, "some_other_plugin": True}


def opt_out_event():
    return GeventWillPatchAllEvent(dict(PATCH_ALL_ARGUMENTS), dict(PATCH_ALL_KWARGS))


class PatchMpOptOutTest(TestCase):
    """Only the opt-out is exercised here: the enabled path patches the live
    interpreter, so it belongs to the integration suites."""

    def setUp(self):
        self.had_settings = GEVENT_SAVED_MODULE_SETTINGS in saved
        self.old_settings = saved.get(GEVENT_SAVED_MODULE_SETTINGS)
        saved[GEVENT_SAVED_MODULE_SETTINGS] = {}

    def tearDown(self):
        if self.had_settings:
            saved[GEVENT_SAVED_MODULE_SETTINGS] = self.old_settings
        else:
            del saved[GEVENT_SAVED_MODULE_SETTINGS]

    def test_gevent_cannot_report_on_a_third_party_name(self):
        # The reason geventmp has to read the kwargs itself. If gevent ever teaches
        # `will_patch_module` about the extra kwargs, this fails and the workaround in
        # `_patch_mp` can go away.
        event = opt_out_event()

        self.assertIsNone(event.will_patch_module("geventmp"))
        self.assertIs(event.patch_all_kwargs["geventmp"], False)
        self.assertTrue(event.will_patch_module("thread"))

    def test_opt_out_is_recorded_for_children(self):
        # This dict is replayed as `patch_all(**...)` in spawned children, so an opt-out
        # that is not recorded here comes back in every child.
        _patch_mp(opt_out_event())

        self.assertIs(saved[GEVENT_SAVED_MODULE_SETTINGS]["geventmp"], False)


if __name__ == "__main__":
    main()
