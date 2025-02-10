from base64 import b64decode

import ahjo.database_utilities.conn_info as ahjo
import pytest


@pytest.mark.parametrize(
    "hostname, port", [("localhost", 1433), ("localhost", "5432"), ("my-host-name", 34)]
)
def test_create_server_string_should_include_port(hostname, port):
    server_string = ahjo._create_server_string(hostname, port)
    assert server_string == f"{hostname},{port}"


@pytest.mark.parametrize(
    "hostname, port", [("localhost", None), ("localhost", 0), ("my-host-name", None)]
)
def test_create_server_string_should_not_include_port(hostname, port):
    server_string = ahjo._create_server_string(hostname, port)
    assert server_string == hostname


@pytest.fixture(scope="function")
def read_config(ahjo_config, mssql_sample):
    return ahjo_config(mssql_sample)


def test_create_conn_info_should_return_dict_with_keys(read_config):
    conn_info = ahjo.create_conn_info(read_config)
    assert conn_info
    assert "host" in conn_info
    assert "port" in conn_info
    assert "server" in conn_info
    assert "database" in conn_info
    assert "driver" in conn_info
    assert "dialect" in conn_info
    assert "username" in conn_info
    assert "password" in conn_info
    assert "azure_auth" in conn_info
    assert "token" in conn_info
    assert "sqlalchemy_url" in conn_info
    assert "sqla_url_query_map" in conn_info


def test_conn_info_should_partially_match_config(read_config):
    conn_info = ahjo.create_conn_info(read_config)
    assert conn_info["host"] == read_config.get("target_server_hostname")
    assert conn_info["port"] == read_config.get("sql_port")
    assert conn_info["database"] == read_config.get("target_database_name")
    assert conn_info["driver"] == read_config.get("sql_driver")
    assert conn_info["dialect"] == read_config.get("sql_dialect")
    assert conn_info["azure_auth"] == read_config.get("azure_authentication")


def test_conn_info_server_should_be_created_by_ahjo(read_config):
    conn_info = ahjo.create_conn_info(read_config)
    server_string = ahjo._create_server_string(
        read_config.get("target_server_hostname"), read_config.get("sql_port")
    )
    assert conn_info["server"] == server_string


def test_conn_info_should_set_defalut_to_sql_dialect(read_config):
    read_config.pop("sql_dialect", None)
    conn_info = ahjo.create_conn_info(read_config)
    assert conn_info["dialect"] == "mssql+pyodbc"


def test_conn_info_should_store_credentials(read_config):
    username_file = read_config["username_file"]
    with open(username_file, "r") as f:
        username = f.read()
    password_file = read_config["password_file"]
    with open(password_file, "r") as f:
        password = f.read()
    conn_info = ahjo.create_conn_info(read_config)
    pw = password.split("=")[1]
    # Add padding: Divide the length of the input string by 4, take the remainder.
    # If it is 2, add two = characters at the end. If it is 3, add one = character at the end.
    extra = len(pw) % 4
    if extra > 0:
        pw = pw + ("=" * (4 - extra))
    assert conn_info["username"] == username.split("=")[1]
    assert conn_info["password"] == b64decode(pw.encode()).decode()


def test_conn_info_should_set_longasmax_to_yes_for_odbc_driver_18(read_config):
    read_config["sql_driver"] = "ODBC Driver 18 for SQL Server"
    conn_info = ahjo.create_conn_info(read_config)
    assert conn_info["sqla_url_query_map"]["LongAsMax"] == "Yes"
