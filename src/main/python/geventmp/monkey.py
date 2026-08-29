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

GEVENT_SAVED_MODULE_SETTINGS = "_gevent_saved_patch_all_module_settings"

_RESOURCE_TRACKER = "geventmp._mp.3._mp_resource_tracker"


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

    return gevent_module, target_module


def _patch_mp(will_patch_all):
    from gevent.monkey._state import saved

    # `geventmp` is not one of gevent's own module names, so `patch_all` files it under
    # the extra kwargs. `will_patch_module` only consults `patch_all_arguments`, where
    # it can never appear, so it answered None whether `geventmp=False` was passed or
    # nothing was passed at all, and the opt-out could never fire.
    geventmp_arg = will_patch_all.patch_all_kwargs.get("geventmp")
    enabled = geventmp_arg is None or bool(geventmp_arg)
    if enabled:
        _patch_module("_mp.3._mp_spawn", _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_util", _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_connection", _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_synchronize", _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_popen_fork", _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_popen_forkserver", _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_popen_spawn_posix", _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_forkserver", _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_resource_tracker", _package_prefix='geventmp.')

    # Replayed as `patch_all(**...)` in spawned children, so the opt-out travels too.
    saved[GEVENT_SAVED_MODULE_SETTINGS]["geventmp"] = enabled


def _patch_mp_done(did_patch_all):
    from sys import modules

    gevent_module = modules.get(_RESOURCE_TRACKER)
    if gevent_module is None:
        return

    from multiprocessing.resource_tracker import _resource_tracker

    if _resource_tracker is not gevent_module._resource_tracker:
        return

    if not hasattr(_resource_tracker, "_write"):
        # Older interpreters issue the non-blocking write from `_send`, outside the
        # lock, so there is nothing to yield underneath.
        return

    # `_write` parks in the hub while `_ensure_running_and_write` holds this lock. The
    # tracker is built during `will_patch_all`, so it was handed a native RLock, which
    # is owned per OS thread: a second greenlet acquires it instead of waiting, and
    # upstream mistakes the overlap for a reentrant call. `threading` is patched by the
    # time this runs, so this lock is owned per greenlet instead.
    from threading import RLock

    _resource_tracker._lock = RLock()
