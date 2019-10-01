# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

'''Ahjo package setup'''
from os import path

from setuptools import find_packages, setup

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    readme = f.read()

setup(
    name="ahjo",
    version="0.4.0",
    author="ALM Partners Oy",
    author_email="aleksi.korpinen@almpartners.fi",
    description="Database deployment framework",
    long_description=readme,
    long_description_content_type='text/markdown',
    keywords="ahjo",
    url="https://github.com/ALMPartners/ahjo",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'ahjo = ahjo.scripts.master:main',
            'ahjo-init-project = ahjo.scripts.init_project:main',
        ]
    },
    include_package_data=True,
    install_requires=[
        'commentjson>=0.7.1',
        'alembic>=1.0.6',
        'pyodbc>=4.0.22',
        'sqlalchemy>=1.3.0',
    ],
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License", # 2.0 is the only OSI approved Apache license
        "Topic :: Database",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
)
