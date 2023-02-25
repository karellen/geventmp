===============================================
 GeventMP_ - Gevent_ Multiprocessing Extension
===============================================

.. image:: https://img.shields.io/gitter/room/karellen/Lobby?logo=gitter
   :target: https://app.gitter.im/#/room/#karellen_Lobby:gitter.im
   :alt: Gitter
.. image:: https://img.shields.io/github/actions/workflow/status/karellen/geventmp/build.yml?branch=master
   :target: https://github.com/karellen/geventmp/actions/workflows/build.yml
   :alt: Build Status
.. image:: https://img.shields.io/coveralls/github/karellen/geventmp/master?logo=coveralls
   :target: https://coveralls.io/r/karellen/geventmp?branch=master
   :alt: Coverage Status

|

.. image:: https://img.shields.io/pypi/v/geventmp?logo=pypi
   :target: https://pypi.org/project/geventmp/
   :alt: GeventMP Version
.. image:: https://img.shields.io/pypi/pyversions/geventmp?logo=pypi
   :target: https://pypi.org/project/geventmp/
   :alt: GeventMP Python Versions
.. image:: https://img.shields.io/pypi/dd/geventmp?logo=pypi
   :target: https://pypi.org/project/geventmp/
   :alt: GeventMP Downloads Per Day
.. image:: https://img.shields.io/pypi/dw/geventmp?logo=pypi
   :target: https://pypi.org/project/geventmp/
   :alt: GeventMP Downloads Per Week
.. image:: https://img.shields.io/pypi/dm/geventmp?logo=pypi
   :target: https://pypi.org/project/geventmp/
   :alt: GeventMP Downloads Per Month

|

.. warning::
    HIC SUNT DRACONES!!!

    This code is experimental (beta). There is some testing, but a lots of things are in flux, and
    some platforms don't work at all.

    You MAY try to use this in production with the understanding that this is a beta-quality software.

    That said, this code may crash your server, bankrupt your company, burn your house down and be mean
    to your puppy.

    You've been warned.

Problem
=======

Due to internal implementation, `multiprocessing` (`MP`) is unsafe to use with Gevent_ even when `monkey-patched`__.
Namely, the use of OS semaphore primitives and inter-process IO in `MP` will cause the main
loop to stall/deadlock/block (specific issue depends on the version of CPython).

__ monkey_

Solution
========
GeventMP_ (`Gee-vent Em-Pee`) is a gevent_ multiprocessing extension plugin for the `monkey-patching`__ subsystem.
As with the rest of the monkey patch subsystem the process is fairly clear:

__ monkey_

1. Identify all places where blocking occurs and where it may stall the loop.
2. If blocking occurs on a file descriptor (`FD`), try to convert the file descriptor from blocking to non-blocking
   (sockets/pipes/fifos, sometimes even files where, rarely, appropriate) and replace blocking IO functions with their
   gevent_ non-blocking equivalents.
3. If blocking occurs in a Python/OS primitive that does not support non-blocking access and thus cannot be geventized,
   wrap all blocking access to that primitive with native thread-pool-based wrappers and call it a day (while fully
   understanding that primitive access latency will increase and raw performance may suffer as a result).
4. If you are really brave and have lots of free time on your hands, completely replace a standard blocking Python
   non-`FD`-based primitive with implementation based on an `FD`-based OS primitive (e.g. POSIX semaphore =>
   Linux `eventfd-based semaphore for kernels > 2.6.30`__).
5. Due to launching of separate processes in `MP`, figure out how, when, and whether to `monkey-patch`__ spawned/forked
   children and grandchildren.

__ eventfd_

__ monkey_

Installation
============
The package is hosted on PyPi_.

For stable version:

.. code-block:: bash

  pip install geventmp

For unstable version:

.. code-block:: bash

  pip install --pre geventmp


Once installed, `GeventMP`_ will activate by default in the below stanza.

.. code-block:: python

   from gevent.monkey import patch_all
   patch_all()

If you would like `GeventMP`_ to not activate by default, either do not install it or explicitly disable it:

.. code-block:: python

   from gevent.monkey import patch_all
   patch_all(geventmp=False)

That's it - there are no other flags, settings, properties or config values so far.

Supported Platforms
===================

.. note::
    All claims of support may not be real at all. You're welcome to experiment. See warnings on top.

* Linux and Darwin.
* CPython 3.7, 3.8, 3.9, 3.10, 3.11
* PyPy 3.7, 3.8, 3.9

Known Issues
============

* Multiprocessing `forkserver` works in GeventMP_, but the spawned child isn't green.

TODO
====
1. Monkey patch Windows to the extent possible.
2. Lots of applications use `Billiard <https://github.com/celery/billiard>`_ for multiprocessing instead of stock Python
   package. Consider monkey patching Billiard if detected.

Contact Us
==========

Post feedback and issues on the `Bug Tracker`_, `Gitter`_,
and `Twitter (@karelleninc)`_.

.. _Gevent: https://github.com/gevent/gevent/
.. _geventmp: https://github.com/karellen/geventmp
.. _bug tracker: https://github.com/karellen/geventmp/issues
.. _gitter: https://gitter.im/karellen/Lobby
.. _twitter (@karelleninc): https://twitter.com/karelleninc
.. _monkey: https://en.wikipedia.org/wiki/Monkey_patch
.. _eventfd: https://linux.die.net/man/2/eventfd
.. _pypi: https://pypi.org/project/geventmp/
