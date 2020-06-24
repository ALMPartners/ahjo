from ahjo.action import action
from ahjo.database_utilities import execute_query
from ahjo.operation_manager import OperationManager


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

#create_multiaction("complete-build", ["init", "structure", "deploy", "data", "testdata", "test"])
