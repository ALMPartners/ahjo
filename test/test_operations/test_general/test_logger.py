from os import chdir, getcwd

import pytest
from ahjo.logging import setup_ahjo_logger
from ahjo.interface_methods import display_message
from ahjo.operations.general import sqlfiles
from ahjo.operations.tsql import display_db_info
from ahjo.operation_manager import OperationManager
from ahjo.database_utilities.sqla_utilities import add_db_logger_listeners_to_engine
from sqlalchemy.sql import text

PRODUCTCATEGORY = "store.ProductCategory"
PRODUCT_COUNT = f"SELECT COUNT(*) FROM {PRODUCTCATEGORY}"
AHJO_LOG_TABLE = "dbo.ahjo_log"
DB_HANDLER_BUFFER_SIZE = 100


@pytest.mark.mssql
class TestDBLoggerWithSQLServer:

    @pytest.fixture(scope="function", autouse=True)
    def db_logging_mssql_setup_and_teardown(
        self,
        ahjo_config,
        mssql_sample,
        mssql_engine,
        run_alembic_action,
        drop_mssql_objects,
        ahjo_context,
    ):
        self.config = ahjo_config(mssql_sample)
        self.context = ahjo_context(mssql_sample)
        self.logger = setup_ahjo_logger(enable_database_log=True, context=self.context)
        self.alembic_table = (
            self.config["alembic_version_table_schema"]
            + "."
            + self.config["alembic_version_table"]
        )
        self.engine = add_db_logger_listeners_to_engine(
            mssql_engine, self.get_db_logger_handler()
        )
        old_cwd = getcwd()
        chdir(mssql_sample)
        run_alembic_action("upgrade", "head")
        yield
        drop_mssql_objects(self.engine)
        run_alembic_action("downgrade", "base")
        with self.engine.begin() as connection:
            connection.execute(text(f"DROP TABLE {self.alembic_table}"))
            connection.execute(text("DROP TABLE dbo.ahjo_log"))
        chdir(old_cwd)

    def test_deploy_sql_from_file_should_log_to_db(self):
        sqlfiles.deploy_sql_from_file(
            file=f"database/data/{PRODUCTCATEGORY}.sql",
            connectable=self.engine,
            display_output=False,
            scripting_variables=None,
        )
        self.flush_handler()
        excepted_row_exists = False
        with self.engine.begin() as connection:
            result = connection.execute(
                text(f"SELECT * FROM {AHJO_LOG_TABLE}")
            ).fetchall()
            for row in result:
                if row[4] == f"Deployment of {PRODUCTCATEGORY}.sql completed":
                    assert (row[2], row[3], row[5], row[8]) == (
                        "sqlfiles",
                        "INFO",
                        "sa",
                        self.config["url_of_remote_git_repository"],
                    )
                    excepted_row_exists = True
        if not excepted_row_exists:
            raise AssertionError("Log row not found in database")

    def test_deploy_sql_from_file_should_not_log_to_db_without_flush(self):
        sqlfiles.deploy_sql_from_file(
            file=f"database/data/{PRODUCTCATEGORY}.sql",
            connectable=self.engine,
            display_output=False,
            scripting_variables=None,
        )
        with self.engine.begin() as connection:
            result = connection.execute(text("SELECT * FROM dbo.ahjo_log")).fetchall()
            assert len(result) == 0

    def test_db_logger_should_flush_when_capacity_reached(self):
        self.empty_log_table()
        for i in range(DB_HANDLER_BUFFER_SIZE + 1):
            self.logger.info(f"Test row {i}")
        with self.engine.begin() as connection:
            result = connection.execute(
                text(f"SELECT * FROM {AHJO_LOG_TABLE}")
            ).fetchall()
            assert len(result) == DB_HANDLER_BUFFER_SIZE

    def test_db_logger_should_flush_when_handler_is_flushed(self):
        self.empty_log_table()
        self.logger.info("Test")
        self.flush_handler()
        with self.engine.begin() as connection:
            result = connection.execute(
                text(f"SELECT * FROM {AHJO_LOG_TABLE}")
            ).fetchall()
            assert len(result) == 1

    def test_db_logger_should_not_flush_when_capacity_not_reached(self):
        self.empty_log_table()
        for i in range(DB_HANDLER_BUFFER_SIZE - 1):
            self.logger.info(f"Test row {i}")
        with self.engine.begin() as connection:
            result = connection.execute(
                text(f"SELECT * FROM {AHJO_LOG_TABLE}")
            ).fetchall()
            assert len(result) == 0

    def test_db_logger_should_not_log_filtered_records(self):
        self.empty_log_table()

        display_message("Test", use_logger=True)
        display_db_info(self.context)
        self.logger.info("Test", extra={"record_class": "line"})

        self.flush_handler()
        with self.engine.begin() as connection:
            result = connection.execute(
                text(f"SELECT * FROM {AHJO_LOG_TABLE}")
            ).fetchall()
            assert len(result) == 0

    def test_db_formatter_should_format_records_correctly(self):
        self.empty_log_table()
        with OperationManager("Test"):
            pass
        self.flush_handler()
        with self.engine.begin() as connection:
            result = connection.execute(
                text(f"SELECT * FROM {AHJO_LOG_TABLE}")
            ).fetchall()
            assert result[0][4] == "Test"

    def test_db_handler_should_lock_within_transaction(self):
        with self.engine.begin() as connection:
            assert self.get_handler_lock_status() == True

    def test_db_handler_should_unlock_after_commit(self):
        with self.engine.begin() as connection:
            pass
        assert self.get_handler_lock_status() == False

    def test_db_handler_should_not_flush_when_locked(self):
        self.empty_log_table()
        with self.engine.begin() as connection:
            for i in range(DB_HANDLER_BUFFER_SIZE + 1):
                self.logger.info(f"Test row {i}")
            log_records = connection.execute(
                text(f"SELECT * FROM {AHJO_LOG_TABLE}")
            ).fetchall()
            assert (
                len(self.get_db_logger_handler().buffer) == DB_HANDLER_BUFFER_SIZE + 1
                and len(log_records) == 0
            )

    def empty_log_table(self):
        with self.engine.begin() as connection:
            connection.execute(text(f"DELETE FROM {AHJO_LOG_TABLE}"))

    def get_db_logger_handler(self):
        for handler in self.logger.handlers:
            if handler.name == "handler_database":
                return handler
        return None

    def flush_handler(self):
        for handler in self.logger.handlers:
            if handler.name == "handler_database":
                handler.flush()

    def get_handler_lock_status(self):
        for handler in self.logger.handlers:
            if handler.name == "handler_database":
                return handler.locked
        return None
