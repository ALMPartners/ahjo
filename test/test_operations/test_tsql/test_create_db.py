import pytest

from ahjo.operations.tsql.create_db import create_db
from sqlalchemy import text


@pytest.mark.mssql_init
class TestCreateDBWithSQLServer:
    """Test class for creating a database with SQL Server."""

    @pytest.fixture(scope="function", autouse=True)
    def db_create_setup_and_teardown(
        self, mssql_sample, ahjo_config, mssql_master_engine, ahjo_context
    ):
        self.config = ahjo_config(mssql_sample)
        self.engine = mssql_master_engine
        self.db_name = self.config["target_database_name"]
        self.context = ahjo_context(mssql_sample)

        yield

        with self.engine.connect() as connection:
            connection.execution_options(isolation_level="AUTOCOMMIT").execute(
                text(
                    f"IF EXISTS (SELECT name FROM sys.databases WHERE name = '{self.db_name}') DROP DATABASE {self.db_name}"
                )
            )
        self.engine.dispose()

    @pytest.mark.mssql_init
    def test_create_db(self):
        """Test creating a database."""

        db_name = self.context.get_conn_info().get("database")
        db_path = self.context.configuration.get("database_data_path")
        log_path = self.context.configuration.get("database_log_path")
        init_size = self.context.configuration.get("database_init_size", 100)
        max_size = self.context.configuration.get("database_max_size", 10000)
        file_growth = self.context.configuration.get("database_file_growth", 500)
        compatibility_level = self.context.configuration.get(
            "database_compatibility_level"
        )
        collation = self.context.configuration.get(
            "database_collation", "Latin1_General_CS_AS"
        )

        create_db(
            self.engine,
            db_name,
            db_path,
            log_path,
            init_size,
            max_size,
            file_growth,
            compatibility_level,
            collation,
        )

        with self.engine.connect() as connection:
            result = connection.execute(
                text(f"SELECT name FROM sys.databases WHERE name = '{self.db_name}'")
            )
            db_name = result.fetchone()

        assert db_name is not None, "Database was not created successfully."
