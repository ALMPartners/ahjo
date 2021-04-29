Ahjo Framework
====================

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ahjo)](https://pypi.org/project/ahjo/) [![PyPI](https://img.shields.io/pypi/v/ahjo)](https://pypi.org/project/ahjo/)

# Description

Ahjo is a database project framework and a deployment script. It is made to unify database project deployment and development practices and to give basic tooling for such projects. 

Ahjo provides a base scripts for database deployment with simple commands ("actions"), and the possibility to define custom actions for project's special needs. The scripts are designed to reduce accidental operations to production environments. The actions and their parts are logged by Ahjo.

Database tooling is currently based on sqlalchemy/alembic and SQL scripts. Support for other backends than Microsoft SQL Server is currently limited.

# Dependencies
## Common
* [alembic](https://pypi.org/project/alembic/)
* [commentjson](https://pypi.org/project/commentjson/)
* [pyparsing](https://pypi.org/project/pyparsing/)
* [SQL Alchemy](https://pypi.org/project/SQLAlchemy/)

## Platform-specific

### mssql
* [pyodbc](https://pypi.org/project/pyodbc/)

# Install Guide

## Install Guide 1 - PyPI
Install Ahjo (without platform-specific dependencies) from [Python Package Index](https://pypi.org/) with the following command:
```
pip install ahjo
```
In order to use Ahjo with the database engine of your choice, install platform-specific dependencies using available tags. For example, if you use Ahjo with Microsoft SQL Server, use tag `mssql` to install required dependencies. See full list of available tags below.
```
pip install ahjo[mssql]
```


## Install Guide 2 - Clone and install
1. Clone Ahjo

    - Get your clone command from the repository.

2. Install with pip


    - Use `-e` flag to install package in develop mode. 

```
cd .\ahjo
pip install [-e] .[mssql]
```

## Available platform tags
- `mssql` - Microsoft SQL Server

# Project Initialization
Create a new project by running the following command:
```
ahjo-init-project
```
This will start the project initialization command and you'll be asked to enter a name for your new project:
```
This is Ahjo project initialization command.
Enter project name:
```
Enter a name for your project and hit enter. Confirm, if project name and locations are correct.
```
Enter project name: project_1
You are about to initialize a new project project_1 to location C:\projects
Are you sure you want to proceed?
[Y/N] (N): Y
confirmed
[2019-06-04 08:46:23] Ahjo - Creating new project project_1
Project C:\projects\project_1 created.
```

# Usage

## Usage Example

Before running actions:

1. Install Ahjo (see "Install Guide")
2. Initialize project using ahjo-init-project (see "Project Initialization")
3. Have your development database server running (SQL Server for the example)
4. Fill database connection information to the config-file

To create a database without objects, run the following command in the project root:
```
ahjo init config_development.jsonc
```
After the command, there should be a empty database at the server, as configured in config_development.jsonc. This step is usually run only once, and is not required if the database already exists in the server.

After tables are defined using alembic (see alembic's documentation for creating new version scripts), the tables can be deployed using:

```
ahjo deploy config_development.jsonc
```

This command also runs all the SQL scripts that are defined in directories database/functions, database/procedures and database/views.

Conventionally scripts under database/data include row inserts for dimension tables, and database/testdata for mock data insertion scripts. To populate the dimension tables run:

```
ahjo data config_development.jsonc
```

To run test SQL on top of mock data:

```
ahjo testdata config_development.jsonc
ahjo test config_development.jsonc
```

To run all the previous commands at once, a single (multi-)action "complete-build" can be used:

```
ahjo complete-build config_development.jsonc
```

To deploy your project to production you need a new config-file. In production environment actions like "downgrade" can be quite hazard. To exclude such actions set "allowed_actions" to a list:

```
"allowed_actions": ["deploy", "data"]
```

Now running "downgrade" is not possible using production configuration.

```
ahjo downgrade config_production.jsonc
[2019-10-01 12:58:12] Starting to execute "downgrade"
Action downgrade is not permitted, allowed actions: deploy, data
------
```

To add your own actions (f.e. for more complex testing), modify ahjo_actions.py.

## Script and arguments
```
ahjo <action> <config_filename>
```
Confirmation is asked for actions that affect the database. Depending on the configuration, the database credentials can be stored into files or be asked when needed, once per application run. The later option is recommended for production environments. The credential handling is shared with alembic with custom [env.py](./ahjo/resources/files/env.py) file.

Pre-defined actions include:

* init-config
    * Initializes local configuration file. This file is intended to hold configurations that should not be versioned.

* init
    * Creates the database. 
        * Database is created with module [create_db.py](./ahjo/operations/tsql/create_db.py). Required configurations are *target_database_name*, *target_server_hostname* and *sql_port*. For optional configurations, see config file cheat sheet below.

* structure
    * Creates database structure, that is schemas, tables and constraints. 
        * Primary method runs all SQL files under directories *./database/schemas*, *./database/tables* and *./database/constraints*. Alternate method runs SQL script *./database/create_db_structure.sql*. If structure can't be created with primary method (one of the listed directories does not exists etc.), alternate method is attempted.

* deploy
    * Runs alembic migrations, creates views, procedures and functions. 
        * First, runs *alembic upgrade head*. Second, creates functions, views and procedures by executing all SQL files under directories *./database/functions*, *./database/views* and *./database/procedures*. Third, attempts to update documented extended properties to database. Finally, updates current GIT version (`git describe`) to GIT version table.

* data
    * Runs data insertion scripts.
        * Runs all SQL files under *./database/data*.

* testdata
    * Inserts data for testing into database.
        * Runs all SQL files under *./database/data/testdata*.

* complete-build
    * Runs actions init, deploy, data, testdata and test in order.

* drop
    * Drops all views, procedures, functions, clr-procedures and assemblies that are listed in directory *./database*. Drops are executed with TRY-CATCH.

* downgrade
    * Reverts the database back to basic structure.
        * First, drops all views, procedures, functions, clr-procedures and assemblies that are listed in directory *./database*. Drops are executed with TRY-CATCH. Second, runs `alembic downgrade base`.

* version
    * Prints the alembic- and git-version currently in the database.
        * Alembic version is read from *alembic_version_table*. GIT version is read from *git_table*.
* update-file-obj-prop
    * Write objects and their extended properties (only SQL Server) to JSON files under *./docs* directory.
        * Documented schemas are listed in *metadata_allowed_schemas*.
* update-db-obj-prop
    * Update documented extended properties (only SQL Server) from JSON files under *./docs* directory to database.
        * Updated schemas are listed in *metadata_allowed_schemas*.
* test
    * Runs tests and returns the results.
        * Runs all SQL scripts under *./database/tests*.

### List
You can view all available actions and their descriptions with command `ahjo list`.
```
ahjo list
-------------------------------
List of available actions
-------------------------------
'assembly': (MSSQL) Drop and deploy CLR-procedures and assemblies.
'complete-build': (MSSQL) Run 'init', 'deploy', 'data', 'testdata' and 'test' actions.
.
.
.
```

## Config File
Ahjo requires config file to be JSON or JSONC (JSON with comments) format. Ahjo configs are located in *BACKEND* section of file. Below is an example of config file and a list of default configuration parameters.
```
{
    "BACKEND": {
        "allowed_actions": "ALL",
        //Git repository and git version table information
        "url_of_remote_git_repository": "https:\\\\github.com\\user\\projectx\\",
        "git_table": "git_version",
        "git_table_schema": "dbo",
        //Database connection information
        "sql_port": 1433,
        "sql_driver": "SQL Server",
        "target_database_name": "PROJECTX",
        "target_server_hostname": "localhost",
        // Database file location
        "database_data_path": "/var/opt/mssql/data/PROJECTX.mdf",
        "database_log_path": "/var/opt/mssql/data/PROJECTX.ldf",
        //Alembic
        //the table that alembic creates automatically for migration version handling
        "alembic_version_table": "alembic_version",
        "alembic_version_table_schema": "dbo",
    }
}
```



| Parameter  | Required | Description | Type | Default Value |
| --- | --- | --- | --- | --- |
| alembic_version_table | No | Name of Alembic version table. Table holds the current revision number. | str | "alembic_version" |
| alembic_version_table_schema | No | Schema of Alembic version table. | str | "dbo" |
| allowed_actions | Yes | List of actions Ahjo is allowed to execute. If all actions are allowed, use "ALL". | str or list of str | |
| azure_authentication | No | Authentication type to Azure AD. Possible values are "ActiveDirectoryPassword", "ActiveDirectoryInteractive" and "ActiveDirectoryIntegrated". | str | |
| database_collation | No | Collation of database. | str | "Latin1_General_CS_AS" |
| database_compatibility_level | No | Compatibility level of database. | int | Depends on server. SQL Server 2017 default is 140. |
| database_data_path | No | Path of database data file. | str | |
| database_file_growth | No | The size (MB) of how much database data file will grow when it runs out of space. | int | 500 |
| database_init_size | No | Initial size (MB) of database data file. | int | 100 |
| database_log_path | No | Path of database log file. | str | |
| database_max_size | No | Maximum size (MB) of database data file. | int | 10000 |
| git_table | No | Name of git hash table. Table holds current branch, commit hash and URL of remote repository. | str | "git_version" |
| git_table_schema | No | Schema of git hash table. | str | "dbo" |
| metadata_allowed_schemas | No | List of schemas that extended properties will be written to JSON files and updated to database. If list left empty, nothing is documented or updated. | list of str | |
| password_file | No | Path of file where password will be stored. If no path given, credentials are asked everytime any database altering action is run. | str | |
| sql_dialect | No | Dialect used by SQL Alchemy. | str | "mssql+pyodbc" |
| sql_driver | No | Name of ODBC driver. | str | |
| sql_port | Yes | Port number of target database server. | int | |
| target_database_name | Yes | Name of target database. | str | |
| target_server_hostname | Yes | Host name of target database server. | str | |
| url_of_remote_git_repository | No | URL of project's remote repository. | str | |
| username_file | No | Path of file where username will be stored. If no path given, credentials are asked everytime any database altering action is run. | str | |


## Using Alembic with Ahjo
Alembic upgrade HEAD is used in deploy action, but for many use cases other alembic commands are needed. For these needs Ahjo comes with a [env.py](./ahjo/resources/files/env.py) file that enables running Alembic commands without running Ahjo.

The env.py modifications provide logging integration to Ahjo, default naming schema and possibility to run alembic according to project configuration. The engines are created according to configuration, and there is no need for storing plain-text connection strings in the project.

Usage example:
```
alembic -x main_config=config_development.jsonc downgrade -1
```

The [env.py](./ahjo/resources/files/env.py) is created in initialize-project command.

# Logging
Ahjo's logging is very inclusive. Everything Ahjo prints to console, is also written into log file ahjo.log.

# Customization
Every default Ahjo action and multiaction can be overwritten in project's ahjo_actions.py file.

In example below, *'init'* and *'complete-build'* actions are overwritten.
```
import ahjo.operations as op
from ahjo.action import action, create_multiaction


@action(affects_database=True)
def structure(context):
    """New structure action."""
    from models import Base
    Base.metadata.create_all(context.get_engine())

# overwrite Ahjo complete-build
create_multiaction("complete-build", ["init", "structure", "deploy", "data", "test"])
```

# License
Copyright 2019, 2020, 2021 ALM Partners Oy

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
