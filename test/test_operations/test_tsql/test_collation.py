from ahjo.operations.tsql.db_info import get_db_info

import pytest


@pytest.mark.mssql
class TestDBInfoWithSQLServer:

    @pytest.fixture(scope="function", autouse=True)
    def db_info_setup(self, mssql_sample, ahjo_config, mssql_engine):
        self.config = ahjo_config(mssql_sample)
        self.engine = mssql_engine

    def test_db_info_should_return_non_empty_values(self):
        """Test that the get_db_info function returns non-empty values."""
        db_info = get_db_info(self.engine, self.config["target_database_name"])
        host_name = db_info.get("Host name")
        login_name = db_info.get("Login name")
        database = db_info.get("Database")
        database_collation = db_info.get("Database collation")
        sql_version = db_info.get("SQL version")
        server_edition = db_info.get("Server edition")

        assert (
            host_name is not None
            and host_name != ""
            and login_name is not None
            and login_name != ""
            and database is not None
            and database != ""
            and database_collation is not None
            and database_collation != ""
            and sql_version is not None
            and sql_version != ""
            and server_edition is not None
            and server_edition != ""
        )
