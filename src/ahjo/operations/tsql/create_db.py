# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

'''Module for database drop and create.

Global variable QUERIES holds SQL select statements to
retrieve session and database ids from database.'''
from os import path
from typing import Union

from ahjo.database_utilities import execute_query
from ahjo.operation_manager import OperationManager
from sqlalchemy.engine import Engine

QUERIES = {
    'get_db_session': 'SELECT session_id FROM sys.dm_exec_sessions WHERE database_id = :database_id',
    'get_db_id': 'SELECT db_id(:db_name)',
    'get_existing_db': 'SELECT name from sys.databases where name = :db_name'
}


def create_db(engine: Engine, db_name: str, db_path: str, log_path: str, init_size: int, max_size: int, file_growth: int, compatibility_level: str, collation: str):
    '''First, kill all database sessions. Second, drop database if it exists.
    Third, create database according to given parameters.

    Arguments
    ---------
    engine
        SQL Alchemy engine connected to 'master' database.
    db_name
        Name of the database.
    db_path
        Path to database data file.
    log_path
        Path to database log file.
    init_size
        Initial size of database data file (MB).
    max_size
        Max size of database data file (MB).
    file_growth
        How much the database data file will grow when it runs out of space (MB).
    compatibility_level
        Compatibility level of database.
    collation
        Collation of database.
    '''
    def drop_database(database_id: Union[str, int]):
        '''Kill all connections to database and connections made by given login.
        Drop login and database.
        '''
        session_ids = execute_query(
            engine, QUERIES.get('get_db_session'),
            variables={"database_id": database_id}
        )
        for sid in session_ids:
            execute_query(engine, f'KILL {sid.session_id}')
        execute_query(engine, f'DROP DATABASE [{db_name}]')

    def create_database():
        '''Create database and alter its collation, compatibility level and recovery.'''
        # If filepaths are not given - do not specify database/log files and their size
        create_query = f"CREATE DATABASE [{db_name}]"
        if db_path is not None and log_path is not None:
            db_file = path.splitext(path.basename(db_path))[0] + '_dat'
            log_file = path.splitext(path.basename(log_path))[0] + '_log'
            init_size_str = f'{init_size}MB'
            max_size_str = f'{max_size}MB'
            file_growth_str = f'{file_growth}MB'
            create_query = create_query + f"""
                ON (
                NAME = {db_file},
                FILENAME = '{db_path}',
                SIZE = {init_size_str},
                MAXSIZE = {max_size_str},
                FILEGROWTH = {file_growth_str} )  
	            LOG ON  
	            ( 
                    NAME = {log_file},
	                FILENAME = '{log_path}', 
	                SIZE = 50MB,  
	                MAXSIZE = 5000MB,  
	                FILEGROWTH = 500MB 
	            	)"""
        execute_query(engine, create_query)
        if collation is not None:
            execute_query(
                engine,
                f'ALTER DATABASE [{db_name}] COLLATE {collation}'
            )
        if compatibility_level is not None:
            execute_query(
                engine,
                f'ALTER DATABASE [{db_name}] SET COMPATIBILITY_LEVEL = {compatibility_level}'
            )
        execute_query(engine, f'ALTER DATABASE [{db_name}] SET RECOVERY SIMPLE')

    with OperationManager('Creating database'):
        db_id = execute_query(
            engine,
            QUERIES.get('get_db_id'),
            variables={"db_name": db_name}
        )[0][0]
        if db_id is not None:
            drop_database(db_id)

        database = execute_query(
            engine,
            QUERIES.get('get_existing_db'),
            variables={"db_name": db_name}
        )
        if len(database) == 0:
            create_database()
