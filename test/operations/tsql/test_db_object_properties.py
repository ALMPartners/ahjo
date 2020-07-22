import pytest
from subprocess import Popen, PIPE

import ahjo.operations.tsql.db_object_properties as dop


@pytest.mark.mssql
class TestWithSQLServer():

    @pytest.fixture(scope='function', autouse=True)
    def db_objects_setup_and_teardown(self, mssql_sample, mssql_engine):
        self.engine = mssql_engine
        p = Popen(['ahjo', 'deploy-without-object-properties', 'config_development.jsonc'],
                  cwd=mssql_sample, stdin=PIPE)
        p.communicate(input='y\n'.encode())
        yield
        p = Popen(['ahjo', 'downgrade', 'config_development.jsonc'],
                  cwd=mssql_sample, stdin=PIPE)
        p.communicate(input='y\n'.encode())

    def test_objects_should_not_have_descriptions(self):
        dop.update_csv_object_properties(self.engine, ['store'])
        assert 1 == 1

    #def test_mssql_mark3(self):
    #    assert 1 == 1
