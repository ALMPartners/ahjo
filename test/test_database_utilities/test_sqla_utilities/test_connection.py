import pytest
import ahjo.database_utilities.sqla_utilities as sqla_utils
from os import chdir, getcwd


@pytest.mark.mssql
class TestDBConnectionWithSQLServer:

    @pytest.fixture(scope="function", autouse=True)
    def test_connection_mssql_setup_and_teardown(
        self, mssql_sample, mssql_engine, ahjo_context
    ):

        old_cwd = getcwd()
        chdir(mssql_sample)
        self.engine = mssql_engine
        self.context = ahjo_context(mssql_sample)

        yield

        chdir(old_cwd)

    def test_connection_should_succeed(self):
        assert sqla_utils.test_connection(self.engine)

    def test_try_pyodbc_connection_should_succeed(self):
        result = sqla_utils.try_pyodbc_connection(self.engine)
        assert result[0] == 0 and result[1] == None

    def test_try_sqla_connection_should_succeed(self):
        result = sqla_utils.try_sqla_connection(self.engine)
        assert result[0] == 0 and result[1] == None

    def test_connection_should_fail(self):
        assert sqla_utils.test_connection(None) == False

    def test_try_pyoconnection_should_fail(self):
        result = sqla_utils.try_pyodbc_connection(None)
        assert result[0] == 1

    def test_try_sqla_connection_should_return_retry_code_on_failure(self):
        result = sqla_utils.try_sqla_connection(None)
        assert result[0] == -1
