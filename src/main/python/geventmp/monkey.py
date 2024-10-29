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
from importlib import import_module

GEVENT_SAVED_MODULE_SETTINGS = "_gevent_saved_patch_all_module_settings"


def _patch_module(name,
                  items=None,
                  _warnings=None,
                  _patch_kwargs=None,
                  _notify_will_subscribers=True,
                  _notify_did_subscribers=True,
                  _call_hooks=True,
                  _package_prefix='gevent.'):
    from gevent.monkey.api import patch_module

    gevent_module = import_module(_package_prefix + name)
    target_module_name = getattr(gevent_module, '__target__', name)
    target_module = import_module(target_module_name)

    patch_module(target_module, gevent_module, items=items,
                 _warnings=_warnings, _patch_kwargs=_patch_kwargs,
                 _notify_will_subscribers=_notify_will_subscribers,
                 _notify_did_subscribers=_notify_did_subscribers,
                 _call_hooks=_call_hooks)

    # On Python 2, the `futures` package will install
    # a bunch of modules with the same name as those from Python 3,
    # such as `_thread`; primarily these just do `from thread import *`,
    # meaning we have alternate references. If that's already been imported,
    # we need to attempt to patch that too.

    # Be sure to keep the original states matching also.

    alternate_names = getattr(gevent_module, '__alternate_targets__', ())
    from gevent.monkey._state import saved  # TODO: Add apis for these use cases.
    for alternate_name in alternate_names:
        alternate_module = sys.modules.get(alternate_name)
        if alternate_module is not None and alternate_module is not target_module:
            saved.pop(alternate_name, None)
            patch_module(alternate_module, gevent_module, items=items,
                         _warnings=_warnings,
                         _notify_will_subscribers=False,
                         _notify_did_subscribers=False,
                         _call_hooks=False)
            saved[alternate_name] = saved[target_module_name]

    return gevent_module, target_module


def _patch_mp(will_patch_all):
    from gevent.monkey._state import saved
    geventmp_arg = will_patch_all.will_patch_module("geventmp")
    if geventmp_arg is None or geventmp_arg:
        _patch_module("_mp.3._mp_spawn", _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_util", _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_connection", _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_synchronize", _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_popen_fork", _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_popen_spawn_posix", _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_forkserver", _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_resource_tracker", _package_prefix='geventmp.')
    saved[GEVENT_SAVED_MODULE_SETTINGS]["geventmp"] = True
