# Ahjo - Database deployment framework
#
# Copyright 2019, 2020 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for Git version operations."""
from shlex import split
from subprocess import check_output
from logging import getLogger

from sqlalchemy import Table, Column, String, MetaData
from sqlalchemy.exc import NoSuchTableError

from ahjo.database_utilities import execute_query
from ahjo.operation_manager import OperationManager

logger = getLogger('ahjo')


def _sqla_git_table(metadata, git_table_schema, git_table):
    """Return Git table definition given by schema and table name."""
    return Table(
        git_table, metadata,
        Column('Repository', String(50), primary_key=True),
        Column('Branch', String(50), primary_key=True),
        Column('Commit', String(50)),
        schema=git_table_schema
    )


def update_git_version(engine, git_table_schema, git_table, repository=None):
    """Store the Git remote, branch and commit information to database.
    Alembic version does not catch changes to views and procedures, but git version catches.
    """
    with OperationManager("Updating Git version table"):
        try:
            git_table_name = git_table_schema + "." + git_table
            logger.info(f'GIT version table: {git_table_name}')
             # get the repository info and commit info
            if repository is None:
                origin_url_command = split("git config --get remote.origin.url")
                repository = check_output(origin_url_command).decode("utf-8").strip()
                if repository is None:
                    repository = ''
            branch, commit = _get_git_commit_info()
        except Exception as error:
            logger.error('Failed to retrieve Git commit. See log for detailed error message.')
            logger.debug(error)
            return
        try:
            _update_git_db_record(engine, git_table_schema, git_table, repository, branch, commit)
        except Exception as error:
            logger.error('Failed to update Git version table. See log for detailed error message.')
            logger.debug(error)


def _get_git_commit_info():
    """Retrieve branch and commit information with 'git rev-parse'
    and 'git describe' commands.
    Can fail if Git repository is not initialized.
    """
    banch_command = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    branch = check_output(banch_command).decode("utf-8").strip()
    commit_command = ['git', 'describe', '--always', '--tags']
    commit = check_output(commit_command).decode("utf-8").strip()
    return branch, commit


def _update_git_db_record(engine, git_table_schema, git_table, repository, branch, commit):
    """Update or create a Git version table."""
    metadata = MetaData(engine)
    try:
        git_version_table = Table(git_table, metadata, autoload=True, schema=git_table_schema)
    except NoSuchTableError as error:
        logger.info(f'Table {git_table_schema + "." + git_table} not found. Creating the table.')
        git_version_table = _sqla_git_table(metadata, git_table_schema, git_table)
        try:
            metadata.create_all()
        except Exception as error:
            raise Exception('Git version table creation failed. See log for detailed error message.') from error
    git_version_table_columns = [col.name for col in git_version_table.c]
    if 'Commit_hash' in git_version_table_columns:
        logger.info(f'Re-creating table {git_table_schema + "." + git_table}.')
        try:
            metadata.drop_all()
            new_metadata = MetaData(engine)
            git_version_table = _sqla_git_table(new_metadata, git_table_schema, git_table)
            new_metadata.create_all()
        except Exception as error:
            raise Exception('Failed to re-create Git version table. See log for detailed error message.') from error
    logger.info(f"Repository: {repository}")
    logger.info(f"Branch: {branch}")
    logger.info(f"Version: {commit}")
    engine.execute(git_version_table.delete())
    update_query = git_version_table.insert().values(Repository=repository,
                                                     Branch=branch,
                                                     Commit=commit)
    engine.execute(update_query)


def print_git_version(engine, git_table_schema, git_table):
    with OperationManager('Checking Git version from database'):
        try:
            metadata = MetaData(engine)
            git_version_table = _sqla_git_table(metadata, git_table_schema, git_table)
            git_version_query = git_version_table.select()
            result = execute_query(engine=engine, query=git_version_query)[0]
            repository, branch, version = result
            logger.info(f"Repository: {repository}")
            logger.info(f"Branch: {branch}")
            logger.info(f"Version: {version}")
        except Exception as error:
            logger.error('Failed to read GIT version table. See log for detailed error message.')
            logger.debug(error)
