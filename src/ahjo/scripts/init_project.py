# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

'''Ahjo project initialization command entrypoint.
'''
from os import getcwd, path
from logging.config import fileConfig

from ahjo.interface_methods import are_you_sure, remove_special_chars
from ahjo.operations import create_new_project
import ahjo # unqualified import for ahjo.__file__ location

INIT_LOCATION = getcwd()

fileConfig(path.join(path.dirname(ahjo.__file__), 'resources/logger.ini'))


def main():
    print('This is Ahjo project initialization command.')
    project_name_raw = input('Enter project name: ')
    project_name = remove_special_chars(project_name_raw)
    warning_message = f"You are about to initialize a new project {project_name} to location {INIT_LOCATION}"
    if are_you_sure(warning_message):
        create_new_project(project_name, INIT_LOCATION, f'Ahjo - Creating new project {project_name}')

if __name__ == '__main__':
    main()
