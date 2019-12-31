# Ahjo - Database deployment framework
#
# Copyright 2019, 2020 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Utily for extracting connection info from configuration json.
"""
from ahjo.credential_handler import get_credentials

def create_conn_info(conf):
    """Create dictionary holding all important items for creating a connection to database.
    Call get_credentials to either read credentials from file or ask them from user.

    Arguments
    ---------
    conf: dict
        Project configuration loaded from JSON.

    Returns
    -------
    dict
        Dictionary with the following keys: host, port, server, database, driver,
        dialect, username and password.
    """
    username_file = conf.get("username_file")
    password_file = conf.get("password_file")
    username, password = get_credentials(usrn_file_path=username_file, pw_file_path=password_file)
    host = conf.get('target_server_hostname')
    port = conf.get('sql_port')
    server = _create_server_string(host, port)
    database = conf.get('target_database_name')
    driver = conf.get('sql_driver')
    dialect = conf.get('sql_dialect', 'mssql+pyodbc')
    return {
        'host': host,
        'port': port,
        'server': server,
        'database': database,
        'driver': driver,
        'dialect': dialect,
        'username': username,
        'password': password
    }

def _create_server_string(hostname, server_port):
    if server_port is not None and server_port != 0:
        server_string = str(hostname) + ',' + str(server_port)
    else:
        server_string = str(hostname)
    return server_string
