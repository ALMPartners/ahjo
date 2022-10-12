# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021, 2022 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

'''
    Ahjo multi-project-build command entrypoint.
'''

import argparse
from ahjo.operations.general.multi_project_build import run_multi_project_build

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config_filename", help="Configuration filename", type=str, nargs="?")
    print('This is Ahjo multi-project build command.')

    args = parser.parse_args()
    run_multi_project_build(args.config_filename)

if __name__ == '__main__':
    main()
