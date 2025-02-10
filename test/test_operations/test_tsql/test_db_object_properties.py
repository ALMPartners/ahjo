import json
import logging
from os import chdir, getcwd
from sqlalchemy.sql import text

import ahjo.operations.tsql.db_object_properties as dop
import pytest


DESC_QUERY = """
    SELECT
		S.[name] + '.' + O.[name] + '.' + C.[name] AS [object_name]
		,CONVERT(VARCHAR(8000), EP.[value]) AS [Description]
	FROM sys.all_objects AS O
		INNER JOIN sys.schemas AS S
			ON O.[schema_id] = S.[schema_id]
		INNER JOIN sys.columns AS C
			ON O.[object_id] = C.[object_id]
		INNER JOIN sys.extended_properties AS EP
			ON EP.[major_id] = O.[object_id] AND EP.[minor_id] = C.[column_id]
     WHERE EP.name = 'Description' AND EP.value != ''
    """

FLAG_QUERY = """
    SELECT
		S.[name] + '.' + O.[name] + '.' + C.[name] AS [object_name]
		,CONVERT(VARCHAR(8000), EP.[value]) AS [Flag]
	FROM sys.all_objects AS O
		INNER JOIN sys.schemas AS S
			ON O.[schema_id] = S.[schema_id]
		INNER JOIN sys.columns AS C
			ON O.[object_id] = C.[object_id]
		INNER JOIN sys.extended_properties AS EP
			ON EP.[major_id] = O.[object_id] AND EP.[minor_id] = C.[column_id]
     WHERE EP.name = 'Flag' AND EP.value != ''
    """


@pytest.mark.mssql
class TestDBObjectPropertiesWithSQLServer:

    @pytest.fixture(scope="function", autouse=True)
    def db_objects_setup_and_teardown(
        self, mssql_sample, mssql_engine, run_alembic_action
    ):
        """Deploy objects without updating object properties and git version."""
        self.engine = mssql_engine
        old_cwd = getcwd()
        chdir(mssql_sample)
        run_alembic_action("upgrade", "head")
        yield
        run_alembic_action("downgrade", "base")
        chdir(old_cwd)

    def test_objects_should_not_have_external_properties_before_update(self):
        with self.engine.begin() as connection:
            result = connection.execute(text(DESC_QUERY))
            descriptions = result.fetchall()
            result = connection.execute(text(FLAG_QUERY))
            flags = result.fetchall()
            assert len(descriptions) == 0
            assert len(flags) == 0

    def test_objects_should_have_external_properties_after_update(self):
        dop.update_db_object_properties(self.engine, ["store", "report"])
        with self.engine.begin() as connection:
            result = connection.execute(text(DESC_QUERY))
            descriptions = result.fetchall()
            result = connection.execute(text(FLAG_QUERY))
            flags = result.fetchall()
            assert len(descriptions) > 0
            assert len(flags) > 0

    def test_update_should_not_span_warnings_when_all_schemas_are_not_updated(
        self, caplog
    ):
        caplog.set_level(logging.WARNING)
        # updating report schema not allowed
        dop.update_db_object_properties(self.engine, ["store"])
        assert len(caplog.record_tuples) == 0

    def test_all_descs_in_db_should_be_found_in_files(self):
        dop.update_db_object_properties(self.engine, ["store", "report"])
        with self.engine.begin() as connection:
            result = connection.execute(text(DESC_QUERY))
            db_decs = result.fetchall()
            with open("./docs/db_objects/columns.json", "r") as f:
                file_descs = json.load(f)
            with open("./docs/db_objects/columns_default.json", "r") as f:
                default_descs = json.load(f)
            for row in db_decs:
                object_name = row[0]
                if object_name not in file_descs:
                    file_desc = default_descs[object_name.split(".")[-1]]["Description"]
                else:
                    file_desc = file_descs[object_name]["Description"]
                assert file_desc == row[1]

    def test_all_descs_in_file_should_be_found_in_db(self):
        dop.update_db_object_properties(self.engine, ["store", "report"])
        with self.engine.begin() as connection:
            result = connection.execute(text(DESC_QUERY))
            db_decs = result.fetchall()
            db_decs = dict(db_decs)
            column_description_file = "./docs/db_objects/columns.json"
            with open(column_description_file, "r") as f:
                file_descs = json.load(f)
            for object_name in file_descs:
                if file_descs[object_name].get("Description"):
                    assert (
                        file_descs[object_name]["Description"] == db_decs[object_name]
                    )
