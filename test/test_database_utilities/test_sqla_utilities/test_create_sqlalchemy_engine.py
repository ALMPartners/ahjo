import pyodbc
from ahjo.database_utilities.sqla_utilities import create_sqlalchemy_engine, create_sqlalchemy_url
from sqlalchemy.engine import Engine

CONN_INFO = {
    'host': 'localhost',
    'port': 1433,
    'server': 'localhost,1433',
    'database': 'DB_NAME',
    'driver': 'ODBC Driver 18 for SQL Server',
    'dialect': 'mssql+pyodbc',
    'username': 'sa',
    'password': 'SALA_kala12',
    'odbc_encrypt': 'no',
    'odbc_trust_server_certificate': 'yes'
}


def test_create_sqlalchemy_engine_should_return_engine_instance():
    engine = create_sqlalchemy_engine(create_sqlalchemy_url(CONN_INFO))
    assert isinstance(engine, Engine)

def test_pyodb_pooling_should_be_false():
    create_sqlalchemy_engine(create_sqlalchemy_url(CONN_INFO))
    assert pyodbc.pooling == False
