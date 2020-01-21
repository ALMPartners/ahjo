# Ahjo - Database deployment framework
#
# Copyright 2019, 2020 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Initialize operations.
Includes functions for creating local configuration file and a new project.

Global variable PROJECT_STRUCTURE is a dictionary holding information about project file structure.
- If key value is dictionary, new directory with the name of key is created
- If key value is "empty file", empty file with the name of key is created
- If key value is a path to resource folder, the file of the path is copied to new project
"""
import json
from os import makedirs, path
from pathlib import Path
from shutil import copyfile

from ahjo.context import AHJO_PATH, filter_nested_dict
from ahjo.interface_methods import load_json_conf
from ahjo.operation_manager import OperationManager

PROJECT_STRUCTURE = {
    "alembic": {
        "versions": {},
        "env.py": "resources/files/env.py",
        "README": "empty file",
        "script.py.mako": "resources/files/script.py.mako"
        },
    "database": {
        "data": {
            "testdata": {"schema.tableName.sql": "resources/sql/templates/schema.tableName.sql"}
        },
        "assemblies": {},
        "functions": {"schema.functionName.sql": "resources/sql/templates/schema.functionName.sql"},
        "procedures": {"schema.procedureName.sql": "resources/sql/templates/schema.procedureName.sql"},
        "clr-procedures": {},
        "views":  {"schema.viewName.sql": "resources/sql/templates/schema.viewName.sql"},
        "tests": {}
    },
    ".gitignore" : "resources/files/.gitignore",
    "ahjo_actions.py": "resources/files/ahjo_actions.py",
    "alembic.ini": "resources/files/alembic.ini",
    "config_development.jsonc": "resources/files/config_development.jsonc",
    "README.md": "empty file"
}

def create_local_config_base(config_filename):
    """Check the existence and create local config file,
    if key 'LOCAL' exists in configuration file (config_filename).

    Local config file is used in development environment to store Django
    related passwords, secrets and all stuff which aren't suitable for versioning.
    """
    with OperationManager('Initializing local config file'):
        if not Path(config_filename).is_file():
            print("File not found: "+ config_filename)
            return
        config_data = load_json_conf(config_filename, key='')
        local_path = config_data.get('LOCAL', None)
        if not local_path:
            print("Local config not defined in {}".format(config_filename))
            return
        if Path(local_path).is_file():
            print("Local config file already exists")
            return
        if isinstance(local_path, str):
            try:
                local_conf_dict = filter_nested_dict(config_data, '$')
                with open(local_path, 'w+', encoding='utf-8') as file:
                    json.dump(local_conf_dict, file)
                print('Local config file created')
            except Exception as err:
                print('Problem creating local config file: {}'.format(err))


def create_new_project(project_name, init_location, message):
    '''Create project root directory and call populate_project.'''
    with OperationManager(message):
        project_root = path.join(init_location, project_name)
        if path.exists(project_root):
            print(f'Folder {project_root} already exists. Terminating.')
            return
        makedirs(project_root)
        populate_project(project_root, PROJECT_STRUCTURE)
        print(f'Project {project_root} created.')


def populate_project(root_path, dir_dict):
    '''Recursively create given file structure to root location.'''
    for key in dir_dict:
        object_path = path.join(root_path, key)
        if isinstance(dir_dict[key], dict):
            makedirs(object_path)
            populate_project(object_path, dir_dict[key])
        elif isinstance(dir_dict[key], str):
            if dir_dict[key] == 'empty file':
                open(object_path, 'a').close()
            else:
                copyfile(path.join(AHJO_PATH, dir_dict[key]), object_path)
