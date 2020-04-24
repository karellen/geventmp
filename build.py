#   -*- coding: utf-8 -*-
from pybuilder.core import (use_plugin, init, Author, before, Dependency)

use_plugin("python.core")
use_plugin("python.integrationtest")
use_plugin("python.flake8")
use_plugin("python.coverage")
use_plugin("python.distutils")
use_plugin("python.pycharm")
use_plugin("python.coveralls")
use_plugin("copy_resources")

name = "geventmp"
version = "0.0.1.dev"

summary = "Multiprocessing Gevent Extension"
authors = [Author("Karellen, Inc.", "supervisor@karellen.co")]
maintainers = [Author("Arcadiy Ivanov", "arcadiy@ivanov.biz")]
url = "https://github.com/karellen/geventmp"
urls = {
    "Bug Tracker": "https://github.com/karellen/geventmp/issues",
    "Source Code": "https://github.com/karellen/geventmp/",
    "Documentation": "https://github.com/karellen/geventmp/"
}
license = "Apache License, Version 2.0"

requires_python = ">=2.7,!=3.0,!=3.1,!=3.2,!=3.3,!=3.4"

default_task = ["analyze", "publish"]


@init
def set_properties(project):
    project.depends_on("gevent", ">=1.3.0")

    project.set_property("it_coverage_concurrency", ["gevent"])
    project.set_property("it_coverage_debug", ["trace"])

    project.set_property("integrationtest_inherit_environment", True)

    project.set_property("flake8_break_build", True)
    project.set_property("flake8_extend_ignore", "E303,E402")
    project.set_property("flake8_include_test_sources", True)
    project.set_property("flake8_include_scripts", True)
    project.set_property("flake8_max_line_length", 130)

    project.set_property("copy_resources_target", "$dir_dist/geventmp")
    project.get_property("copy_resources_glob").append("LICENSE")
    project.include_file("geventmp", "LICENSE")

    project.set_property("distutils_readme_description", True)
    project.set_property("distutils_description_overwrite", True)
    project.set_property("distutils_upload_skip_existing", True)
    project.set_property("distutils_setup_keywords", ["gevent", "multiprocessing", "mp", "monkey"])
    project.set_property("distutils_readme_file", "README.rst")
    project.set_property("distutils_readme_file_type", "text/x-rst")
    project.set_property("distutils_readme_file_encoding", "UTF-8")

    project.set_property("distutils_entry_points", {
        "gevent.plugins.monkey.will_patch_all": ["geventmp = geventmp.monkey:_patch_mp"]
    })

    project.set_property("distutils_classifiers", [
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
        "Development Status :: 2 - Pre-Alpha"
    ])


@before("run_integration_tests", only_once=True)
def install_for_tests(project, logger, reactor):
    reactor.python_env_registry["test"].install_dependencies([Dependency(project.expand_path("$dir_dist"))])
