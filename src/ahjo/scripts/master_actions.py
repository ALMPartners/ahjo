# Ahjo - Database deployment framework
#
# Copyright 2019, 2020 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""This script defines actions for the project.
The actions are imported to master.py, where they are executed.

This file can be broken to multiple files, as long as every action is imported to
'master.py' and create_multiaction-calls are made after the parts are already defined.
"""
from logging import getLogger

import ahjo.operations as op
from ahjo.action import action, create_multiaction, registered_actions

logger = getLogger('ahjo')


@action()
def init_config(context):
    """Create a local configuration file."""
    op.create_local_config_base(context.config_filename)


@action(affects_database=True)
def init(context):
    """(MSSQL) Create the database. If database exists, drop it first."""
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
        op.create_db(master_engine, db_name, db_path, log_path, init_size,
                     max_size, file_growth, compatibility_level, collation)
    finally:
        master_engine.dispose()


@action(affects_database=True, dependencies=['init'])
def create_db_login(context):
    """(MSSQL) Create login to the database."""
    login_name = context.configuration.get('target_database_name') + '_LOGIN'
    default_password = 'SALASANA'
    default_db = context.configuration.get('target_database_name')
    op.create_db_login(context.get_engine(),
                       login_name, default_password, default_db)


@action(affects_database=True, dependencies=['init'])
def structure(context):
    """(MSSQL) Create database structure (schemas, tables, constraints). Not available if these are created with alembic."""
    success1 = op.deploy_sqlfiles(context.get_conn_info(), './database/schema/', 'Creating schemas')
    success2 = op.deploy_sqlfiles(context.get_conn_info(), './database/tables/', 'Creating tables')
    success3 = op.deploy_sqlfiles(context.get_conn_info(), './database/constraints/', 'Creating constraints')
    if success1 is False and success2 is False and success3 is False:
        logger.error(
            'Failed to create database structure using primary method, attempting alternate method.')
        try:
            op.create_db_structure(context.get_conn_info())
        except:
            logger.error('Failed to create database structure using alternate method. File database/create_db_structure.sql does not exist.'
                         '\nRefer to the Ahjo documentation for creating database structure.\n------')


@action(affects_database=True, dependencies=['init'])
def deploy(context):
    """(MSSQL) Run 'alembic upgrade head'. Deploy functions, views and prodecures. Update extended properties and Git version."""
    op.upgrade_db_to_latest_alembic_version(context.config_filename)
    op.deploy_sqlfiles(context.get_conn_info(), "./database/functions/", "Deploying functions")
    op.deploy_sqlfiles(context.get_conn_info(), "./database/views/", "Deploying views")
    op.deploy_sqlfiles(context.get_conn_info(), "./database/procedures/", "Deploying procedures")
    op.update_db_object_properties(
        context.get_engine(),
        context.configuration.get('metadata_allowed_schemas')
        )
    op.update_git_version(
        context.get_engine(),
        context.configuration.get('git_table_schema', 'dbo'),
        context.configuration.get('git_table'),
        context.configuration.get('url_of_remote_git_repository')
        )


@action(affects_database=True, dependencies=['init'])
def assembly(context):
    """"(MSSQL) Drop and deploy CLR-procedures and assemblies."""
    op.drop_sqlfile_objects(context.get_engine(), 'PROCEDURE', "./database/clr-procedures/", "Dropping CLR-procedures")
    op.drop_sqlfile_objects(context.get_engine(), 'ASSEMBLY', "./database/assemblies/", "Dropping assemblies")
    op.deploy_sqlfiles(context.get_conn_info(), "./database/assemblies/", "Deploying assemblies")
    op.deploy_sqlfiles(context.get_conn_info(), "./database/clr-procedures/", "Deploying CLR-procedures")


@action(affects_database=True, dependencies=['deploy'])
def data(context):
    """(MSSQL) Insert data."""
    op.deploy_sqlfiles(context.get_conn_info(), './database/data/', "Inserting data")


@action(affects_database=True, dependencies=['data'])
def testdata(context):
    """(MSSQL) Insert testdata."""
    op.deploy_sqlfiles(context.get_conn_info(), './database/data/testdata/', "Inserting test data")


@action(affects_database=True, dependencies=['init'])
def create_db_permissions(context):
    """(MSSQL) Set permissions for users."""
    op.create_db_permissions(context.get_conn_info())


@action(affects_database=True, dependencies=["init"])
def drop(context):
    """(MSSQL) Drop views, procedures, functions and clr-procedures."""
    op.drop_sqlfile_objects(context.get_engine(), 'VIEW', "./database/views/", "Dropping views")
    op.drop_sqlfile_objects(context.get_engine(), 'PROCEDURE', "./database/procedures/", "Dropping procedures")
    op.drop_sqlfile_objects(context.get_engine(), 'FUNCTION', "./database/functions/", "Dropping functions")
    op.drop_sqlfile_objects(context.get_engine(), 'PROCEDURE', "./database/clr-procedures/", "Dropping CLR-procedures")
    op.drop_sqlfile_objects(context.get_engine(), 'ASSEMBLY', "./database/assemblies/", "Dropping assemblies")


@action(affects_database=True, dependencies=["init"])
def downgrade(context):
    """(MSSQL) Drop views, procedures, functions and clr-procedures. Run 'alembic downgrade'."""
    op.drop_sqlfile_objects(context.get_engine(), 'VIEW', "./database/views/", "Dropping views")
    op.drop_sqlfile_objects(context.get_engine(), 'PROCEDURE', "./database/procedures/", "Dropping procedures")
    op.drop_sqlfile_objects(context.get_engine(), 'FUNCTION', "./database/functions/", "Dropping functions")
    op.drop_sqlfile_objects(context.get_engine(), 'PROCEDURE', "./database/clr-procedures/", "Dropping CLR-procedures")
    op.drop_sqlfile_objects(context.get_engine(), 'ASSEMBLY', "./database/assemblies/", "Dropping assemblies")
    op.downgrade_db_to_alembic_base(context.config_filename)


@action()
def test(context):
    """(MSSQL) Run tests."""
    op.deploy_sqlfiles(context.get_conn_info(), './database/tests/', "Running tests", display_output=True)


@action(dependencies=["deploy"])
def version(context):
    """Print Git and Alembic version."""
    op.print_git_version(
        context.get_engine(),
        context.configuration.get('git_table_schema', 'dbo'),
        context.configuration.get('git_table')
        )
    op.print_alembic_version(
        context.get_engine(),
        context.configuration['alembic_version_table']
        )


@action(dependencies=["deploy"])
def update_file_obj_prop(context):
    """(MSSQL) Update extended properties to files."""
    op.update_file_object_properties(
        context.get_engine(),
        context.configuration.get('metadata_allowed_schemas')
        )


@action(affects_database=True, dependencies=["deploy"])
def update_db_obj_prop(context):
    """(MSSQL) Update extended properties to database."""
    op.update_db_object_properties(
        context.get_engine(),
        context.configuration.get('metadata_allowed_schemas')
        )


create_multiaction("complete-build", ["init", "deploy", "data", "testdata", "test"],
                   description="(MSSQL) Run 'init', 'deploy', 'data', 'testdata' and 'test' actions.")
