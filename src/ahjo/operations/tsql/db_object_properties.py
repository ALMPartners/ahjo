# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for updating database extended properties.

Global variable EXCLUDED_SCHEMAS holds list of schemas that should
be excluded from update.

Global variable DOCS_DIR holds the documentation path of project.

Global variable DB_OBJECTS is a dictionary holding the following information
for listed object types:
- file = where documented extended properties are stored
- query = path to query that returns metadata and existing extended properties for this object type
- key_columns = list of columns whose values form an unique object key
"""
import json
from logging import getLogger
from os import makedirs, path
from typing import Union

from ahjo.interface_methods import rearrange_params
from ahjo.context import AHJO_PATH
from ahjo.database_utilities import execute_query, get_schema_names
from ahjo.operation_manager import OperationManager
from sqlalchemy.engine import Engine, Connection

logger = getLogger('ahjo')

EXCLUDED_SCHEMAS = ['db_accessadmin', 'db_backupoperator', 'db_datareader', 'db_datawriter',
                    'db_ddladmin', 'db_denydatareader', 'db_denydatawriter', 'db_owner',
                    'db_securityadmin', 'guest', 'INFORMATION_SCHEMA', 'sys']
DOCS_DIR = 'docs/db_objects'
DB_OBJECTS = {
    'schema': {
        'file': path.join(DOCS_DIR, 'schemas.json'),
        'query': 'resources/sql/queries/extended_properties_schemas.sql',
        'key_columns': ['schema_name']
    },
    'procedure': {
        'file': path.join(DOCS_DIR, 'procedures.json'),
        'query': 'resources/sql/queries/extended_properties_procedures.sql',
        'key_columns': ['schema_name', 'object_name']
    },
    'function': {
        'file': path.join(DOCS_DIR, 'functions.json'),
        'query': 'resources/sql/queries/extended_properties_functions.sql',
        'key_columns': ['schema_name', 'object_name']
    },
    'table': {
        'file': path.join(DOCS_DIR, 'tables.json'),
        'query': 'resources/sql/queries/extended_properties_tables.sql',
        'key_columns': ['schema_name', 'object_name']
    },
    'view': {
        'file': path.join(DOCS_DIR, 'views.json'),
        'query': 'resources/sql/queries/extended_properties_views.sql',
        'key_columns': ['schema_name', 'object_name']
    },
    'column': {
        'file': path.join(DOCS_DIR, 'columns.json'),
        'query': 'resources/sql/queries/extended_properties_columns.sql',
        'key_columns': ['schema_name', 'object_name', 'column_name']
    }
}


@rearrange_params({"engine": "connectable"})
def update_db_object_properties(connectable: Union[Engine, Connection], schema_list: list):
    """Update extended properties from file to database.

    Arguments
    ---------
    engine : Engine or Connection
    schema_list : list of str
        List of schemas to be documented.
            - If None, all schemas are updated.
            - If empty list, nothing is updated.
            - Else schemas of schema_list are updated.
    """
    with OperationManager('Updating extended properties'):
        if schema_list is None:
            schema_list = [s for s in get_schema_names(connectable)
                           if s not in EXCLUDED_SCHEMAS]
        elif len(schema_list) == 0:
            logger.warning(
                'No schemas allowed for update. Check variable "metadata_allowed_schemas".')
            return
        logger.debug(
            f'Updating extended properties for schemas {", ".join(schema_list)}')
        for object_type in DB_OBJECTS:
            existing_metadata = query_metadata(
                connectable, DB_OBJECTS[object_type], schema_list)
            source_file = DB_OBJECTS[object_type]['file']
            if not path.exists(source_file):
                logger.warning(
                    f"Cannot update extended properties for {object_type}s. File {source_file} does not exist.")
                continue
            try:
                with open(source_file, 'r', encoding='utf-8') as f:
                    documented_properties = json.load(f)
            except Exception as err:
                raise Exception(
                    f'Failed to read extended properties for {object_type}') from err
            for object_name, extended_properties in documented_properties.items():
                schema_name = object_name.split('.')[0]
                if schema_name in schema_list:
                    object_metadata = existing_metadata.get(object_name)
                    for property_name, property_value in extended_properties.items():
                        if object_metadata is not None and property_value == object_metadata.get(property_name):
                            continue
                        exec_update_extended_properties(
                            connectable,
                            object_name,
                            object_metadata,
                            property_name,
                            property_value,
                            object_type = object_type
                        )


@rearrange_params({"engine": "connectable"})
def exec_update_extended_properties(connectable: Union[Engine, Connection], object_name: str, object_metadata: dict, 
        extended_property_name: str, extended_property_value: str, object_type: str = ""):
    """Update object's extended properties by calling either
    procedure sp_addextendedproperty or sp_updateextendedproperty.
    If object_metadata is None, object does not exist in database.
    """
    try:
        if object_metadata is None:
            raise Exception('Object not found in database.')
        if object_metadata.get(extended_property_name) is None:
            procedure_call = 'EXEC sp_addextendedproperty '
        else:
            procedure_call = 'EXEC sp_updateextendedproperty '
        procedure_call += '@name=:name, @value=:value, @level0type=:level0type, @level0name=:level0name'
        params = {
            "name": extended_property_name,
            "value": extended_property_value,
            "level0type": 'schema',
            "level0name": object_metadata.get('schema_name')
        }
        object_type = object_metadata.get('object_type')
        parent_type = object_metadata.get('parent_type')
        if object_type in ('view', 'table', 'function', 'procedure', 'column'):
            level1type = parent_type if parent_type is not None else object_type
            procedure_call += ', @level1type=:level1type, @level1name=:level1name'
            params["level1type"] = level1type
            params["level1name"] = object_metadata.get('object_name')
            if object_type == 'column':
                procedure_call += ', @level2type=:level2type, @level2name=:level2name'
                params["level2type"] = 'column'
                params["level2name"] = object_metadata.get('column_name')
        execute_query(connectable, procedure_call, params)
    except Exception as err:
        logger.warning(
            f"Failed to update extended property '{extended_property_name}' for {object_type} '{object_name}'."
        )
        logger.debug(f"Extended property value: {extended_property_value}")
        logger.debug(err, exc_info=1)


@rearrange_params({"engine": "connectable"})
def update_file_object_properties(connectable: Union[Engine, Connection], schema_list: list):
    """Write extended properties to JSON file.
    If project doesn't have docs directory, create it.

    If schema_list is None, all schemas are written to file.
    If schema_list is empty list, nothing is written to file.
    Else schemas of schema_list are written to file.

    Arguments
    ---------
    connectable
        SQL Alchemy engine or connection.
    schema_list : list of str
        List of schemas to be documented.
    """
    with OperationManager('Fetching extended properties to files'):
        if not path.exists(DOCS_DIR):
            makedirs(DOCS_DIR, exist_ok=True)
        if schema_list is None:
            schema_list = [s for s in get_schema_names(connectable)
                           if s not in EXCLUDED_SCHEMAS]
        elif len(schema_list) == 0:
            logger.warning(
                'No schemas allowed for document. Check variable "metadata_allowed_schemas".')
            return
        logger.debug(
            f'Fetching extended properties for schemas {", ".join(schema_list)}')
        for object_type in DB_OBJECTS:
            existing_metadata = query_metadata(
                connectable,
                DB_OBJECTS[object_type],
                schema_list,
                properties_only=True
            )
            target_file = DB_OBJECTS[object_type]['file']
            with open(target_file, 'w+', encoding='utf-8', newline='') as f:
                json.dump(existing_metadata, f, indent=4, ensure_ascii=False)
        logger.debug('Extended properties fetched')


@rearrange_params({"engine": "connectable"})
def query_metadata(connectable: Union[Engine, Connection], metadata: dict, schema_list: list, properties_only: bool = False) -> dict:
    query_path = path.join(AHJO_PATH, metadata['query'])
    query_result = prepare_and_exec_query(connectable, query_path=query_path, param_list=schema_list)
    return result_set_to_dict(query_result, metadata['key_columns'], properties_only)


@rearrange_params({"engine": "connectable"})
def prepare_and_exec_query(connectable: Union[Engine, Connection], query_path: str, param_list: list) -> list:
    """Open query from query_path and set correct amount of
    parameter placeholders to question mark. Finally, execute query."""
    with open(query_path, 'r', encoding='utf-8') as file:
        query = file.read()
    param_placeholder = ""
    variables = {}
    for param in param_list:
        param_placeholder = param_placeholder + ":" + param + ","
        variables[param] = param
    param_placeholder = param_placeholder[:-1]
    query = query.replace('?', param_placeholder)
    result = execute_query(
        connectable, 
        query=query, 
        variables=variables,
        include_headers=True
    )
    return result


def result_set_to_dict(result_set: list, key_columns: list, properties_only: bool) -> dict:
    result = {}
    columns = result_set[0]
    for values in result_set[1:]:
        row = dict(zip(columns, values))
        object_key = '.'.join([row[k] for k in key_columns])
        if result.get(object_key) is None:
            if properties_only is True:
                result[object_key] = {}
            else:
                result[object_key] = row.copy()
                result[object_key].pop('property_name', None)
                result[object_key].pop('property_value', None)
        property_name = row['property_name']
        property_value = row['property_value']
        if property_name is not None:
            result[object_key][property_name] = property_value
    return result
