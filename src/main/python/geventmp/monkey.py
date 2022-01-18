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

import gevent
import pkg_resources
from gevent.monkey import __call_module_hook, _notify_patch, saved, _NONE

GEVENT_PRE_15a3 = False
GEVENT_SAVED_MODULE_SETTINGS = "_gevent_saved_patch_all_module_settings"
gevent_ver = pkg_resources.parse_version(gevent.__version__)
if gevent_ver < pkg_resources.parse_version("1.5a3"):
    GEVENT_PRE_15a3 = True
    GEVENT_SAVED_MODULE_SETTINGS = "_gevent_saved_patch_all"


def patch_item(module, attr, newitem, _patch_module=False):
    olditem = getattr(module, attr, _NONE)
    if olditem is not _NONE:
        saved.setdefault(module.__name__, {}).setdefault(attr, olditem)
    setattr(module, attr, newitem)
    if _patch_module:
        if olditem is not None and newitem is not None:
            try:
                newitem.__module__ = olditem.__module__
            except (TypeError, AttributeError):
                pass


def patch_module(target_module, source_module, items=None,
                 _warnings=None,
                 _notify_will_subscribers=True,
                 _notify_did_subscribers=True,
                 _call_hooks=True,
                 _patch_module=False):
    """
    patch_module(target_module, source_module, items=None)

    Replace attributes in *target_module* with the attributes of the
    same name in *source_module*.

    The *source_module* can provide some attributes to customize the process:

    * ``__implements__`` is a list of attribute names to copy; if not present,
      the *items* keyword argument is mandatory.
    * ``_gevent_will_monkey_patch(target_module, items, warn, **kwargs)``
    * ``_gevent_did_monkey_patch(target_module, items, warn, **kwargs)``
      These two functions in the *source_module* are called *if* they exist,
      before and after copying attributes, respectively. The "will" function
      may modify *items*. The value of *warn* is a function that should be called
      with a single string argument to issue a warning to the user. If the "will"
      function raises :exc:`gevent.events.DoNotPatch`, no patching will be done. These functions
      are called before any event subscribers or plugins.

    :keyword list items: A list of attribute names to replace. If
       not given, this will be taken from the *source_module* ``__implements__``
       attribute.
    :return: A true value if patching was done, a false value if patching was canceled.

    .. versionadded:: 1.3b1
    """
    from gevent import events

    if items is None:
        items = getattr(source_module, '__implements__', None)
        if items is None:
            raise AttributeError('%r does not have __implements__' % source_module)

    try:
        if _call_hooks:
            __call_module_hook(source_module, 'will', target_module, items, _warnings)
        if _notify_will_subscribers:
            _notify_patch(
                events.GeventWillPatchModuleEvent(target_module.__name__, source_module,
                                                  target_module, items),
                _warnings)
    except events.DoNotPatch:
        return False

    for attr in items:
        patch_item(target_module, attr, getattr(source_module, attr),
                   _patch_module=_patch_module)

    if _call_hooks:
        __call_module_hook(source_module, 'did', target_module, items, _warnings)

    if _notify_did_subscribers:
        # We allow turning off the broadcast of the 'did' event for the benefit
        # of our internal functions which need to do additional work (besides copying
        # attributes) before their patch can be considered complete.
        _notify_patch(
            events.GeventDidPatchModuleEvent(target_module.__name__, source_module,
                                             target_module)
        )

    return True


def _patch_module(name,
                  items=None,
                  _warnings=None,
                  _notify_will_subscribers=True,
                  _notify_did_subscribers=True,
                  _call_hooks=True,
                  _patch_module=False,
                  _package_prefix='gevent.'):
    gevent_module = import_module(_package_prefix + name)
    module_name = getattr(gevent_module, '__target__', name)
    target_module = import_module(module_name)

    patch_module(target_module, gevent_module, items=items,
                 _warnings=_warnings,
                 _notify_will_subscribers=_notify_will_subscribers,
                 _notify_did_subscribers=_notify_did_subscribers,
                 _call_hooks=_call_hooks,
                 _patch_module=_patch_module)

    # On Python 2, the `futures` package will install
    # a bunch of modules with the same name as those from Python 3,
    # such as `_thread`; primarily these just do `from thread import *`,
    # meaning we have alternate references. If that's already been imported,
    # we need to attempt to patch that too.

    # Be sure to keep the original states matching also.

    alternate_names = getattr(gevent_module, '__alternate_targets__', ())
    for alternate_name in alternate_names:
        alternate_module = sys.modules.get(alternate_name)
        if alternate_module is not None and alternate_module is not target_module:
            saved.pop(alternate_name, None)
            patch_module(alternate_module, gevent_module, items=items,
                         _warnings=_warnings,
                         _notify_will_subscribers=False,
                         _notify_did_subscribers=False,
                         _call_hooks=False,
                         _patch_module=_patch_module)
            saved[alternate_name] = saved[module_name]

    return gevent_module, target_module


def _patch_mp(will_patch_all):
    geventmp_arg = will_patch_all.will_patch_module("geventmp")
    if geventmp_arg is None or geventmp_arg:
        _patch_module("_mp.3._mp_spawn", _patch_module=True, _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_util", _patch_module=True, _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_connection", _patch_module=True, _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_synchronize", _patch_module=True, _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_popen_fork", _patch_module=True, _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_popen_spawn_posix", _patch_module=True, _package_prefix='geventmp.')
        _patch_module("_mp.3._mp_forkserver", _patch_module=True, _package_prefix='geventmp.')
        if sys.version_info >= (3, 8):
            # See https://bugs.python.org/issue36867
            _patch_module("_mp.3._mp_resource_tracker", _patch_module=True, _package_prefix='geventmp.')
        else:
            _patch_module("_mp.3._mp_sem_tracker", _patch_module=True, _package_prefix='geventmp.')

        saved[GEVENT_SAVED_MODULE_SETTINGS]["geventmp"] = True
