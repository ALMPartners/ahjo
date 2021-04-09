import ahjo.database_utilities.sqla_utilities as ahjo
import pytest
from sqlalchemy.engine.url import URL

CONN_INFO = [{
    'host': 'localhost',
    'port': 5432,
    'server': 'localhost,5432',
    'database': 'DB_NAME',
    'driver': 'Postgre SQL Unicode',
    'dialect': 'postgresql',
    'username': 'postgres',
    'password': 'moimoi',
    'azure_auth': None
},
    {
    'host': 'localhost',
    'port': 1433,
    'server': 'localhost,1433',
    'database': 'DB_NAME',
    'driver': 'ODBC Driver 17 for SQL Server',
    'dialect': 'mssql+pyodbc',
    'username': 'sa',
    'password': 'SALA_kala12',
    'azure_auth': 'ActiveDirectoryPassword'
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
    if conn_info['azure_auth']:
        assert f"Database={conn_info['database']}" in url.query['odbc_connect']


def test_create_sqlalchemy_url_should_return_url_for_postgresql_postgres_db():
    conn_info = CONN_INFO[0]
    url = ahjo.create_sqlalchemy_url(conn_info, use_master_db=True)
    assert url.database == 'postgres'


def test_create_sqlalchemy_url_should_return_url_for_mssql_master_db():
    conn_info = CONN_INFO[1]
    url = ahjo.create_sqlalchemy_url(conn_info, use_master_db=True)
    assert url.database == 'master'
    assert 'Database=master' in url.query['odbc_connect']

#@pytest.mark.mssql
#class TestWithSQLServer():
#
#    @pytest.fixture(scope='function', autouse=True)
#    def sqla_utilities_mssql_setup_and_teardown(self, mssql_engine):
#        self.engine = mssql_engine