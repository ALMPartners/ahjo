# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

from logging import getLogger
from pathlib import Path
from re import sub

import commentjson as cjson

logger = getLogger('ahjo')


def load_json_conf(conf_file, key='BACKEND'):
    f_path = Path(conf_file)
    if not f_path.is_file():
        logger.error("No such file: " + f_path.absolute().as_posix())
        return None
    with open(f_path, encoding='utf-8') as f:
        raw_data = f.read()
    data = cjson.loads(raw_data)
    key_value = data.get(key, None)
    if key_value:
        return key_value
    return data


def are_you_sure(message):
    """Ask confirmation for action.

    Arguments
    ---------
    message: str
        Message to display before user confirmation.

    Returns
    -------
    Boolean
        True if the action is going to happen, False if the user does not permit the action.
    """
    logger.info(message)
    logger.info('Are you sure you want to proceed?')
    choise = input('[Y/N] (N): ')
    if choise == 'y' or choise == 'Y':
        logger.info('confirmed')
        return True
    else:
        logger.info('cancelled')
        return False


def remove_special_chars(in_string):
    '''Return a cleared string, that is, remove all characters except
    - alphabetical (A-Z) characters
    - numerical characters
    - underscores
    '''
    out_string = in_string.replace(' ', '_')
    out_string = sub('[^a-zA-Z0-9_]', '', out_string)
    out_string = out_string.lower()
    return out_string



def format_to_table(lst_of_lsts):
    """Format list of iterables to nice human-readable table."""
    col_widths = [0]*len(lst_of_lsts)
    for row in lst_of_lsts:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    col_formats = [f"{{:<{width + 2}}}" for width in col_widths]
    formatted_output = ''
    for row in lst_of_lsts:
        for i, cell in enumerate(row):
            formatted_output += col_formats[i].format(cell)
        formatted_output += '\n'
    return formatted_output
