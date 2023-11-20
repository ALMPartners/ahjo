# Ahjo - Database deployment framework
#
# Copyright 2019 - 2022 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import ahjo.scripts.master_actions
import os
import importlib
import sys
from ahjo.database_utilities import create_conn_info, create_sqlalchemy_url, create_sqlalchemy_engine
from ahjo.interface_methods import load_conf, are_you_sure
from ahjo.action import execute_action, registered_actions, DEFAULT_ACTIONS_SRC
from ahjo.operation_manager import format_message
from logging import getLogger
from logging.config import fileConfig
from pathlib import Path


def run_multi_project_build(master_config_path: str, skip_project_confirmation = True):
    """
        Run all selected actions from different projects at once.

        Parameters
        ----------
        master_config_path
            Path to JSON/JSONC config file.
    """

    # Load multi-project-build config
    anchor_path = load_conf(master_config_path, "projects_path")
    config_conn_info = load_conf(master_config_path, "connection_info")
    ahjo_projects = load_conf(master_config_path, "projects")
    anchor_parent_path_str = str(Path(anchor_path).parent)
    anchor_name = Path(anchor_path).parts[-1]

    # Format are_you_sure message
    are_you_sure_msg = ["You are about to run the following actions: ", ""]
    for ahjo_project in ahjo_projects:
        are_you_sure_msg.append(ahjo_project + ":")
        are_you_sure_msg.append(" " * 2 + ", ".join(ahjo_projects[ahjo_project]["actions"]))
    are_you_sure_msg.append("")

    # Confirm action
    if not are_you_sure(are_you_sure_msg, False): return False

    # Create sqlalchemy master engine
    conn_info = create_conn_info(config_conn_info)
    master_engine = create_sqlalchemy_engine(
        create_sqlalchemy_url(
            conn_info, 
            use_master_db=True
        ), 
        token = conn_info.get("token")
    )

    for ahjo_project in ahjo_projects:
        
        # Reload master actions & update global variable: registered_actions
        importlib.reload(ahjo.scripts.master_actions)

        # Load project config
        project_path = str(Path(anchor_path, ahjo_project))
        project_actions = ahjo_projects[ahjo_project]["actions"]
        project_config_path = ahjo_projects[ahjo_project]["config"]
        
        # Load logging config
        os.chdir(project_path)
        sys.path.append(os.getcwd())
        if load_conf(project_config_path).get("windows_event_log", False):
            fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger_winLog.ini'))
        else:
            fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))
        logger = getLogger('ahjo')
        logger.info('------')
        logger.info('Building ahjo project: ' + ahjo_project)

        # Import ahjo project actions
        os.chdir(anchor_parent_path_str)

        try:
            # Load user defined actions
            project_config_dict = load_conf(project_config_path)
            ahjo_action_files = project_config_dict.get("ahjo_action_files", DEFAULT_ACTIONS_SRC)
            
            for action_file in ahjo_action_files:

                action_source = action_file["source_file"]
                action_module = action_source.replace(".py", "").replace("/", ".").replace("\\", ".")
                action_name = action_file["name"]

                # Check if action file exists
                if not os.path.exists(anchor_name + "/" + ahjo_project + "/" + action_source):
                    logger.info(format_message(f"{action_name} not found"))
                    raise Exception(f"{action_name} not found")
                
                # Load actions
                sys.path.append(os.getcwd())
                importlib.import_module(anchor_name + "." + ahjo_project + "." + action_module)

                logger.info(format_message(f"Succesfully loaded {action_name}"))

        except Exception as e:
            logger.exception(format_message(f"Error while loading ahjo actions: {e}"))
            raise

        os.chdir(project_path)

        # Run ahjo actions
        for project_action in project_actions:
            execute_action(
                project_action, 
                project_config_path, 
                engine = master_engine, 
                skip_confirmation = skip_project_confirmation
            )
        
