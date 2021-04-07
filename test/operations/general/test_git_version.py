from os import environ
from subprocess import check_output

import ahjo.operations.general.git_version as git
import pytest
from sqlalchemy import Column, MetaData, String, Table, select
from sqlalchemy.exc import NoSuchTableError


@pytest.fixture(scope='function')
def disable_git_setup_and_teardown():
    """Overwrite PATH variable.
    Works in WIN to 'disable' Git.
    """
    path_var = environ.get("PATH")
    environ["PATH"] = ""
    yield
    environ["PATH"] = path_var


def test_update_git_version_should_skip_when_no_git(disable_git_setup_and_teardown, caplog):
    git.update_git_version(None, 'dbo', 'git_version', 'repository')
    assert "Failed to retrieve Git commit. See log for detailed error message." in caplog.text


@pytest.mark.git
def test_update_git_version_should_skip_when_no_connection(caplog):
    git.update_git_version(None, 'dbo', 'git_version', 'repository')
    assert "Failed to update Git version table. See log for detailed error message." in caplog.text


@pytest.mark.mssql
class TestWithSQLServer():

    @pytest.fixture(scope='function', autouse=True)
    def git_version_mssql_setup_and_teardown(self, ahjo_config, mssql_sample, mssql_engine):
        config = ahjo_config(mssql_sample)
        self.git_table = config['git_table']
        self.git_table_schema = config['git_table_schema']
        self.sample_repository = config['url_of_remote_git_repository']
        self.engine = mssql_engine
        yield
        with self.engine.connect() as connection:
            connection.execution_options(isolation_level="AUTOCOMMIT")
            connection.execute(f"DROP TABLE IF EXISTS {self.git_table_schema}.{self.git_table}")

    def reflected_git_table(self):
        return Table(self.git_table, MetaData(),
                     autoload=True, autoload_with=self.engine,
                     schema=self.git_table_schema)

    def test_git_version_table_should_not_exist(self):
        with pytest.raises(NoSuchTableError):
            self.reflected_git_table()

    @pytest.mark.git
    def test_git_version_table_should_exist_after_update(self):
        git.update_git_version(self.engine, self.git_table_schema, self.git_table)
        git_version_table = self.reflected_git_table()
        git_version_table_columns = [col.name for col in git_version_table.c]
        assert 'Repository' in git_version_table_columns
        assert 'Branch' in git_version_table_columns
        assert 'Commit' in git_version_table_columns

    @pytest.mark.git
    def test_git_version_table_should_store_commit_after_update(self):
        git.update_git_version(self.engine, self.git_table_schema, self.git_table)
        git_version_table = self.reflected_git_table()
        result = self.engine.execute(
            select([
                git_version_table.c.Repository,
                git_version_table.c.Branch,
                git_version_table.c.Commit
            ]))
        row = result.fetchall()[0]
        git_remote = check_output(
            ["git", "remote", "get-url", "origin"]).decode('utf-8').strip()
        git_branch = check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode('utf-8').strip()
        git_commit = check_output(
            ["git", "describe", "--always", "--tags"]).decode('utf-8').strip()
        assert row.Repository == git_remote
        assert row.Branch == git_branch
        assert row.Commit == git_commit

    @pytest.mark.git
    def test_git_version_table_should_store_repository_from_ahjo_config(self):
        git.update_git_version(self.engine, self.git_table_schema,
                               self.git_table, self.sample_repository)
        git_version_table = self.reflected_git_table()
        result = self.engine.execute(
            select([
                git_version_table.c.Repository,
                git_version_table.c.Branch,
                git_version_table.c.Commit
            ]))
        row = result.fetchall()[0]
        git_branch = check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode('utf-8').strip()
        git_commit = check_output(
            ["git", "describe", "--always", "--tags"]).decode('utf-8').strip()
        assert row.Repository == self.sample_repository
        assert row.Branch == git_branch
        assert row.Commit == git_commit

    @pytest.mark.git
    def test_git_version_table_should_update_if_previously_existed(self):
        """First, create git version table with 'old schema'
        (has column Commit_hash). Run update_git_version and check that
        column Commit_hash has been renamd in git version table.
        """
        metadata = MetaData()
        existing_git_version_table = Table(
            self.git_table, metadata,
            Column('Repository', String(50), primary_key=True),
            Column('Branch', String(50), primary_key=True),
            Column('Commit_hash', String(50)),
            schema=self.git_table_schema
        )
        metadata.create_all(self.engine)
        insert = existing_git_version_table.insert().values(
            Repository="ahjo",
            Branch="dev",
            Commit_hash="commit"
            )
        self.engine.execute(insert)
        git.update_git_version(self.engine, self.git_table_schema, self.git_table)
        git_version_table = self.reflected_git_table()
        git_version_table_columns = [col.name for col in git_version_table.c]
        assert 'Commit' in git_version_table_columns
