from os import chdir, getcwd, path

import ahjo.database_utilities.sqla_utilities as ahjo
import pytest
from yaml import safe_load
from sqlalchemy.sql import text

MSSQL_PATTERNS = ahjo.get_dialect_patterns('mssql')
POSTGRESQL_PATTERNS = ahjo.get_dialect_patterns('postgresql')

def query_batches_equals_result_batches(batches, query):
    assert len(batches) == len(query['batches'])
    for i in range(len(batches)):
        assert batches[i] == query['batches'][i]

@pytest.mark.parametrize("file_name", ['store.vwClients_UTF_16'])
def test_execute_from_file_should_raise_error_if_file_is_not_utf_8_bom(mssql_sample, file_name):
    sql_file = path.join(mssql_sample, f'database/error/{file_name}.sql')
    with pytest.raises(ValueError):
        ahjo.execute_from_file(None, sql_file)


@pytest.mark.mssql
class TestWithSQLServer():
    @pytest.fixture(scope='function', autouse=True)
    def exec_from_file_mssql_setup_and_teardown(self, ahjo_config, mssql_sample, mssql_engine, run_alembic_action, drop_mssql_objects):
        self.config = ahjo_config(mssql_sample)
        self.alembic_table = self.config['alembic_version_table_schema'] + \
            '.' + self.config['alembic_version_table']
        self.engine = mssql_engine
        old_cwd = getcwd()
        chdir(mssql_sample)
        run_alembic_action('upgrade', 'head')
        yield
        drop_mssql_objects(self.engine)
        run_alembic_action('downgrade', 'base')
        with self.engine.begin() as connection:
            connection.execute(text(f"DROP TABLE {self.alembic_table}"))
        chdir(old_cwd)

    @pytest.mark.parametrize("object_name", ['store.vwClients', 'store.vwProducts'])
    def test_execute_from_file_should_create_view(self, object_name):
        schema, name = object_name.split('.')
        with self.engine.begin() as connection:
            result = connection.execute(
                text("SELECT * FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :name"), 
                {"schema": schema, "name": name}
            ).fetchall()
            assert not result
            ahjo.execute_from_file(
                self.engine,
                f'database/views/{object_name}.sql'
                )
            result = connection.execute(
                text("SELECT * FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :name"), 
                {"schema": schema, "name": name}
            ).fetchall()
            assert len(result) == 1

    # possibility to parametrize
    def test_execute_from_file_should_insert_data(self):
        object_name = 'store.ProductCategory'
        query = f"SELECT COUNT(*) FROM {object_name}"
        with self.engine.begin() as connection:
            result = connection.execute(text(query)).fetchall()
            assert result[0] == (0,)
            ahjo.execute_from_file(self.engine, f'database/data/{object_name}.sql')
            result = connection.execute(text(query)).fetchall()
            assert result[0] == (3,)

    @pytest.mark.parametrize("file_name", ['test_colon_escaping'])
    def test_execute_from_file_should_not_raise_error_if_file_contains_colon(self, mssql_sample, file_name):
        ahjo.execute_from_file(
            self.engine,
            path.join(mssql_sample, f'database/tests/{file_name}.sql')
        )

    @pytest.mark.parametrize("file_name", ['tab_count'])
    def test_split_to_batches_should_preserve_tabs(self, mssql_sample, file_name):
        result = ahjo.execute_from_file(
            self.engine,
            path.join(mssql_sample, f'database/tests/{file_name}.sql')
        )
        assert result[0][0] == 2
        assert result[1][0] == 1
        
    @pytest.mark.parametrize("file_name", ['go_with_indentations'])
    def test_split_to_batches_with_mssql_dialect_should_split_with_indented_go(self, mssql_sample, file_name):
        result = ahjo.execute_from_file(
            self.engine,
            path.join(mssql_sample, f'database/tests/{file_name}.sql')
        )
        assert result[0][0] == 1
        assert result[1][0] == 2

@pytest.mark.mssql
class TestWithPopulatedSQLServer():
    @pytest.fixture(scope='function', autouse=True)
    def exec_from_file_mssql_setup_and_teardown(self, ahjo_config, mssql_sample, mssql_engine, run_alembic_action, deploy_mssql_objects, drop_mssql_objects, populate_table):
        self.config = ahjo_config(mssql_sample)
        self.alembic_table = self.config['alembic_version_table_schema'] + \
            '.' + self.config['alembic_version_table']
        self.engine = mssql_engine
        old_cwd = getcwd()
        chdir(mssql_sample)
        run_alembic_action('upgrade', 'head')
        deploy_mssql_objects(self.engine)
        populate_table(self.engine, 'store.Clients')
        populate_table(self.engine, 'store.Products')
        yield
        drop_mssql_objects(self.engine)
        run_alembic_action('downgrade', 'base')
        query = f"DROP TABLE {self.alembic_table}"
        with self.engine.begin() as connection:
            connection.execute(text(query))
        chdir(old_cwd)

    @pytest.mark.parametrize("query_name,result_set", [
        ('clients_are_populated', [['QUESTION', 'ANSWER'], ('Is Clients Populated?', 'YES')]),  # nopep8
        ('products_are_populated', [])  # script has insufficient NOCOUNT setting    # nopep8
    ])
    def test_execute_from_file_should_return_query_results(self, query_name, result_set):
        query_result = ahjo.execute_from_file(
            self.engine,
            f'database/tests/{query_name}.sql',
            include_headers=True
            )
        assert query_result == result_set

    @pytest.mark.parametrize("query_name,result_set", [
        ('table_row_count', [['Table name', 'Row count'], ('Clients', 5), ('Products', 3)])  # nopep8
    ])
    def test_execute_from_file_should_handle_variables(self, query_name, result_set, test_db_name):
        query_result = ahjo.execute_from_file(
            self.engine,
            f'database/tests/{query_name}.sql',
            scripting_variables={"DB_NAME": test_db_name},
            include_headers=True
        )
        assert query_result == result_set

def get_query(dialect_name, query_key):
    """Get query used in test from config."""
    current_dir = path.dirname(path.realpath(__file__))
    query_file_path = path.join(current_dir, 'test_execute_from_file.yaml')
    with open(query_file_path, 'r') as f:
        queries = safe_load(f)
    return queries[dialect_name][query_key]


@pytest.mark.parametrize("scripting_variables", [None, 'testi', ['value'], 10])
def test_insert_script_variables_should_raise_error_if_not_dict(scripting_variables):
    sql = get_query('mssql', 'query1')['sql_with_variables']
    with pytest.raises(AttributeError):
        ahjo._insert_script_variables(
            dialect_patterns=MSSQL_PATTERNS,
            sql=sql,
            scripting_variables=scripting_variables
        )


def test_insert_script_variables_should_not_do_anything_if_empty_dict():
    sql_before = get_query('mssql', 'query1')['sql_with_variables']
    sql_after = ahjo._insert_script_variables(
        dialect_patterns=MSSQL_PATTERNS,
        sql=sql_before,
        scripting_variables={}
    )
    assert sql_before == sql_after


@pytest.mark.parametrize('query_key', ['query1'])
def test_insert_script_variables_with_no_dialect(query_key):
    query = get_query('empty', query_key)
    sql_without_variables = ahjo._insert_script_variables(
        dialect_patterns={},
        sql=query['sql_with_variables'],
        scripting_variables=query['variables']
    )
    for key in query['variables']:
        assert key not in sql_without_variables
    assert sql_without_variables == query['sql_with_value']


@pytest.mark.parametrize('query_key', ['query1'])
def test_insert_script_variables_with_mssql(query_key):
    query = get_query('mssql', query_key)
    tsql_without_variables = ahjo._insert_script_variables(
        dialect_patterns=MSSQL_PATTERNS,
        sql=query['sql_with_variables'],
        scripting_variables=query['variables']
    )
    for key in query['variables']:
        assert key not in tsql_without_variables
    assert tsql_without_variables == query['sql_with_value']

# test_insert_script_variables_with_postgresql

@pytest.mark.parametrize('query_key', ['query1'])
def test_split_to_batches_with_empty_dialect_should_not_split(query_key):
    query = get_query('empty', query_key)
    batches = ahjo._split_to_batches(
        dialect_patterns={},
        sql=query['sql_with_value']
    )
    assert len(batches) == 1
    assert batches[0] == query['sql_with_value']


@pytest.mark.parametrize('query_key', ['query1', 'query2'])
def test_split_to_batches_with_mssql_dialect_should_split_with_go(query_key):
    query = get_query('mssql', query_key)
    batches = ahjo._split_to_batches(
        dialect_patterns=MSSQL_PATTERNS,
        sql=query['sql_with_value']
    )
    query_batches_equals_result_batches(batches, query)

@pytest.mark.parametrize('query_key', ['query3'])
def test_split_to_batches_with_mssql_dialect_should_split_with_case_insensitive_go(query_key):
    query = get_query('mssql', query_key)
    query_batches_equals_result_batches(
        ahjo._split_to_batches(
            dialect_patterns=MSSQL_PATTERNS,
            sql=query['sql_with_value']
        ), 
        query
    )

@pytest.mark.parametrize('query_key', ['query_goto'])
def test_split_to_batches_with_mssql_dialect_should_not_split_with_goto(query_key):
    query = get_query('mssql', query_key)
    query_batches_equals_result_batches(
        ahjo._split_to_batches(
            dialect_patterns=MSSQL_PATTERNS,
            sql=query['sql_with_value']
        ), 
        query
    )

@pytest.mark.parametrize('query_key', ['query_go_count'])
def test_split_to_batches_with_mssql_dialect_should_split_with_go_count(query_key):
    query = get_query('mssql', query_key)
    query_batches_equals_result_batches(
        ahjo._split_to_batches(
            dialect_patterns=MSSQL_PATTERNS,
            sql=query['sql_with_value']
        ), 
        query
    )

@pytest.mark.parametrize('query_key', ['query1'])
def test_split_to_batches_with_postgresql_dialect_should_split_with_semicolon(query_key):
    query = get_query('postgresql', query_key)
    batches = ahjo._split_to_batches(
        dialect_patterns=POSTGRESQL_PATTERNS,
        sql=query['sql_with_value']
    )
    query_batches_equals_result_batches(batches, query)
