#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.md') as readme_file:
    readme = readme_file.read()

requirements = [
    'beautifulsoup4',
    'Click>=6.0'
]

setup(
    name='medium_to_ghost',
    version='0.0.2',
    description="Convert a Medium blog export file to Ghost 2.0 format (including images)",
    long_description=readme,
    packages=['medium_to_ghost'],
    author="Adam Geitgey",
    author_email='ageitgey@gmail.com',
    url='https://github.com/ageitgey/medium_to_ghost',
    entry_points={
        'console_scripts': [
            'medium_to_ghost=medium_to_ghost.medium_to_ghost:main'
        ]
    },
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='Medium',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)
