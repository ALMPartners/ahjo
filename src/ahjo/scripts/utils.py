# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

'''
    Utility functions for Ahjo scripts.
'''

import os

def get_config_path(config_filename: str) -> str:
    '''Get configuration filename from environment variable if not given as argument.'''
    if config_filename is None and 'AHJO_CONFIG_PATH' in os.environ:
        return os.environ.get('AHJO_CONFIG_PATH')
    return config_filename