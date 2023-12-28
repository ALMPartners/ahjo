import ahjo.database_utilities.sqla_utilities as ahjo
import pytest
from sqlalchemy.engine.url import URL

CONN_INFO = [
    {
        'host': 'localhost',
        'port': 5432,
        'server': 'localhost,5432',
        'database': 'DB_NAME',
        'driver': 'Postgre SQL Unicode',
        'dialect': 'postgresql',
        'username': 'postgres',
        'password': 'moimoi',
        'azure_auth': None,
        'odbc_trust_server_certificate': 'yes',
        'odbc_encrypt': 'no'
    },
    {
        'host': 'localhost',
        'port': 1433,
        'server': 'localhost,1433',
        'database': 'DB_NAME',
        'driver': 'ODBC Driver 18 for SQL Server',
        'dialect': 'mssql+pyodbc',
        'username': 'sa',
        'password': 'SALA_kala12',
        'azure_auth': 'ActiveDirectoryPassword',
        'odbc_trust_server_certificate': 'yes',
        'odbc_encrypt': 'no'
    },
    {
        'host': 'localhost',
        'port': 1433,
        'server': 'localhost,1433',
        'database': 'DB_NAME',
        'driver': 'ODBC Driver 18 for SQL Server',
        'dialect': 'mssql+pyodbc',
        'username': 'sa',
        'password': 'SALA_kala12',
        'azure_auth': 'ActiveDirectoryPassword',
        'odbc_trust_server_certificate': 'yes',
        'odbc_encrypt': 'no'
    }
]


@pytest.mark.filterwarnings('ignore::sqlalchemy.exc.SADeprecationWarning')
@pytest.mark.parametrize("conn_info", CONN_INFO)
def test_create_sqlalchemy_url_should_return_url_instance(conn_info):
    url = ahjo.create_sqlalchemy_url(conn_info)
    assert isinstance(url, URL)


@pytest.mark.parametrize("conn_info", CONN_INFO)
def test_create_sqlalchemy_url_should_return_url_for_given_db(conn_info):
    url = ahjo.create_sqlalchemy_url(conn_info, use_master_db=False)
    assert url.database == conn_info['database']


def test_create_sqlalchemy_url_should_return_url_for_postgresql_postgres_db():
    conn_info = CONN_INFO[0]
    url = ahjo.create_sqlalchemy_url(conn_info, use_master_db=True)
    assert url.database == 'postgres'


def test_create_sqlalchemy_url_should_return_url_for_mssql_master_db():
    conn_info = CONN_INFO[1]
    url = ahjo.create_sqlalchemy_url(conn_info, use_master_db=True)
    assert url.database == 'master'


def test_create_sqlalchemy_url_should_enable_odbc_trust_server_certificate():
    conn_info = CONN_INFO[2]
    url = ahjo.create_sqlalchemy_url(conn_info, use_master_db=True)
    trust_cert = url.query["TrustServerCertificate"]
    assert trust_cert == "yes"


def test_create_sqlalchemy_url_should_disable_odbc_encrypt():
    conn_info = CONN_INFO[2]
    url = ahjo.create_sqlalchemy_url(conn_info, use_master_db=True)
    assert url.query["Encrypt"] == "no"


def test_create_sqlalchemy_url_should_support_exact_odbc_connect_string():
    conn_info = {
        "dialect": "mssql+pyodbc",
        "odbc_connect": "DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost,1433;DATABASE=DB_NAME;UID=sa;PWD=SALA_kala12;TrustServerCertificate=no;Encrypt=yes"
    }
    url = ahjo.create_sqlalchemy_url(conn_info)
    assert url.drivername == "mssql+pyodbc"
    assert url.render_as_string() == "mssql+pyodbc://?odbc_connect=DRIVER%3D%7BODBC+Driver+18+for+SQL+Server%7D%3BSERVER%3Dlocalhost%2C1433%3BDATABASE%3DDB_NAME%3BUID%3Dsa%3BPWD%3DSALA_kala12%3BTrustServerCertificate%3Dno%3BEncrypt%3Dyes"