from os import chdir, getcwd

import ahjo.database_utilities.sqla_utilities as ahjo
import pytest
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.sql import text


@pytest.mark.mssql
class TestWithPopulatedSQLServer():

    @pytest.fixture(scope='function', autouse=True)
    def execute_query_mssql_setup_and_teardown(self, ahjo_config, mssql_sample, mssql_engine, run_alembic_action, deploy_mssql_objects, drop_mssql_objects, populate_table):
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
        with self.engine.begin() as connection:
            connection.execute(text(query))
        chdir(old_cwd)

    def test_execute_query_should_return_rows(self):
        result = ahjo.execute_query(
            self.engine,
            query='SELECT * FROM store.Clients'
        )
        assert result

    def test_execute_query_should_accept_dict_param(self):
        result = ahjo.execute_query(
            self.engine,
            query='SELECT * FROM store.Clients WHERE country = :country',
            variables={'country': 'Finland'}
        )
        assert result

    def test_execute_query_should_accept_dict_params(self):
        result = ahjo.execute_query(
            self.engine,
            query='SELECT * FROM store.Clients WHERE country = :country AND zip_code = :zip_code',
            variables={'country': 'Finland', 'zip_code': '00180'}
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

    def test_execute_query_should_accept_list_param(self):
        result = ahjo.execute_query(
            self.engine,
            query='SELECT * FROM store.Clients WHERE country = ?',
            variables=['Finland']
        )
        assert result

    def test_execute_query_should_accept_list_params(self):
        result = ahjo.execute_query(
            self.engine,
            query='SELECT * FROM store.Clients WHERE country = ? AND zip_code = ?',
            variables=['Finland', '00180']
        )
        assert result

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
        with self.engine.begin() as connection:
            result = connection.execute(text(query)).fetchall()
        assert result[0] == ('Test_1', '112')
        assert result[1] == ('Test_2', '112')
