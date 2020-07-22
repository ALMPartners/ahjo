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


@action('deploy-without-object-properties', True, ['init'])
def deploy_without_object_properties_action(context):
    op.upgrade_db_to_latest_alembic_version(context.config_filename)
    op.deploy_sqlfiles(context.get_conn_info(), "./database/functions/", "Deploying functions")
    op.deploy_sqlfiles(context.get_conn_info(), "./database/views/", "Deploying views")
    op.deploy_sqlfiles(context.get_conn_info(), "./database/procedures/", "Deploying procedures")

#create_multiaction("complete-build", ["init", "structure", "deploy", "data", "testdata", "test"])
