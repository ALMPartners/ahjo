# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Utily for extracting connection info from configuration json.
"""
import importlib
from logging import getLogger
from typing import Union
from ahjo.credential_handler import get_credentials
from sqlalchemy.engine import make_url

logger = getLogger('ahjo')

def create_conn_info(conf: dict) -> dict:
    """Create a dictionary holding all important items for creating a connection to database.
    Call get_credentials to either read credentials from file or ask them from user.

    Arguments
    ---------
    conf
        Project configuration loaded from JSON.

    Returns
    -------
    dict
        Dictionary with the following keys: host, port, server, database, driver,
        dialect, username, password, azure_auth, token, odbc_trust_server_certificate and odbc_encrypt.
    """
    host = conf.get('target_server_hostname')
    port = conf.get('sql_port')
    server = _create_server_string(host, port)
    database = conf.get('target_database_name')
    driver = conf.get('sql_driver')
    dialect = conf.get('sql_dialect', 'mssql+pyodbc')
    azure_auth = conf.get('azure_authentication')
    username_file = conf.get("username_file")
    password_file = conf.get("password_file")
    sqlalchemy_url = conf.get("sqlalchemy.url")
    sqla_url_query_map = conf.get("sqla_url_query_map", {})
    sqla_engine_params = {}
    token = None
    username = None
    password = None
    odbc_trust_server_certificate = conf.get("odbc_trust_server_certificate") # deprecated
    odbc_encrypt = conf.get("odbc_encrypt") # deprecated
    azure_auth_lower = azure_auth.lower() if azure_auth is not None else None
    
    if odbc_trust_server_certificate is not None:
        logger.debug(
            "The config key 'odbc_trust_server_certificate' is deprecated. Set odbc connection parameters with 'sqla_url_query_map' or 'odbc_connect' instead."
        )
        sqla_url_query_map["TrustServerCertificate"] = odbc_trust_server_certificate
    
    if odbc_encrypt is not None:
        logger.debug(
            "The config key 'odbc_encrypt' is deprecated. Set odbc connection parameters with 'sqla_url_query_map' or 'odbc_connect instead'."
        )
        sqla_url_query_map["Encrypt"] = odbc_encrypt

    # Get driver, server, database, username and password from sqlalchemy url     
    if sqlalchemy_url is not None:
        sqlalchemy_url_obj = make_url(sqlalchemy_url)
        dialect = sqlalchemy_url_obj.drivername
        server = sqlalchemy_url_obj.host
        database = sqlalchemy_url_obj.database
        driver = sqlalchemy_url_obj.query.get("driver")
        username = sqlalchemy_url_obj.username
        password = sqlalchemy_url_obj.password
        port = sqlalchemy_url_obj.port
        host = server.split(",")[0]

    # Driver specific default settings
    if isinstance(driver, str):
        driver_lower = driver.lower()
        if driver_lower.startswith("odbc driver"): # ODBC specific default connection parameters

            if "Encrypt" not in sqla_url_query_map:
                sqla_url_query_map["Encrypt"] = "yes" if driver_lower == "odbc driver 18 for sql server" else "no"

            if driver_lower == "odbc driver 18 for sql server":
                sqla_url_query_map["LongAsMax"] = "Yes"

    # Parameters for sqlalchemy engine
    for key, value in conf.items():
        if key == "sqlalchemy.url": continue
        if key.startswith("sqlalchemy."):
            sqla_engine_params[key[11:]] = value

    if azure_auth_lower == "azureidentity":

        azure = importlib.import_module('.identity', 'azure')
        struct = importlib.import_module("struct")
        requests = importlib.import_module("requests")
        azure_identity_settings = conf.get("azure_identity_settings")
        token_url = azure_identity_settings.get("token_url") if isinstance(azure_identity_settings, dict) and "token_url" in azure_identity_settings else "https://database.windows.net/.default"
        azure_credentials = azure.AzureCliCredential()
        raw_token = azure_credentials.get_token(
            token_url # The token URL for any Azure SQL database
        ).token.encode("utf-16-le")
        raw_token_len = len(raw_token)
        token = struct.pack(f"<I{raw_token_len}s", raw_token_len, raw_token)

        # Get username
        try:
            graph_token = azure_credentials.get_token("https://graph.microsoft.com/.default").token
            response = requests.get(
                "https://graph.microsoft.com/v1.0/me", 
                headers = {
                    "Authorization": f"Bearer {graph_token}"
                }
            )
            if response.status_code == 200:
                user_info = response.json()
                username = user_info.get("userPrincipalName") 
            else:
                logger.debug(f"Failed to get user info: {response.status_code} - {response.text}")
        except Exception as error:
            logger.debug(f"Failed to get user info: {str(error)}")

    else:
        if sqlalchemy_url is None:
            if azure_auth in ('ActiveDirectoryIntegrated', 'ActiveDirectoryInteractive'):
                username, password = get_credentials(
                    usrn_file_path=username_file,
                    pw_file_path=password_file,
                    pw_prompt=None    # do not ask for password
                )
            else:
                username, password = get_credentials(
                    usrn_file_path = username_file,
                    pw_file_path = password_file
                )

    return {
        'host': host,
        'port': port,
        'server': server,
        'database': database,
        'driver': driver,
        'dialect': dialect,
        'username': username,
        'password': password,
        'azure_auth': azure_auth,
        'token': token,
        'odbc_trust_server_certificate': odbc_trust_server_certificate,
        'odbc_encrypt': odbc_encrypt,
        'sqlalchemy_url': sqlalchemy_url,
        'sqla_url_query_map': sqla_url_query_map,
        'sqla_engine_params': sqla_engine_params
    }


def _create_server_string(hostname: str, server_port: Union[str, int]) -> str:
    if server_port is not None and server_port != 0:
        server_string = str(hostname) + ',' + str(server_port)
    else:
        server_string = str(hostname)
    return server_string
