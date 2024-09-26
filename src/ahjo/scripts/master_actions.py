# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""This script defines actions for the project.
The actions are imported to master.py, where they are executed.

This file can be broken to multiple files, as long as every action is imported to
'master.py' and create_multiaction-calls are made after the parts are already defined.
"""
from logging import getLogger

import ahjo.operations as op
import ahjo.database_utilities as du
import networkx as nx
from ahjo.action import action, create_multiaction, registered_actions
from ahjo.operations.tsql.sqlfiles import deploy_mssql_sqlfiles
from ahjo.operations.general.db_tester import DatabaseTester
from ahjo.logging import setup_db_logger
from sqlalchemy import Column, Integer, String, DateTime, func, MetaData, Table, select
from sqlalchemy.sql import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import NoSuchTableError

logger = getLogger('ahjo')

# Default column definitions for ahjo test table
DEFAULT_TEST_TABLE_COLS = [
    Column("batch_id", Integer),
    Column("start_time", DateTime),
    Column("end_time", DateTime, default=func.now()),
    Column("test_name", String),
    Column("issue", String),
    Column("result", String),
    Column("test_file", String)
]


@action(connection_required=False)
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
    except:
        raise
    finally:
        if dispose_master_engine:

            master_engine.dispose()

            if context.configuration.get("enable_database_logging", False):
                # Create database log table
                try:
                    setup_db_logger(context, test_db_connection = False)
                except Exception as error:
                    logger.error(f"Error setting up logger: {str(error)}")
                    raise
                for handler in logger.handlers:
                    if handler.name == "handler_database":
                        handler.flush()
                        break
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
    cl_args = context.get_command_line_args()
    
    if not cl_args.get("skip_alembic_update", False):
        op.upgrade_db_to_latest_alembic_version(
            context.config_filename,
            connection = context.get_connection() if type(connectable) == Connection else None
        )

    op.deploy_sqlfiles(context.get_connectable(), "./database/functions/", "Deploying functions")
    op.deploy_sqlfiles(context.get_connectable(), "./database/views/", "Deploying views")
    op.deploy_sqlfiles(context.get_connectable(), "./database/procedures/", "Deploying procedures")

    if not cl_args.get("skip_git_update", False):
        op.update_git_version(
            context.get_connectable(),
            context.configuration.get('git_table_schema', 'dbo'),
            context.configuration.get('git_table', 'git_version'),
            repository = context.configuration.get('url_of_remote_git_repository'),
            git_version_info_path = context.configuration.get('git_version_info_path')
        )

    if not cl_args.get("skip_metadata_update", False):
        op.update_db_object_properties(
                context.get_connectable(),
                context.configuration.get('metadata_allowed_schemas')
        )


@action(affects_database=True, dependencies=['init'])
def deploy_files(context, **kwargs):
    """(MSSQL) Run 'alembic upgrade head' Deploy files. Update Git version."""
    cl_args = context.get_command_line_args()
    deploy_files = cl_args.get("files", [])

    if not (isinstance(deploy_files, list) and len(deploy_files) > 0):
        logger.warning('Check argument: "files".')
        return

    if not cl_args.get("skip_alembic_update", False):
        op.upgrade_db_to_latest_alembic_version(context.config_filename)

    op.deploy_sqlfiles(context.get_connectable(), deploy_files, "Deploying sql files")

    if not cl_args.get("skip_git_update", False):
        op.update_git_version(
            context.get_connectable(),
            context.configuration.get('git_table_schema', 'dbo'),
            context.configuration.get('git_table', 'git_version'),
            repository = context.configuration.get('url_of_remote_git_repository'),
            git_version_info_path = context.configuration.get('git_version_info_path')
        )


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
    cl_args = context.get_command_line_args()
    engine = context.get_engine()
    connectable = context.get_connectable()
    deploy_args = [connectable, "./database/data/", "Inserting data"]
    deploy_mssql_sqlfiles(*deploy_args) if engine.name == "mssql" else op.deploy_sqlfiles(*deploy_args)
    if not cl_args.get("skip_git_update", False):
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
def create_db_roles(context):
    """(MSSQL) Create database roles."""
    op.deploy_sqlfiles(
        connectable = context.get_connectable(),
        data_src = "./database/permissions/create_db_roles.sql",
        message = "Creating database roles",
        display_output = False,
        scripting_variables = context.configuration.get("db_permissions_variables")
    )


@action(affects_database=True, dependencies=["create-db-roles"])
def grant_db_permissions(context):
    """(MSSQL) Grant permissions to roles."""
    op.deploy_sqlfiles(
        connectable = context.get_connectable(),
        data_src = "./database/permissions/grant_db_permissions.sql",
        message = "Granting permissions to roles",
        display_output = False,
        scripting_variables = context.configuration.get("db_permissions_variables")
    )


@action(affects_database=True, dependencies=["init"])
def create_db_users(context):
    """(MSSQL) Create database users."""
    op.deploy_sqlfiles(
        connectable = context.get_connectable(),
        data_src = "./database/permissions/create_db_users.sql",
        message = "Creating database users",
        display_output = False,
        scripting_variables = context.configuration.get("db_permissions_variables")
    )


@action(affects_database=True, dependencies=["create-db-roles", "create-db-users"])
def add_users_to_roles(context):
    """(MSSQL) Add users to roles."""
    op.deploy_sqlfiles(
        connectable = context.get_connectable(),
        data_src = "./database/permissions/add_users_to_db_roles.sql",
        message = "Adding users to roles",
        display_output = False,
        scripting_variables = context.configuration.get("db_permissions_variables")
    )


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


@action(affects_database=True)
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
    """Run test files and optionally save the results to the database."""

    metadata = MetaData()
    connectable = context.get_connectable()
    test_table = None

    if context.configuration.get("save_test_results_to_db", False):

        test_table_name = context.configuration.get("test_table_name", "ahjo_tests")
        test_table_schema = context.configuration.get("test_table_schema", "dbo")

        try:
            # Load existing test table
            test_table = Table(
                test_table_name,
                metadata, 
                autoload_with = connectable, 
                schema = test_table_schema
            )
        except NoSuchTableError:
            if context.configuration.get("create_test_table_if_not_exists", True):
                logger.debug(f"Test table not found. Creating new test table.")
                # Default table format for test results
                test_table = Table(
                    test_table_name,
                    metadata,
                    *DEFAULT_TEST_TABLE_COLS,
                    schema = test_table_schema
                )
                metadata.create_all(connectable)
                logger.debug(f"Test table '{test_table_schema}.{test_table_name}' created.")
            else:
                raise Exception("Test table not found.")
        except Exception as error:
            raise error

    db_tester = DatabaseTester(
        connectable, 
        table = test_table, 
        save_test_results_to_db = context.configuration.get("save_test_results_to_db", False)
    )
    db_tester.execute_test_files("./database/tests/")


@action(affects_database=True, dependencies=["init"])
def create_test_table(context):
    """Create test table for test results."""
    try:
        metadata = MetaData()
        connectable = context.get_connectable()
        test_table_name = context.configuration.get("test_table_name", "ahjo_tests")
        test_table_schema = context.configuration.get("test_table_schema", "dbo")
        test_table = Table(
            test_table_name,
            metadata,
            *DEFAULT_TEST_TABLE_COLS,
            schema = test_table_schema
        )
        metadata.create_all(connectable, checkfirst=False)
        logger.info(f"Test table '{test_table_schema}.{test_table_name}' created.")
    except Exception as error:
        logger.error(f"Error creating test table: {str(error)}")
        return


@action(affects_database=True, dependencies=["init"])
def create_test_view(context):
    """Create test view for test results."""
    try:
        connectable = context.get_connectable()
        view_name = context.configuration.get("test_view_name", "vwAhjoTests")
        view_schema = context.configuration.get("test_view_schema", "dbo")
        metadata = MetaData()

        # Load table for view
        test_table = Table(
            context.configuration.get("test_table_name", "ahjo_tests"),
            MetaData(),
            autoload_with = connectable,
            schema = context.configuration.get("test_table_schema", "dbo")
        )

        # Create view
        test_view = du.view(
            view_name,
            metadata,
            select(
                test_table.columns.batch_id.label("batch_id"),
                test_table.columns.start_time.label("start_time"),
                test_table.columns.end_time.label("end_time"),
                test_table.columns.test_name.label("test_name"),
                test_table.columns.issue.label("issue"),
                test_table.columns.result.label("result"),
                test_table.columns.test_file.label("test_file")
            ),
            schema = view_schema
        )
        metadata.create_all(connectable, checkfirst=False)
        
    except Exception as error:
        logger.error(f"Error creating test view: {str(error)}")
        return
    logger.info(f"Test view '{view_schema}.{view_name}' created.")


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


@action()
def plot_dependency_graph(context, **kwargs):
    """(MSSQL) Plot dependency graph."""
    cl_args = context.get_command_line_args()
    deploy_files = cl_args.get("files", [])
    cl_layout = cl_args.get("layout")
    if not (isinstance(deploy_files, list) and len(deploy_files) > 0):
        deploy_files = ["./database/functions/", "./database/procedures/", "./database/views/", "./database/tables/"]

    G = op.create_dependency_graph(deploy_files)
    G.remove_nodes_from(list(nx.isolates(G)))

    op.plot_dependency_graph(
        G,
        layout = cl_layout[0].lower() if cl_layout is not None else "spring_layout"
    )


create_multiaction(
    "create-users-roles-and-permissions", 
    ["create-db-roles", "grant-db-permissions", "create-db-users", "add-users-to-roles"],
    description = "(MSSQL) Run 'create-db-roles', 'grant-db-permissions', 'create-db-users' and 'add-users-to-roles' actions."
)

create_multiaction(
    "complete-build",
    ["init", "deploy", "data", "testdata", "test"],
    description="(MSSQL) Run 'init', 'deploy', 'data', 'testdata' and 'test' actions."
)
