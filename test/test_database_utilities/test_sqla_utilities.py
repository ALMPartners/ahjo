from os import chdir, getcwd
from re import DOTALL, search

import ahjo.database_utilities.sqla_utilities as ahjo
import pytest
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import DBAPIError, ProgrammingError

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
}]

MSSQL_PATTERNS = ahjo.DIALECT_PATTERNS.get('mssql')


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


def test_remove_comments_should_remove_all_tsql_comments():
    tsql_with_comments = """/**This is comment*/
SELECT * FROM store.Clients -- Test
/**
Another comment GO
*/
GO
-- Another select
SELECT TOP 1 * FROM store.Clients
-- """
    tsql_without_comments = ahjo._remove_comments(
        dialect_patterns=MSSQL_PATTERNS,
        sql=tsql_with_comments
        )
    comments = MSSQL_PATTERNS.get('comment_patterns')
    for comment in comments:
        match = search(comment, tsql_without_comments, flags=DOTALL)
        assert match is None
    assert tsql_without_comments == "\nSELECT * FROM store.Clients \nGO\nSELECT TOP 1 * FROM store.Clients\n-- "


def test_insert_script_variables_should_replace_all_instances():
    sql_with_variables = """
SELECT * FROM store.Clients WHERE ZIP_VAR = '00180'
GO
-- Another select
SELECT TOP 1 * FROM CLIENT_TABLE
"""
    scripting_vars = {'ZIP_VAR': 'zip_code', 'CLIENT_TABLE': 'store.Clients'}
    sql_without_variables = ahjo._insert_script_variables(
        dialect_patterns={},
        sql=sql_with_variables,
        scripting_variables=scripting_vars
    )
    for key in scripting_vars:
        assert key not in sql_without_variables
    assert sql_without_variables == """
SELECT * FROM store.Clients WHERE zip_code = '00180'
GO
-- Another select
SELECT TOP 1 * FROM store.Clients
"""


def test_insert_script_variables_should_replace_all_tsql_variables():
    tsql_with_variables = """
SELECT * FROM store.Clients WHERE $(ZIP_VAR) = '00180'
GO
-- Another select
SELECT TOP 1 * FROM $(CLIENT_TABLE)
"""
    scripting_vars = {'ZIP_VAR': 'zip_code', 'CLIENT_TABLE': 'store.Clients'}
    tsql_without_variables = ahjo._insert_script_variables(
        dialect_patterns=MSSQL_PATTERNS,
        sql=tsql_with_variables,
        scripting_variables=scripting_vars
    )
    for key in scripting_vars:
        assert key not in tsql_without_variables
    assert tsql_without_variables == """
SELECT * FROM store.Clients WHERE zip_code = '00180'
GO
-- Another select
SELECT TOP 1 * FROM store.Clients
"""


def test_split_to_batches_should_split_tsql_with_go():
    tsql_with_batches = """SET NOCOUNT ON
GO
SELECT * FROM store.Clients
GO
-- GO AND UPDATE TABLE
EXEC store.UpdateClients
-- GOVERMENT"""
    batches = ahjo._split_to_batches(
        dialect_patterns=MSSQL_PATTERNS,
        sql=tsql_with_batches
    )
    assert len(batches) == 3
    assert batches[0] == 'SET NOCOUNT ON'


@pytest.mark.mssql
class TestWithPopulatedSQLServer():

    @pytest.fixture(scope='function', autouse=True)
    def sqla_utilities_mssql_setup_and_teardown(self, ahjo_config, mssql_sample, mssql_engine, run_alembic_action, deploy_mssql_objects, drop_mssql_objects, populate_table):
        self.config = ahjo_config(mssql_sample)
        self.alembic_table = self.config['alembic_version_table_schema'] + \
            '.' + self.config['alembic_version_table']
        self.engine = mssql_engine
        old_cwd = getcwd()
        chdir(mssql_sample)
        run_alembic_action('upgrade', 'head')
        deploy_mssql_objects(self.engine)
        populate_table(self.engine, 'store.Clients')
        yield
        drop_mssql_objects(self.engine)
        run_alembic_action('downgrade', 'base')
        query = f"DROP TABLE {self.alembic_table}"
        self.engine.execute(query)
        chdir(old_cwd)

    def test_execute_query_should_return_rows(self):
        result = ahjo.execute_query(
            self.engine,
            query='SELECT * FROM store.Clients'
        )
        assert result

    def test_execute_query_should_accept_list_params(self):
        result = ahjo.execute_query(
            self.engine,
            query='SELECT * FROM store.Clients WHERE country = ?',
            variables=['Finland']
        )
        assert result

    def test_execute_query_should_accept_tuple_param(self):
        result = ahjo.execute_query(
            self.engine,
            query='SELECT * FROM store.Clients WHERE country = ?',
            variables=('Finland',)
        )
        assert result

    def test_execute_query_should_accept_tuple_params(self):
        result = ahjo.execute_query(
            self.engine,
            query='SELECT * FROM store.Clients WHERE country = ? AND zip_code = ?',
            variables=('Finland', '00180')
        )
        assert result

    def test_execute_query_should_not_accept_dict_params(self):
        with pytest.raises(DBAPIError):
            ahjo.execute_query(
                self.engine,
                query='SELECT * FROM store.Clients WHERE country = ? AND zip_code = ?',
                variables={'country': 'Finland', 'zip_code': '00180'}
            )

    def test_execute_query_should_not_accept_str_param(self):
        with pytest.raises(DBAPIError):
            ahjo.execute_query(
                self.engine,
                query='SELECT * FROM store.Clients WHERE country = ?',
                variables='Finland'
            )

    def test_execute_query_should_not_return_headers(self):
        result = ahjo.execute_query(
            self.engine, query='SELECT name FROM store.Clients')
        assert result[0][0] != 'name'

    def test_execute_query_should_return_headers(self):
        result = ahjo.execute_query(
            self.engine,
            query='SELECT name FROM store.Clients',
            include_headers=True
        )
        assert result[0][0] == 'name'

    def test_execute_query_should_return_rows_from_proc(self):
        result = ahjo.execute_query(
            self.engine,
            query='EXEC store.ReturnClients'
        )
        assert result

    def test_execute_query_should_not_return_rows_from_proc(self):
        result = ahjo.execute_query(
            self.engine,
            query='EXEC store.UpdateClients'
        )
        assert result == []

    def test_execute_query_should_raise_error_from_proc(self):
        with pytest.raises(ProgrammingError):
            ahjo.execute_query(self.engine, query='EXEC store.RaiseError')

    def test_execute_query_should_autocommit(self):
        ahjo.execute_query(
            self.engine,
            query="INSERT INTO store.Clients (name, phone) VALUES ('Test_1', 112), ('Test_2', 112)",
            isolation_level='AUTOCOMMIT'    # default
        )
        query = "SELECT name, phone FROM store.Clients WHERE phone = 112"
        result = self.engine.execute(query).fetchall()
        assert result[0] == ('Test_1', '112')
        assert result[1] == ('Test_2', '112')


    # execute_from_file
    # execute_try_catch
    # get_schema_names
