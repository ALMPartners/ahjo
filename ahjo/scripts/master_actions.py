# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""This script defines actions for the project.
The actions are imported to master.py, where they are executed.

This file can be broken to multiple files, as long as every action is imported to
'master.py' and create_multiaction-calls are made after the parts are already defined.
"""
from logging import getLogger
from os import path

import ahjo.operations as op
from ahjo.action import action, create_multiaction, registered_actions

console_logger = getLogger('ahjo.console')


@action('init-config', False)
def init_config_action(context):
    op.create_local_config_base(context.config_filename)


@action('init', True)
def init_action(context):
    # Create new engine connected to 'master' database
    master_engine = context.get_master_engine()
    try:
        db_name = context.configuration.get('target_database_name')
        db_path = context.configuration.get('database_data_path')
        log_path = context.configuration.get('database_log_path')
        init_size = context.configuration.get('database_init_size', 100)
        max_size = context.configuration.get('database_max_size', 10000)
        file_growth = context.configuration.get('database_file_growth', 500)
        compatibility_level = context.configuration.get('database_compatibility_level')
        collation = context.configuration.get('database_collation', 'Latin1_General_CS_AS')
        op.create_db(master_engine, db_name, db_path, log_path, init_size, max_size, file_growth, compatibility_level, collation)
    finally:
        master_engine.dispose()


@action('create-db-login', True, ['init'])
def create_db_login(context):
    login_name = context.configuration.get('target_database_name') + '_LOGIN'
    default_password = 'SALASANA'
    default_db = context.configuration.get('target_database_name')
    op.create_db_login(context.get_engine(), login_name, default_password, default_db)


@action('structure', True, ['init'])
def structure_action(context):
    success1 = op.deploy_sqlfiles(context.get_conn_info(), './database/schema/', 'Creating schemas')
    success2 = op.deploy_sqlfiles(context.get_conn_info(), './database/tables/', 'Creating tables')
    success3 = op.deploy_sqlfiles(context.get_conn_info(), './database/constraints/', 'Creating constraints')
    if success1 is False and success2 is False and success3 is False:
        console_logger.error('Failed to create database structure using primary method, attempting alternate method.')
        try:
            op.create_db_structure(context.get_conn_info())
        except:
            console_logger.error('Failed to create database structure using alternate method. File database/create_db_structure.sql does not exist.' \
                '\nRefer to the Ahjo documentation for creating database structure.\n------')


@action('deploy', True, ['init'])
def deploy_action(context):
    op.upgrade_db_to_latest_alembic_version(context.config_filename)
    op.deploy_sqlfiles(context.get_conn_info(), "./database/functions/", "Deploying functions")
    op.deploy_sqlfiles(context.get_conn_info(), "./database/views/", "Deploying views")
    op.deploy_sqlfiles(context.get_conn_info(), "./database/procedures/", "Deploying procedures")
    op.update_git_version(context.get_engine(),
                           context.configuration.get('git_table_schema', 'dbo'),
                           context.configuration.get('git_table'),
                           context.configuration.get('url_of_remote_git_repository'))


@action('assembly', True, ['init'])
def assembly_action(context):
    op.drop_sqlfile_objects(context.get_engine(), 'PROCEDURE', "./database/clr-procedures/", "Dropping CLR-procedures")
    op.drop_sqlfile_objects(context.get_engine(), 'ASSEMBLY', "./database/assemblies/", "Dropping assemblies")
    op.deploy_sqlfiles(context.get_conn_info(), "./database/assemblies/", "Deploying assemblies")
    op.deploy_sqlfiles(context.get_conn_info(), "./database/clr-procedures/", "Deploying CLR-procedures")


@action('data', True, ['deploy'])
def data_action(context):
    op.deploy_sqlfiles(context.get_conn_info(), './database/data/', "Inserting data")


@action('testdata', True, ['data'])
def testdata_acction(context):
    op.deploy_sqlfiles(context.get_conn_info(), './database/data/testdata/', "Inserting test data")


@action('create-db-permissions', True, ['init'])
def create_db_permissions(context):
    op.create_db_permissions(context.get_conn_info())


@action('downgrade', True, ["init"])
def downgrade_action(context):
    op.drop_sqlfile_objects(context.get_engine(), 'VIEW', "./database/views/", "Dropping views")
    op.drop_sqlfile_objects(context.get_engine(), 'PROCEDURE', "./database/procedures/", "Dropping procedures")
    op.drop_sqlfile_objects(context.get_engine(), 'FUNCTION', "./database/functions/", "Dropping functions")
    op.drop_sqlfile_objects(context.get_engine(), 'PROCEDURE', "./database/clr-procedures/", "Dropping CLR-procedures")
    op.drop_sqlfile_objects(context.get_engine(), 'ASSEMBLY', "./database/assemblies/", "Dropping assemblies")
    op.downgrade_db_to_alembic_base(context.config_filename)


@action('test', False, ["testdata"])
def test_action(context):
    op.deploy_sqlfiles(context.get_conn_info(), './database/tests/', "Running tests", display_output=True)


@action('version', False, ["init"])
def version_action(context):
    op.print_git_version(context.get_engine(), context.configuration.get('git_table_schema', 'dbo'), context.configuration.get('git_table'))
    op.print_alembic_version(context.get_engine(), context.configuration['alembic_version_table'])


@action('update-csv-obj-prop', False)
def update_csv_obj_prop(context):
    op.update_csv_object_properties(context.get_engine(), context.ahjo_path, context.configuration['metadata_allowed_schemas'])


create_multiaction("complete-build", ["init", "deploy", "data", "testdata", "test"])
