import ahjo.scripts.master_actions
import os
import importlib
import sys
from ahjo.database_utilities import create_conn_info, create_sqlalchemy_url
from ahjo.interface_methods import load_json_conf
from ahjo.action import execute_action
from ahjo.operation_manager import format_message
from logging import getLogger
from logging.config import fileConfig
from pathlib import Path
from sqlalchemy import create_engine


def run_multi_project_build(master_config_path):

    # Load master-job config
    anchor_path = load_json_conf(master_config_path, "projects_path")
    config_conn_info = load_json_conf(master_config_path, "conn_info")
    ahjo_projects = load_json_conf(master_config_path, "projects")
    anchor_parent_path_str = str(Path(anchor_path).parent)
    anchor_name = Path(anchor_path).parts[-1]

    # Create sqlalchemy master engine
    master_engine = create_engine(
        create_sqlalchemy_url(
            create_conn_info(config_conn_info),
            use_master_db=True
        )
    )

    for ahjo_project in ahjo_projects:
        
        # Load project config
        project_path = str(Path(anchor_path, ahjo_project))
        project_actions = ahjo_projects[ahjo_project]["actions"]
        project_config_path = ahjo_projects[ahjo_project]["config"]
        
        # Load logging config
        os.chdir(project_path)
        sys.path.append(os.getcwd())
        fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))
        logger = getLogger('ahjo')
        logger.info('------')

        # Import ahjo actions
        os.chdir(anchor_parent_path_str)
        if os.path.exists(anchor_name + "/" + ahjo_project + '/ahjo_actions.py'):
            logger.debug(format_message('ahjo_actions found'))
            try:
                sys.path.append(os.getcwd())
                importlib.import_module(anchor_name + "." + ahjo_project + ".ahjo_actions")
                logger.info(format_message('Succesfully loaded ahjo_actions'))
            except:
                logger.exception(format_message('Error while loading ahjo_actions'))
                raise
        else:
            logger.info(format_message('ahjo_actions not found'))
        os.chdir(project_path)

        # Run ahjo actions
        for project_action in project_actions:
            execute_action(project_action, project_config_path, master_engine)
