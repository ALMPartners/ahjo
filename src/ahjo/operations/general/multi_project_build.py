# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import ahjo.scripts.master_actions
import os
import importlib
import sys
from ahjo.database_utilities import create_conn_info, create_sqlalchemy_url, create_sqlalchemy_engine
from ahjo.interface_methods import load_conf, are_you_sure
from ahjo.action import execute_action, registered_actions, DEFAULT_ACTIONS_SRC
from ahjo.logging import setup_ahjo_logger
from ahjo.operation_manager import format_message
from ahjo.context import Context
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
        token = conn_info.get("token"),
        **conn_info.get("sqla_engine_params")
    )

    for ahjo_project in ahjo_projects:
        
        # Reload master actions & update global variable: registered_actions
        importlib.reload(ahjo.scripts.master_actions)

        # Load project config
        project_path = str(Path(anchor_path, ahjo_project))
        project_actions = ahjo_projects[ahjo_project]["actions"]
        project_config_path = ahjo_projects[ahjo_project]["config"]
        
        # Load ahjo logger
        try:
            os.chdir(project_path)
            sys.path.append(os.getcwd())
            project_config_dict = load_conf(project_config_path)
            context = Context(project_config_path, master_engine = master_engine)
            enable_db_logging = context.configuration.get("enable_database_logging", True)
            logger = setup_ahjo_logger(
                enable_database_log = enable_db_logging,
                enable_windows_event_log = project_config_dict.get("windows_event_log", False),
                enable_sqlalchemy_log = project_config_dict.get("enable_sqlalchemy_logging", False),
                context = context
            )
        except Exception as e:
            print(f"Error setting up logger: {str(e)}")
            raise

        logger.info('------')
        logger.info('Building ahjo project: ' + ahjo_project)

        # Import ahjo project actions
        os.chdir(anchor_parent_path_str)

        try:
            # Load user defined actions
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
            logger.error(format_message(f"Error while loading ahjo actions: {e}"))
            raise

        os.chdir(project_path)

        # Run ahjo actions
        action_failed = False
        for project_action in project_actions:
            try:
                execute_action(
                    project_action, 
                    project_config_path, 
                    context=context,
                    #engine = master_engine, 
                    skip_confirmation = skip_project_confirmation
                )
            except Exception:
                if enable_db_logging:
                    context.connection = None
                    context.engine = None
                    context.set_connectable("engine")
                    action_failed = True
                    break
        if enable_db_logging:
            for handler in logger.handlers:
                if handler.name == "handler_database":
                    handler.flush()

        if action_failed:
            sys.exit(1)

    sys.exit(0)