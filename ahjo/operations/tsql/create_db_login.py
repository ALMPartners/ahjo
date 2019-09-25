# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0


'''Module for login drop and create.

Global variable QUERIES holds SQL select statements to
retrieve session ids and login name from database.'''
from logging import getLogger

from ahjo.database_utilities import execute_query
from ahjo.operation_manager import OperationManager

console_logger = getLogger('ahjo.console')

QUERIES = {
    'get_login_session' : 'SELECT session_id FROM sys.dm_exec_sessions WHERE login_name = ?',
    'get_login_name' : 'SELECT loginname FROM master.dbo.syslogins WHERE name = ?'
}


def create_db_login(engine, login_name, login_password, default_db):
    '''First, kill all sessions related to login. Second, drop login.
    Third, create login with given password and default database.

    Overwrite example:
    ------------------
    @action('create-db-login', True, ['init'])
    def create_db_login(context):
        config_dict = merge_config_files(context.config_filename)
        login_name = config_dict.get('DJANGO', {}).get('KP_REP_DB_USRNAME', '$')
        login_password = config_dict.get('DJANGO', {}).get('KP_REP_DB_PW', '$')
        default_db = config_dict.get('DJANGO', {}).get('KP_REP_DB_NAME', '$')
        daop.create_db_login(context.engine, login_name, login_password, default_db)

    Arguments
    ---------
    engine : sqlalchemy.engine.Engine
        SQL Alchemy engine.
    login_name :str
        Login name.
    login_password : str
        Login password.
    default_db : str
        Default database of login.
    '''
    with OperationManager('Creating database login'):
        session_ids = execute_query(engine, QUERIES.get('get_login_session'), variables=[login_name])
        for sid in session_ids:
            execute_query(engine, f'KILL {sid.session_id}')
        login = execute_query(engine, QUERIES.get('get_login_name'), variables=[login_name])
        if len(login) > 0:
            execute_query(engine, f'DROP LOGIN {login_name}')
        if login_password == 'SALASANA':
            console_logger.info(f'Creating login {login_name} with default password.')
        create_query = f"""CREATE LOGIN {login_name} WITH PASSWORD='{login_password}',
            DEFAULT_DATABASE=[{default_db}], DEFAULT_LANGUAGE=[us_english],
            CHECK_EXPIRATION=OFF, CHECK_POLICY=OFF"""
        execute_query(engine, create_query)
