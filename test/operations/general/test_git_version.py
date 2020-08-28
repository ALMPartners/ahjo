from os import environ
from subprocess import PIPE, Popen, check_output
import logging

import pytest
from sqlalchemy import Column, MetaData, String, Table, select
from sqlalchemy.exc import NoSuchTableError

import ahjo.operations.general.git_version as git


@pytest.fixture(scope='function')
def git_version_git_setup_and_teardown():
    """Overwrite PATH variable.
    Works in WIN to 'disable' Git.
    """
    path = environ.get("PATH")
    environ["PATH"] = ""
    yield
    environ["PATH"] = path


def test_update_git_version_should_skip_when_no_git(git_version_git_setup_and_teardown, caplog):
    caplog.set_level(logging.ERROR)
    git.update_git_version(None, 'dbo', 'git_version', 'repository')
    assert "Failed to retrieve Git commit. See log for detailed error message." in caplog.text


@pytest.mark.git
def test_update_git_version_should_skip_when_no_connection(caplog):
    caplog.set_level(logging.WARNING)
    git.update_git_version(None, 'dbo', 'git_version', 'repository')
    assert "Failed to update Git version table. See log for detailed error message." in caplog.text


@pytest.mark.mssql
class TestWithSQLServer():

    @pytest.fixture(scope='function', autouse=True)
    def git_version_mssql_setup_and_teardown(self, ahjo_config, mssql_sample, mssql_engine):
        self.config = ahjo_config(mssql_sample)
        self.engine = mssql_engine
        p = Popen(
            ['ahjo', 'deploy-without-git-version-and-object-properties', 'config_development.jsonc'],
            cwd=mssql_sample,
            stdin=PIPE
            )
        p.communicate(input='y\n'.encode())
        yield
        p = Popen(
            ['ahjo', 'downgrade', 'config_development.jsonc'],
            cwd=mssql_sample,
            stdin=PIPE
            )
        p.communicate(input='y\n'.encode())
        p = Popen(
            ['ahjo', 'drop-git-and-alembic-version-if-exists', 'config_development.jsonc'],
            cwd=mssql_sample,
            stdin=PIPE
            )
        p.communicate(input='y\n'.encode())
    

    def test_git_version_table_should_not_exist(self):
        git_table = self.config['git_table']
        with pytest.raises(NoSuchTableError):
            Table(git_table, MetaData(), autoload=True, autoload_with=self.engine)

    @pytest.mark.git
    def test_git_version_table_should_exist_after_update(self):
        git_table = self.config['git_table']
        git_table_schema = self.config['git_table_schema']
        git.update_git_version(self.engine, git_table_schema, git_table)
        git_version_table = Table(git_table, MetaData(), autoload=True, autoload_with=self.engine)
        git_version_table_columns = [col.name for col in git_version_table.c]
        assert 'Repository' in git_version_table_columns
        assert 'Branch' in git_version_table_columns
        assert 'Commit' in git_version_table_columns

    @pytest.mark.git
    def test_git_version_table_should_store_commit_after_update(self):
        git_table = self.config['git_table']
        git_table_schema = self.config['git_table_schema']
        git.update_git_version(self.engine, git_table_schema, git_table)
        git_version_table = Table(git_table, MetaData(), autoload=True, autoload_with=self.engine)
        result = self.engine.execute(
            select([
                git_version_table.c.Repository,
                git_version_table.c.Branch,
                git_version_table.c.Commit
                ]))
        row = result.fetchall()[0]
        git_remote = check_output(["git", "remote", "get-url", "origin"]).decode('utf-8').strip()
        git_branch = check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode('utf-8').strip()
        git_commit = check_output(["git", "describe", "--always", "--tags"]).decode('utf-8').strip()
        assert row.Repository == git_remote
        assert row.Branch == git_branch
        assert row.Commit == git_commit

    @pytest.mark.git
    def test_git_version_table_should_store_repository_from_ahjo_config(self):
        git_table = self.config['git_table']
        git_table_schema = self.config['git_table_schema']
        sample_repository = self.config['url_of_remote_git_repository']
        git.update_git_version(self.engine, git_table_schema, git_table, sample_repository)
        git_version_table = Table(git_table, MetaData(), autoload=True, autoload_with=self.engine)
        result = self.engine.execute(
            select([
                git_version_table.c.Repository,
                git_version_table.c.Branch,
                git_version_table.c.Commit
                ]))
        row = result.fetchall()[0]
        git_branch = check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode('utf-8').strip()
        git_commit = check_output(["git", "describe", "--always", "--tags"]).decode('utf-8').strip()
        assert row.Repository == sample_repository
        assert row.Branch == git_branch
        assert row.Commit == git_commit

    @pytest.mark.git
    def test_git_version_table_should_update_if_previously_existed(self):
        """First, create git version table with 'old schema'
        (has column Commit_hash). Run update_git_version and check that
        column Commit_hash has been renamd in git version table.
        """
        metadata = MetaData()
        git_table = self.config['git_table']
        git_table_schema = self.config['git_table_schema']
        existing_git_version_table = Table(
            git_table, metadata,
            Column('Repository', String(50), primary_key=True),
            Column('Branch', String(50), primary_key=True),
            Column('Commit_hash', String(50)),
            schema=git_table_schema
            )
        metadata.create_all(self.engine)
        insert = existing_git_version_table.insert().values(Repository="ahjo", Branch="dev", Commit_hash="commit")
        self.engine.execute(insert)
        git.update_git_version(self.engine, git_table_schema, git_table)
        git_version_table = Table(git_table, MetaData(), autoload=True, autoload_with=self.engine, schema=git_table_schema)
        git_version_table_columns = [col.name for col in git_version_table.c]
        assert 'Commit' in git_version_table_columns
