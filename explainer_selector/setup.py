#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import find_packages, setup
from glob import glob

NAME = "explainer_selector"

setup(
    name=NAME,
    version="0.1.0",
    license="Apache-2.0",
    description="explainer_selector",
    author="todo",
    author_email="todo@todo.todo",
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/' + NAME, ['package.xml']),
        ('share/ament_index/resource_index/packages', ['res/' + NAME]),
        ('share/' + NAME + '/launch', glob('launch/*.launch.py')),
    ],
    tests_require=['pytest'],
    install_requires=['setuptools'],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'start_explainer_selector = ' + NAME + '.start_explainer_selector:main'
        ],
    },
)
