# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name='gotorrent',
    version='0.1',
    url='https://github.com/danielzarco/DS-GoTorrent/',
    license='MIT License',
    author='Carlos Rincón, Daniel Zarco',
    install_requires=['gevent', 'pyactor'],
    test_suite='test',
)
