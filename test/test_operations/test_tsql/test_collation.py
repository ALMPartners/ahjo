from ahjo.operations.tsql.db_info import get_collation

import pytest


@pytest.mark.mssql
class TestWithSQLServer:

    @pytest.fixture(scope="function", autouse=True)
    def collation_setup(self, mssql_sample, ahjo_config, mssql_engine):
        self.config = ahjo_config(mssql_sample)
        self.engine = mssql_engine

    def test_collation_info_should_exist(self):
        collation, _, server_edition = get_collation(
            self.engine, self.config["target_database_name"]
        )
        assert collation is not None and server_edition is not None
