#!/usr/bin/env python

from setuptools import find_packages
from setuptools import setup

setup(
    test_suite="greentest.testrunner",
    entry_points={
        'gevent.plugins.monkey.will_patch_all': [
            "geventmp = geventmp.monkey:_patch_mp",
        ],
    },
)
