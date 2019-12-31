# Ahjo - Database deployment framework
#
# Copyright 2019, 2020 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

from logging import getLogger
from os import path

from ahjo.interface_methods import load_json_conf
from ahjo.database_utilities import (create_conn_info,
                                     create_sqlalchemy_engine,
                                     create_sqlalchemy_url)

logger = getLogger('ahjo')

AHJO_PATH = path.dirname(__file__)

class Context:
    """All the default stuff that is passed to actions, like configuration."""
    def __init__(self, config_filename):
        self.ahjo_path = AHJO_PATH
        self.engine = None
        self.config_filename = config_filename
        self.configuration = load_json_conf(config_filename)
        if self.configuration is None:
            raise Exception("No configuration found")

    def get_conn_info(self):
        return create_conn_info(self.configuration)

    def get_engine(self):
        """Create engine when needed first time."""
        if self.engine is None:
            url = create_sqlalchemy_url(self.get_conn_info())
            self.engine = create_sqlalchemy_engine(url)
        return self.engine

    def get_master_engine(self):
        """Create and return engine to 'master' database."""
        url = create_sqlalchemy_url(self.get_conn_info(), use_master_db=True)
        return create_sqlalchemy_engine(url)


def filter_nested_dict(node, search_term):
    """Filter a nested dictionary by leaf value."""
    if isinstance(node, (str, int)):
        if node == search_term:
            return node
        else:
            return None
    elif isinstance(node, list):
        if search_term in node:
            return node
        else:
            return None
    elif node is None:
        return None
    else:
        dupe_node = {}
        for key, val in node.items():
            cur_node = filter_nested_dict(val, search_term)
            if cur_node is not None:
                dupe_node[key] = cur_node
        return dupe_node or None

def merge_nested_dicts(dict_a, dict_b, path=None):
    """Merge dictionary b to dictionary a.
    If keys conflict, that is, the same key exists in both dictionaries,
    overwrite the value of dictionary a with the value of dictionary b.
    """
    if path is None:
        path = []
    for key in dict_b:
        if key in dict_a:
            if isinstance(dict_a[key], dict) and isinstance(dict_b[key], dict):
                merge_nested_dicts(dict_a[key], dict_b[key], path + [str(key)])
            elif dict_a[key] == dict_b[key]:
                pass # same leaf value
            else:
                dict_a[key] = dict_b[key] # replace dict_a value with dict_b value
        else:
            dict_a[key] = dict_b[key]
    return dict_a

def merge_config_files(config_filename):
    """Return the contents of config_filename or merged contents,
    if there exists a link to another config file in config_filename.
    """
    config_data = load_json_conf(config_filename, key='')
    local_path = config_data.get('LOCAL', None)
    if local_path is not None:
        try:
            local_data = load_json_conf(local_path, key='')
            if local_data is not None:
                merged_configs = merge_nested_dicts(config_data, local_data)
                return merged_configs
        except Exception as err:
            logger.error(f'Could not open file {local_path}: {err}')
    return config_data
