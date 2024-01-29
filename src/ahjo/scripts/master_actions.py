# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""This script defines actions for the project.
The actions are imported to master.py, where they are executed.

This file can be broken to multiple files, as long as every action is imported to
'master.py' and create_multiaction-calls are made after the parts are already defined.
"""
from logging import getLogger

import ahjo.operations as op
import ahjo.database_utilities as du
from ahjo.action import action, create_multiaction, registered_actions
from ahjo.operations.tsql.sqlfiles import deploy_mssql_sqlfiles
from sqlalchemy.sql import text
from sqlalchemy.engine import Connection

logger = getLogger('ahjo')


@action()
def init_config(context):
    """Create a local configuration file."""
    op.create_local_config_base(context.config_filename)


@action(affects_database=True)
def init(context):
    """(MSSQL) Create the database. If database exists, drop it first."""
    # Create new engine connected to 'master' database
    dispose_master_engine = True
    if context.master_engine is not None:
        master_engine = context.master_engine
        dispose_master_engine = False
    else:
        master_engine = context.get_master_engine()
    try:
        db_name = context.get_conn_info().get('database')
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
        if dispose_master_engine:
            master_engine.dispose()
        else:
            with master_engine.connect() as con:
                con.execute(text('USE ' + db_name + ';'))


@action(affects_database=True, dependencies=['init'])
def create_db_login(context):
    """(MSSQL) Create login to the database."""
    db_name = context.get_conn_info().get('database')
    login_name = db_name + '_LOGIN'
    default_password = 'SALASANA'
    default_db = db_name
    op.create_db_login(context.get_connectable(), login_name, default_password, default_db)


@action(affects_database=True, dependencies=['init'])
def structure(context):
    """(MSSQL) Create database structure (schemas, tables, constraints). Not available if these are created with alembic."""
    success1 = op.deploy_sqlfiles(context.get_connectable(), './database/schema/', 'Creating schemas')
    success2 = op.deploy_sqlfiles(context.get_connectable(), './database/tables/', 'Creating tables')
    success3 = op.deploy_sqlfiles(context.get_connectable(), './database/constraints/', 'Creating constraints')
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
    connectable = context.get_connectable()
    op.upgrade_db_to_latest_alembic_version(
        context.config_filename,
        connection = context.get_connection() if type(connectable) == Connection else None
    )
    op.deploy_sqlfiles(context.get_connectable(), "./database/functions/", "Deploying functions")
    op.deploy_sqlfiles(context.get_connectable(), "./database/views/", "Deploying views")
    op.deploy_sqlfiles(context.get_connectable(), "./database/procedures/", "Deploying procedures")
    op.update_git_version(
        context.get_connectable(),
        context.configuration.get('git_table_schema', 'dbo'),
        context.configuration.get('git_table', 'git_version'),
        repository = context.configuration.get('url_of_remote_git_repository'),
        git_version_info_path = context.configuration.get('git_version_info_path')
    )
    op.update_db_object_properties(
        context.get_connectable(),
        context.configuration.get('metadata_allowed_schemas')
    )

@action(affects_database=True, dependencies=['init'])
def deploy_files(context, **kwargs):
    """(MSSQL) Run 'alembic upgrade head' Deploy files. Update Git version."""
    deploy_files = kwargs["files"] if "files" in kwargs else None
    if isinstance(deploy_files, list) and len(deploy_files) > 0:
        op.upgrade_db_to_latest_alembic_version(context.config_filename)
        op.deploy_sqlfiles(context.get_connectable(), deploy_files, "Deploying sql files")
        op.update_git_version(
            context.get_connectable(),
            context.configuration.get('git_table_schema', 'dbo'),
            context.configuration.get('git_table', 'git_version'),
            repository = context.configuration.get('url_of_remote_git_repository'),
            git_version_info_path = context.configuration.get('git_version_info_path')
        )
    else :
        logger.warning('Check argument: "files".')
        return

@action(affects_database=True, dependencies=['init'])
def assembly(context):
    """(MSSQL) Drop and deploy CLR-procedures and assemblies."""
    op.drop_sqlfile_objects(context.get_connectable(), 'PROCEDURE', "./database/clr-procedures/", "Dropping CLR-procedures")
    op.drop_sqlfile_objects(context.get_connectable(), 'ASSEMBLY', "./database/assemblies/", "Dropping assemblies")
    op.deploy_sqlfiles(context.get_connectable(), "./database/assemblies/", "Deploying assemblies")
    op.deploy_sqlfiles(context.get_connectable(), "./database/clr-procedures/", "Deploying CLR-procedures")


@action(affects_database=True, dependencies=['deploy'])
def data(context):
    """Insert data."""
    engine = context.get_engine()
    connectable = context.get_connectable()
    deploy_args = [connectable, "./database/data/", "Inserting data"]
    deploy_mssql_sqlfiles(*deploy_args) if engine.name == "mssql" else op.deploy_sqlfiles(*deploy_args)
    op.update_git_version(
        connectable,
        context.configuration.get('git_table_schema', 'dbo'),
        context.configuration.get('git_table', 'git_version'),
        repository = context.configuration.get('url_of_remote_git_repository'),
        git_version_info_path = context.configuration.get('git_version_info_path')
    )


@action(affects_database=True, dependencies=['deploy'])
def update_git_version(context):
    """Store the Git remote, branch and commit information to database."""
    op.update_git_version(
        context.get_connectable(),
        context.configuration.get('git_table_schema', 'dbo'),
        context.configuration.get('git_table', 'git_version'),
        repository = context.configuration.get('url_of_remote_git_repository'),
        git_version_info_path = context.configuration.get('git_version_info_path')
    )


@action(affects_database=True, dependencies=['data'])
def testdata(context):
    """Insert testdata."""
    op.deploy_sqlfiles(context.get_connectable(), './database/data/testdata/', "Inserting test data")


@action(affects_database=True, dependencies=['init'])
def create_db_permissions(context):
    """(MSSQL) Set permissions for users."""
    invoke_method = context.configuration.get("db_permission_invoke_method", "sqlalchemy")
    connection = context.get_connectable() if invoke_method == "sqlalchemy" else context.get_conn_info()
    kwargs = dict(
        connection = connection,
        db_permissions = context.configuration.get("db_permissions")
    )
    op.create_db_permissions(**{k: v for k, v in kwargs.items() if v is not None})


@action(affects_database=True, dependencies=["init"])
def drop(context):
    """(MSSQL) Drop views, procedures, functions and clr-procedures."""
    op.drop_sqlfile_objects(context.get_connectable(), 'VIEW', "./database/views/", "Dropping views")
    op.drop_sqlfile_objects(context.get_connectable(), 'PROCEDURE', "./database/procedures/", "Dropping procedures")
    op.drop_sqlfile_objects(context.get_connectable(), 'FUNCTION', "./database/functions/", "Dropping functions")
    op.drop_sqlfile_objects(context.get_connectable(), 'PROCEDURE', "./database/clr-procedures/", "Dropping CLR-procedures")
    op.drop_sqlfile_objects(context.get_connectable(), 'ASSEMBLY', "./database/assemblies/", "Dropping assemblies")

@action(affects_database=True, dependencies=["init"])
def drop_files(context, **kwargs):
    """(MSSQL) Drop sql file objects."""
    files = kwargs["files"] if "files" in kwargs else None
    if not(isinstance(files, list) and len(files) > 0):
        logger.warning('Check variable: "files".')
        return
        
    object_type = kwargs["object_type"] if "object_type" in kwargs else None
    if not(isinstance(object_type, str) and len(object_type) > 0):
        logger.warning('Check variable: "object_type".')
        return

    op.drop_sqlfile_objects(context.get_connectable(), object_type, files, "Dropping files")

@action('drop-obsolete', True)
def drop_obsolete(context):
    """Drop obsolete database objects."""
    du.execute_from_file(
        context.get_connectable(),
        './database/drop_obsolete_objects.sql'
    )

@action(affects_database=True, dependencies=["init"])
def downgrade(context):
    """(MSSQL) Drop views, procedures, functions and clr-procedures. Run 'alembic downgrade'."""
    connectable = context.get_connectable()
    op.drop_sqlfile_objects(connectable, 'VIEW', "./database/views/", "Dropping views")
    op.drop_sqlfile_objects(connectable, 'PROCEDURE', "./database/procedures/", "Dropping procedures")
    op.drop_sqlfile_objects(connectable, 'FUNCTION', "./database/functions/", "Dropping functions")
    op.drop_sqlfile_objects(connectable, 'PROCEDURE', "./database/clr-procedures/", "Dropping CLR-procedures")
    op.drop_sqlfile_objects(connectable, 'ASSEMBLY', "./database/assemblies/", "Dropping assemblies")
    op.downgrade_db_to_alembic_base(context.config_filename, connection = context.get_connection() if type(connectable) == Connection else None)


@action()
def test(context):
    """Run tests."""
    op.deploy_sqlfiles(context.get_connectable(), './database/tests/', "Running tests", display_output=True)


@action(dependencies=["deploy"])
def version(context):
    """Print Git and Alembic version."""
    op.print_git_version(
        context.get_connectable(),
        context.configuration.get('git_table_schema', 'dbo'),
        context.configuration.get('git_table', 'git_version')
    )
    op.print_alembic_version(
        context.get_connectable(),
        context.configuration['alembic_version_table']
    )


@action(dependencies=["deploy"])
def update_file_obj_prop(context):
    """(MSSQL) Update extended properties from database to files."""
    op.update_file_object_properties(
        context.get_connectable(),
        context.configuration.get('metadata_allowed_schemas')
        )


@action(affects_database=True, dependencies=["deploy"])
def update_db_obj_prop(context):
    """(MSSQL) Update extended properties from files to database."""
    op.update_db_object_properties(
        context.get_connectable(),
        context.configuration.get('metadata_allowed_schemas')
        )
                
    
create_multiaction("complete-build", ["init", "deploy", "data", "testdata", "test"],
                   description="(MSSQL) Run 'init', 'deploy', 'data', 'testdata' and 'test' actions.")
