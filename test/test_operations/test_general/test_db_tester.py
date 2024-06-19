import pytest
import datetime
from os import chdir, getcwd
from ahjo.operations.general.db_tester import DatabaseTester
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, text, func

TABLE_NAME = "test_table"
SCHEMA = "dbo"
TEST_FILE = "database/tests/db_tester.sql"

@pytest.mark.mssql
class TestDBTesterWithSQLServer():

    @pytest.fixture(scope='function', autouse=True)
    def db_tester_mssql_setup_and_teardown(self, mssql_sample, mssql_engine, ahjo_context):

        old_cwd = getcwd()
        chdir(mssql_sample)
        self.engine = mssql_engine
        self.context = ahjo_context(mssql_sample)
        metadata = MetaData()
        self.test_table = Table(
            TABLE_NAME, 
            metadata,
            Column("batch_id", Integer),
            Column("start_time", DateTime),
            Column("end_time", DateTime, default=func.now()),
            Column("test_name", String),
            Column("issue", String),
            Column("result", String),
            Column("test_file", String),
            schema = SCHEMA
        )
        metadata.create_all(self.engine)
        self.db_tester = DatabaseTester(self.engine, self.test_table)

        yield

        with self.engine.connect() as connection:
            connection.execution_options(isolation_level="AUTOCOMMIT")
            with connection.begin():
                connection.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.{TABLE_NAME}"))
        chdir(old_cwd)

    def reflected_test_table(self):
        return Table(
            TABLE_NAME, MetaData(),
            autoload_with = self.engine,
            schema= SCHEMA
        )
    
    def test_db_tester_should_return_correct_number_of_rows(self):
        test_results = self.db_tester.execute_test_files(TEST_FILE)
        n_rows = len(test_results[TEST_FILE][1:])
        assert n_rows == 3

    def test_db_tester_should_return_correct_columns(self):
        test_results = self.db_tester.execute_test_files(TEST_FILE)
        expected_columns = ["start_time", "end_time", "test_name", "issue", "result"]
        assert test_results[TEST_FILE][0] == expected_columns

    def test_db_tester_should_return_datetime_objects(self):
        test_results = self.db_tester.execute_test_files(TEST_FILE)
        all_rows_are_datetime = True
        for row in test_results[TEST_FILE][1:]:
            if type(row[0]) != datetime.datetime or type(row[1]) != datetime.datetime:
                all_rows_are_datetime = False
                break
        assert all_rows_are_datetime

    def test_db_tester_should_return_correct_rows(self):
        test_results = self.db_tester.execute_test_files(TEST_FILE)
        all_rows_are_correct = True
        for i, row in enumerate(test_results[TEST_FILE][1:]):
            if not (
                row[2] == f"TEST-{i+1}" 
                and row[3] == f"ISSUE-{i+1}" 
                and row[4] == f"OK" if i != 1 else f"Failed"
            ):
                all_rows_are_correct = False
                break
        assert all_rows_are_correct

    def test_output_rowcount_should_be_equal_to_db_rowcount(self):
        self.db_tester.set_save_test_results_to_db(True)
        test_results = self.db_tester.execute_test_files(TEST_FILE)
        reflected_table = self.reflected_test_table()
        with self.engine.connect() as connection:
            result = connection.execute(reflected_table.select())
            rows = result.fetchall()
        assert len(rows) == len(test_results[TEST_FILE][1:])

    def test_output_rows_should_equal_to_db_rows(self):
        self.db_tester.set_save_test_results_to_db(True)
        test_results = self.db_tester.execute_test_files(TEST_FILE)
        reflected_table = self.reflected_test_table()

        with self.engine.connect() as connection:
            result = connection.execute(reflected_table.select())
            rows = result.fetchall()

        all_rows_are_equal = True
        for i, row in enumerate(rows):
            if not (
                row.start_time == test_results[TEST_FILE][i+1][0] 
                and row.end_time == test_results[TEST_FILE][i+1][1]
                and row.test_name == test_results[TEST_FILE][i+1][2]
                and row.issue == test_results[TEST_FILE][i+1][3]
                and row.result == test_results[TEST_FILE][i+1][4]
            ):
                all_rows_are_equal = False
                break

        assert all_rows_are_equal

    def test_batch_id_should_be_same_for_all_rows(self):
        self.db_tester.set_save_test_results_to_db(True)
        self.db_tester.execute_test_files(TEST_FILE)
        reflected_table = self.reflected_test_table()
        with self.engine.connect() as connection:
            result = connection.execute(reflected_table.select())
            rows = result.fetchall()
        assert len(set([row.batch_id for row in rows])) == 1

    def test_test_file_is_saved_to_db(self):
        self.db_tester.set_save_test_results_to_db(True)
        self.db_tester.execute_test_files(TEST_FILE)
        reflected_table = self.reflected_test_table()
        with self.engine.connect() as connection:
            result = connection.execute(reflected_table.select())
            rows = result.fetchall()
        assert set([row.test_file for row in rows]) == {TEST_FILE}

    def test_db_tester_should_not_save_results_to_db_by_default(self):
        self.db_tester.execute_test_files(TEST_FILE)
        reflected_table = self.reflected_test_table()
        with self.engine.connect() as connection:
            result = connection.execute(reflected_table.select())
            rows = result.fetchall()
        assert len(rows) == 0