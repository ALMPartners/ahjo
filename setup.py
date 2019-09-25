# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

'''Ahjo package setup'''
from setuptools import setup, find_packages

setup(
    name="ahjo",
    version="0.4.0",
    author="ALM Partners Oy",
    author_email="aleksi.korpinen@almpartners.fi",
    description="Database deployment framework",
    keywords="ahjo",
    url="https://bitbucket.org/almp/ahjo/src/",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'ahjo = ahjo.scripts.master:main',
            'ahjo-init-project = ahjo.scripts.init_project:main',
        ]
    },
    include_package_data=True,
    install_requires=[
        'commentjson',
        'alembic',
        'pyodbc',
        'sqlalchemy',
    ],
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License", # 2.0 is the only OSI approved Apache license
        'Topic :: Database',
    ],
)