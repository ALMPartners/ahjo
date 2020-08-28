from ahjo.action import action
from ahjo.database_utilities import execute_query
from ahjo.operation_manager import OperationManager
from ahjo import operations as op


@action("delete-database", True, ['init'])
def delete_database_action(context):
    with OperationManager('Deleting database'):
        engine = context.get_master_engine()
        database = context.configuration.get('target_database_name')
        database_id = execute_query(engine, query='SELECT db_id(?)', variables=[database])[0]
        session_ids = execute_query(engine,
            query='SELECT session_id FROM sys.dm_exec_sessions WHERE database_id = ?', variables=[database_id])
        for sid in session_ids:
            execute_query(engine, f'KILL {sid.session_id}')
        execute_query(engine, f'DROP DATABASE {database}')


@action('drop-git-and-alembic-version-if-exists', True, ["deploy"])
def drop_git_version_exists_action(context):
    with OperationManager('Dropping Git and Alembic version tables'):
        engine = context.get_engine()
        git_table = context.configuration.get('git_table', 'dbo')
        git_table_schema = context.configuration.get('git_table_schema', 'git_table')
        git_table_full = git_table_schema + '.' + git_table
        execute_query(engine, query=f"DROP TABLE IF EXISTS {git_table_full}")
        alembic_table = context.configuration.get('alembic_version_table', 'dbo')
        alembic_table_schema = context.configuration.get('alembic_version_table_schema', 'alembic_version')
        alembic_table_full = alembic_table_schema + '.' + alembic_table
        execute_query(engine, query=f"DROP TABLE IF EXISTS {alembic_table_full}")


@action('deploy-without-git-version-and-object-properties', True, ['init'])
def deploy_without_git_version_and_object_properties_action(context):
    op.upgrade_db_to_latest_alembic_version(context.config_filename)
    op.deploy_sqlfiles(context.get_conn_info(), "./database/functions/", "Deploying functions")
    op.deploy_sqlfiles(context.get_conn_info(), "./database/views/", "Deploying views")
    op.deploy_sqlfiles(context.get_conn_info(), "./database/procedures/", "Deploying procedures")

#create_multiaction("complete-build", ["init", "structure", "deploy", "data", "testdata", "test"])
