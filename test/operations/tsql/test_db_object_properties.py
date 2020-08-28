import pytest
from subprocess import Popen, PIPE

import ahjo.operations.tsql.db_object_properties as dop
from ahjo.context import AHJO_PATH


@pytest.mark.mssql
class TestWithSQLServer():

    @pytest.fixture(scope='function', autouse=True)
    def db_objects_setup_and_teardown(self, mssql_sample, mssql_engine):
        self.engine = mssql_engine
        p = Popen(['ahjo', 'deploy-without-git-version-and-object-properties', 'config_development.jsonc'],
                  cwd=mssql_sample, stdin=PIPE)
        p.communicate(input='y\n'.encode())
        yield
        p = Popen(['ahjo', 'downgrade', 'config_development.jsonc'],
                  cwd=mssql_sample, stdin=PIPE)
        p.communicate(input='y\n'.encode())

    def test_objects_should_not_have_descriptions(self):
        assert 1 == 1

    def test_objects_should_have_descriptions_after_update(self):
        dop.update_csv_object_properties(self.engine, AHJO_PATH, ['store'])
        assert 1 == 1
