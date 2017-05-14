#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2017 InplusLab, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from os.path import dirname, join
from pip.req import parse_requirements

from setuptools import (
    find_packages,
    setup,
)


with open(join(dirname(__file__), 'InplusTrader/VERSION.txt'), 'rb') as f:
    version = f.read().decode('ascii').strip()

requirements = [str(ir.req) for ir in parse_requirements("requirements.txt", session=False)]

setup(
    name='InplusTrader',
    version=version,
    description='Program Trading System with Deep Learning',
    packages=find_packages(exclude=[]),
    author='Vinson Zheng',
    author_email='zhengwsh@foxmail.com',
    license='Apache License v2',
    package_data={'': ['*.*']},
    url='https://github.com/zhengwsh/InplusTrader_Linux',
    install_requires=requirements,
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2.7'
    ],
)