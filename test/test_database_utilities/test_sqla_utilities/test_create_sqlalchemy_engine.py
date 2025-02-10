import pyodbc
from ahjo.database_utilities.sqla_utilities import (
    create_sqlalchemy_engine,
    create_sqlalchemy_url,
)
from sqlalchemy.engine import Engine, BindTyping

CONN_INFO = {
    "host": "localhost",
    "port": 1433,
    "server": "localhost,1433",
    "database": "DB_NAME",
    "driver": "ODBC Driver 18 for SQL Server",
    "dialect": "mssql+pyodbc",
    "username": "sa",
    "password": "SALA_kala12",
}

SQLA_URL = create_sqlalchemy_url(CONN_INFO)


def test_create_sqlalchemy_engine_should_return_engine_instance():
    engine = create_sqlalchemy_engine(SQLA_URL)
    assert isinstance(engine, Engine)


def test_pyodb_pooling_should_be_false():
    create_sqlalchemy_engine(SQLA_URL)
    assert pyodbc.pooling == False


def test_create_sqlalchemy_engine_should_change_echo():
    engine = create_sqlalchemy_engine(SQLA_URL, echo=True)
    assert engine.echo == True


def test_create_sqlalchemy_engine_should_change_use_insertmanyvalues():
    engine = create_sqlalchemy_engine(SQLA_URL, use_insertmanyvalues=False)
    assert engine.dialect.use_insertmanyvalues == False


def test_create_sqlalchemy_engine_should_change_use_setinputsizes():
    engine = create_sqlalchemy_engine(SQLA_URL, use_setinputsizes=False)
    engine.dialect.bind_typing == BindTyping.SETINPUTSIZES
