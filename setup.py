#!/usr/bin/env python

import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

from tornado_fastrpc import version


class PyTest(TestCommand):

    user_options = [
        ('pytest-args=', 'a', "Arguments to pass to py.test"),
    ]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def run_tests(self):
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

setup(
    name="tornado-fastrpc",
    version=version,
    author='Jan Seifert (Seznam.cz, a.s.)',
    author_email="jan.seifert@firma.seznam.cz",
    description=(
        "Asynchronous FastPRC client for Python's Tornado"
    ),
    license="commercial",
    url='ssh://git@gitlab.kancelar.seznam.cz:doporucovani/common.git',
    classifiers=[
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Development Status :: 3 - Alpha',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    platforms=['any'],
    packages=find_packages('tornado_fastrpc'),
    zip_safe=True,
    install_requires=[
        'setuptools>=0.6b1',
        'tornado>=3.2',
        'pycurl',
    ],
    extras_require={
        'FastRPC':  [
            'fastrpc',
        ],
    },
    tests_require=[
        'pytest-cov',
        'pytest',
        'mock',
    ],
    test_suite='tests',
    cmdclass={
        'test': PyTest,
    },
)
