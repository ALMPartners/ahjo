import pytest
from sqlalchemy.sql import text
from sqlalchemy import Column, MetaData, String, Table, Integer
from sqlalchemy.engine import interfaces
from ahjo.operations.general.bulk_insert import bulk_insert_into_database

BULK_INSERT_TABLE = "bulk_insert_table"
BULK_INSERT_SCHEMA = "dbo"

# Generate test data
BULK_DATA = []
BULK_DATA_LEN = 3000
BULK_SMALL_DATA = []
BULK_SMALL_DATA_LEN = 10
COL_1_NAME = "ID"
COL_2_NAME = "col_1"

for i in range(0, BULK_DATA_LEN):
    row = {}
    row_number = i + 1
    row[COL_1_NAME] = row_number
    row[COL_2_NAME] = "Test string " + str(row_number)
    BULK_DATA.append(row)

for i in range(0, BULK_SMALL_DATA_LEN):
    row = {}
    row_number = i + 1
    row[COL_1_NAME] = row_number
    row[COL_2_NAME] = "Test string " + str(row_number)
    BULK_SMALL_DATA.append(row)

@pytest.mark.mssql
class TestWithSQLServer():

    @pytest.fixture(scope='function', autouse=True)
    def bulk_insert_mssql_setup_and_teardown(self, ahjo_config, mssql_sample, mssql_engine):
        self.engine = mssql_engine
        metadata = MetaData()
        bulk_insert_table = Table(
            BULK_INSERT_TABLE, 
            metadata,
            Column(COL_1_NAME, Integer, primary_key=True, autoincrement=True),
            Column(COL_2_NAME, String(50)),
            schema = BULK_INSERT_SCHEMA
        )
        metadata.create_all(self.engine)

        yield

        with self.engine.connect() as connection:
            connection.execution_options(isolation_level="AUTOCOMMIT")
            with connection.begin():
                connection.execute(text(f"DROP TABLE IF EXISTS {BULK_INSERT_SCHEMA}.{BULK_INSERT_TABLE}"))

    def reflected_bulk_insert_table(self):
        return Table(
            BULK_INSERT_TABLE, MetaData(),
            autoload_with=self.engine,
            schema=BULK_INSERT_SCHEMA
        )

    def test_bulk_insert_should_add_data_to_db(self):
        bulk_insert_into_database(
            self.engine, 
            self.reflected_bulk_insert_table(),
            BULK_DATA
        )
        with self.engine.connect() as connection:
            result = connection.execute(
                text(f"SELECT {COL_1_NAME}, {COL_2_NAME} FROM {BULK_INSERT_SCHEMA}.{BULK_INSERT_TABLE}")
            ).fetchall()
            assert BULK_DATA_LEN == len(result)
            for i in range(0, BULK_DATA_LEN):
                row_res = result[i]
                bulk_row = BULK_DATA[i]
                assert bulk_row[COL_1_NAME] == row_res[0]
                assert bulk_row[COL_2_NAME] == row_res[1]

    # If fast_executemany is enabled, the default values for use_insertmanyvalues 
    # and bind_typing are changed during the bulk insert operation.
    # The default values should be restored after the bulk insert operation.
    def test_bulk_insert_should_restore_default_values(self):
        assert self.engine.dialect.use_insertmanyvalues == True
        assert self.engine.dialect.bind_typing == interfaces.BindTyping.SETINPUTSIZES
        bulk_insert_into_database(self.engine, self.reflected_bulk_insert_table(), BULK_SMALL_DATA)
        assert self.engine.dialect.use_insertmanyvalues == True
        assert self.engine.dialect.bind_typing == interfaces.BindTyping.SETINPUTSIZES