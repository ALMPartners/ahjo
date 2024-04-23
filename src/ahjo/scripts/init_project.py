# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

'''Ahjo project initialization command entrypoint.
'''
from os import getcwd
from ahjo.interface_methods import are_you_sure, remove_special_chars
from ahjo.operations import create_new_project
from ahjo.logging import setup_ahjo_logger

INIT_LOCATION = getcwd()
setup_ahjo_logger(enable_database_log = False)


def main():
    print('This is Ahjo project initialization command.')
    project_name_raw = input('Enter project name: ')
    project_name = remove_special_chars(project_name_raw)
    project_config_format = input("Select configuration file format (yaml/json/jsonc): ")
    warning_message = f"You are about to initialize a new project {project_name} to location {INIT_LOCATION}"
    if are_you_sure(warning_message):
        create_new_project(
            project_name, 
            INIT_LOCATION, 
            f'Ahjo - Creating new project {project_name}', 
            project_config_format = project_config_format
        )

if __name__ == '__main__':
    main()
