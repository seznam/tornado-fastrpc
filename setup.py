#!/usr/bin/env python

from setuptools import setup, find_packages


setup(
    name="tornado-fastrpc",
    version='0.0.0',
    author='Seznam.cz, a.s.',
    author_email="jan.seifert@firma.seznam.cz",
    description=(
        "Asynchronous FastPRC client and server (handler) for Python's Tornado"
    ),
    license="commercial",
    url='ssh://git@gitlab.kancelar.seznam.cz:doporucovani/common.git',
    classifiers=[
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    packages=find_packages('tornado_fastrpc'),
    zip_safe=True,
    install_requires=[
        'setuptools>=0.6b1',
        'tornado>=3.0',
        'fastrpc',
        'pycurl',
    ],
)
