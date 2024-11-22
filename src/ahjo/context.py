# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import yaml
import json
from logging import getLogger
from typing import Union, Any
from sqlalchemy.engine import Engine, Connection
from ahjo.database_utilities import (create_conn_info, create_sqlalchemy_engine, create_sqlalchemy_url)
from ahjo.interface_methods import load_conf, load_json_conf, load_yaml_conf
from sqlalchemy import event

logger = getLogger('ahjo')


def _get_app_path() -> str:
    """Get the current app path"""
    # see https://cx-freeze.readthedocs.io/en/latest/faq.html#using-data-files
    if getattr(sys, "frozen", False):
        # Frozen = e.g. installed from an msi
        app_path = os.path.dirname(sys.executable)
    else:
        # Not frozen = e.g. a manual venv installation
        app_path = os.path.dirname(__file__)
    return app_path


AHJO_PATH = _get_app_path()


class Context:
    """All the default stuff that is passed to actions, like configuration."""

    def __init__(self, config_filename: str, master_engine: Engine = None, command_line_args: dict = {}):
        self.engine = None
        self.master_engine = master_engine
        self.connection = None
        self.transaction = None
        self.enable_transaction = None
        self.connectivity_type = None
        self.config_filename = config_filename
        self.configuration = load_conf(config_filename)
        self.command_line_args = command_line_args
        self.conn_info = None
        if self.configuration is None:
            raise Exception("No configuration found")
        

    def get_conn_info(self) -> dict:
        if self.conn_info is None:
            self.conn_info = create_conn_info(self.configuration)
        return self.conn_info
    

    def get_connectable(self) -> Union[Engine, Connection]:
        """Return Engine or Connection depending on connectivity type."""
        if self.connectivity_type is None:
            self.connectivity_type = self.configuration.get("context_connectable_type", "engine").lower()
        if self.connectivity_type == "connection":
            return self.get_connection()
        return self.get_engine()
    
    
    def set_connectable(self, connectable_type: str):
        """Set connectivity type to connectable_type."""
        self.connectivity_type = connectable_type


    def get_engine(self) -> Engine:
        """Create engine when needed first time."""
        if self.engine is None:
            conn_info = self.get_conn_info()
            self.engine = create_sqlalchemy_engine(
                create_sqlalchemy_url(conn_info),
                token = conn_info.get("token"),
                **conn_info.get("sqla_engine_params")
            )
        return self.engine
    

    def get_master_engine(self) -> Engine:
        """Return engine to 'master' database."""
        if self.master_engine is None:
            conn_info = self.get_conn_info()
            self.master_engine = create_sqlalchemy_engine(
                create_sqlalchemy_url(
                    conn_info, 
                    use_master_db=True
                ), 
                token = conn_info.get("token"),
                **conn_info.get("sqla_engine_params")
            )
        return self.master_engine
    

    def get_connection(self) -> Connection:
        """Create connection when needed first time."""
        if self.connection is None:

            connection = self.get_engine().connect()

            @event.listens_for(connection, "commit")
            def receive_after_commit(conn):
                for handler in logger.handlers:
                    if handler.name == "handler_database":
                        handler.set_lock(False)
                        handler.flush()
                        break

            @event.listens_for(connection, "rollback")
            def receive_after_rollback(conn):
                for handler in logger.handlers:
                    if handler.name == "handler_database":
                        handler.buffer = [record for record in handler.buffer if record.levelname != "INFO"]
                        handler.set_lock(False)
                        break
   
            self.connection = connection
            
        if self.enable_transaction is None:
            if self.configuration.get("transaction_mode", "begin_once").lower() == "begin_once":
                self.enable_transaction = True
            else:
                self.enable_transaction = False
        if self.enable_transaction:
            if self.transaction is None:
                self.transaction = self.connection.begin()
        return self.connection


    def get_enable_transaction(self) -> bool:
        return self.enable_transaction


    def get_command_line_args(self) -> dict:
        """ Get all command line arguments. """
        return self.command_line_args


    def get_command_line_arg(self, key: str) -> Any:
        """ Get command line argument value by key. 
            Return None if not found.
        """
        logger.debug('get_command_line_arg is deprecated. Use get_cli_arg instead.')
        return self.command_line_args.get(key, None)


    def get_cli_arg(self, key: str) -> Union[str, list, None]:
        """ Get command line argument value by key.

        Arguments:
        ----------
        key : str
            Key of the command line argument
        
        Returns:
        --------
        Union[str, list, None]
            Value of the command line argument.
        """
        # Reserved keys are not custom command line arguments
        reserved_keys = {"action", "config_filename", "files", "object_type", "non_interactive", "skip_metadata_update", "skip_git_update", "skip_alembic_update"}

        # Get the value of the key from the command line arguments
        cli_args = self.command_line_args.get(key, None)

        # If the key is reserved, return the value as is
        if key in reserved_keys:
            return cli_args
        
        if isinstance(cli_args, list):
            cli_args_len = len(cli_args)
            if cli_args_len == 1: # If there is only one value, return only the value
                return cli_args[0]
            elif cli_args_len > 1: # If there are multiple values, return the list
                return cli_args
            else: # By default, return True if the key exists. This is used for boolean flags (default value is True)
                return True
        return cli_args

    def set_enable_transaction(self, enable_transaction: bool):
        self.enable_transaction = enable_transaction


    def commit_and_close_transaction(self):
        if self.connectivity_type == "connection":
            if self.transaction is not None:
                self.transaction.commit()
                self.transaction.close()
                self.transaction = None
            elif self.connection is not None:
                self.connection.commit()
                self.connection.close()
                self.connection = None
            else:
                logger.warning('Transaction is not open.')


def filter_nested_dict(node, search_term: str) -> Union[dict, None]:
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


def merge_nested_dicts(dict_a: dict, dict_b: dict, path: str = None) -> dict:
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
                pass  # same leaf value
            else:
                # replace dict_a value with dict_b value
                dict_a[key] = dict_b[key]
        else:
            dict_a[key] = dict_b[key]
    return dict_a


def merge_config_files(config_filename: str) -> dict:
    """Return the contents of config_filename or merged contents,
    if there exists a link to another config file in config_filename.
    """
    config_data = load_conf(config_filename, key='')
    local_path = config_data.get('LOCAL', None)
    if local_path is not None:
        try:
            local_data = load_conf(local_path, key='')
            if local_data is not None:
                merged_configs = merge_nested_dicts(config_data, local_data)
                return merged_configs
        except Exception as err:
            logger.error(f'Could not open file {local_path}: {err}')
    return config_data


def config_is_valid(config: Union[str, dict], non_interactive: bool = False) -> bool:
    '''Validate configuration file.'''

    config = config if isinstance(config, dict) else load_conf(config) 

    # Allow only non-interactive authentication methods in non-interactive mode.
    if non_interactive:
        azure_auth = config.get("azure_authentication")
        if azure_auth is not None:
            if azure_auth == "ActiveDirectoryInteractive" :
                logger.error("Error: Azure authentication method ActiveDirectoryInteractive is not supported in non-interactive mode.")
                return False
        else:
            if config.get("username_file") is None:
                logger.error("Error: Username file is required in non-interactive mode.")
                return False
            if config.get("password_file") is None:
                logger.error("Error: Password file is required in non-interactive mode.")
                return False

    return True


def convert_config_to_yaml(config_path: str = "config_development.jsonc", output_path: str = "config_development.yaml") -> bool:
    '''Convert json/jsonc config file to YAML format.'''
    try:

        # Check if config file is in json or jsonc format.
        if not (config_path.endswith('.jsonc') or config_path.endswith('.json')):
            logger.error(f'Error: Configuration file must be in JSON or JSONC format.')
            return False

        configuration = load_json_conf(config_path, key=None)
        with open(output_path, 'w+', encoding='utf-8') as file:
            yaml.dump(configuration, file, default_flow_style=False)
        return True
    except Exception as err:
        logger.error(f'Could not convert config file to YAML format: {err}')
        return False
    

def convert_config_to_json(config_path: str = "config_development.yaml", output_path: str = "config_development.json") -> bool:
    '''Convert YAML config file to JSON format.'''
    try:

        # Check if config file is in yaml or yml format.
        if not (config_path.endswith('.yaml') or config_path.endswith('.yml')):
            logger.error(f'Error: Configuration file must be in YAML or YML format.')
            return False

        configuration = load_yaml_conf(config_path, key=None)
        with open(output_path, 'w+', encoding='utf-8') as file:
            json.dump(configuration, file, indent=4)
        return True
    except Exception as err:
        logger.error(f'Could not convert config file to JSON format: {err}')
        return False