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
* [pyparsing](https://pypi.org/project/pyparsing/)
* [SQL Alchemy](https://pypi.org/project/SQLAlchemy/)

## Platform-specific

### mssql
* [pyodbc](https://pypi.org/project/pyodbc/)

### azure
* [azure-identity](https://pypi.org/project/azure-identity/)

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
pip install [-e] .[mssql,azure]
```

## Available platform tags
- `mssql` - Microsoft SQL Server
- `azure` - Microsoft Azure SQL Database

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
`<config_filename>` is not mandatory if the config path is defined in environment variable `AHJO_CONFIG_PATH`. 
By default, confirmation is asked for actions that affect the database. Confirmation can be skipped with `-ni` or `--non-interactive` argument.
Depending on the configuration, the database credentials can be stored into files or be asked when needed, once per application run. The later option is recommended for production environments. The credential handling is shared with alembic with custom [env.py](./ahjo/resources/files/env.py) file.

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

* deploy-files
    * Runs *alembic upgrade head*, creates database objects by executing all SQL files listed in --files argument and updates current GIT version (`git describe`) to GIT version table. 
    * Example usage: `ahjo deploy-files .\config_development.jsonc --files ./database/procedures/dbo.procedure.sql ./database/functions/dbo.function.sql` .

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

* drop-files
    * Drops database objects from locations that are listed in --files argument. Database objects can be views, procedures, functions or assemblies. Object type is read from --object_type argument. Acceptable --object_type parameters: view, procedure, function, assembly.
    * Example usage: `ahjo drop-files .\config_development.jsonc --files ./database/procedures/dbo.procedure_1.sql ./database/procedures/dbo.procedure_2.sql --object_type procedure` .

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
| skipped_actions | No | List of actions that are skipped. | list of str | [] |
| azure_authentication | No | Authentication type to Azure AD. Possible values are "ActiveDirectoryPassword", "ActiveDirectoryInteractive", "ActiveDirectoryIntegrated" and "AzureIdentity". | str | |
| azure_identity_settings | No | A dictionary containing parameters for azure-identity library (used only if azure_authentication is "AzureIdentity"). Dictionary holds a key: "token_url" (str). Note: currently ahjo supports only AzureCliCredential authentication method. | dict | |
| database_collation | No | Collation of database. If the defined collation is different from the database collation, a warning is logged. | str | "Latin1_General_CS_AS" |
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
| db_permissions | No | List of dictionaries containing file locations & scripting variables for setting up database permissions from sql file(s). Dictionary holds keys: "source" (str) and "variables" (dict). | list of dict | |
| db_permission_invoke_method | No | Invoke method for setting up database permissions. Available options: "sqlcmd" (default) or "sqlalchemy". | str | |
| odbc_trust_server_certificate | No | Value of TrustServerCertificate in ODBC connection string. | str | "no" |
| odbc_encrypt | No | Value of Encrypt in ODBC connection string. | str | "yes" |
| upgrade_actions_file | No | Configuration file for upgrade actions. | str | "./upgrade_actions.jsonc" |
| catalog_collation_type_desc | No | Catalog collation setting of database. If the defined setting is different from the database setting, a warning is logged. Applies only to Azure SQL Database | str | "DATABASE_DEFAULT" |
| display_db_info | No | Print database collation information to console before running actions. | boolean | true |
| context_connectable_type | No | Type of SQLAlchmey object returned by Context.get_connectable(). Possible values are "engine" and "connection". | str | "engine" |
| transaction_mode | No | Transaction management style for ahjo actions. Applied only if context_connectable_type is "connection". Possible values are "begin_once" and "commit_as_you_go". If "begin_once", a transaction is started before running actions and committed after all actions are run. If "commit_as_you_go", a transaction is started before running actions but not committed automatically. | str | "begin_once" |


## Using Alembic with Ahjo
Alembic upgrade HEAD is used in deploy action, but for many use cases other alembic commands are needed. For these needs Ahjo comes with a [env.py](./ahjo/resources/files/env.py) file that enables running Alembic commands without running Ahjo.

The env.py modifications provide logging integration to Ahjo, default naming schema and possibility to run alembic according to project configuration. The engines are created according to configuration, and there is no need for storing plain-text connection strings in the project.

Usage example:
```
alembic -x main_config=config_development.jsonc downgrade -1
```

The [env.py](./ahjo/resources/files/env.py) is created in initialize-project command.


## Authentication with azure-identity
Instructions for enabling azure identity authentication in ahjo:

1. Install [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) & [azure-identity](https://pypi.org/project/azure-identity/) 
2. Set the config variable `azure_authentication` to `AzureIdentity`

Sign in interactively through your browser with the `az login` command.
If the login is successful, ahjo will use Azure credentials for creating an engine that connects to an Azure SQL database.


# Running actions from multiple projects
To run all selected actions from different projects at once, a single command "ahjo-multi-project-build" can be used:

```
ahjo-multi-project-build path/to/config_file.jsonc
```

Use `-c` or `--confirm` flag to enable confirmation messages for ahjo actions.  
Below is an example of JSONC config file. With the following definition, multi-project-build command executes complete-build actions of three ahjo projects:

```
{
    "projects_path": "path/to/projects_folder",
    "connection_info": {
        "sql_port": 14330,
        "sql_driver": "SQL Server",
        "target_server_hostname": "localhost"
    },
    "projects": {
        "ahjo_project_1_name": {
            "config": "path/to/projects_folder/ahjo_project_1_name/config_development.jsonc",
            "actions": [
                "complete-build"
            ]
        },
        "ahjo_project_2_name": {
            "config": "path/to/projects_folder/ahjo_project_2_name/config_development.jsonc",
            "actions": [
                "complete-build"
            ]        
        },
        "ahjo_project_3_name": {
            "config": "path/to/projects_folder/ahjo_project_3_name/config_development.jsonc",
            "actions": [
                "complete-build"
            ]        
        }
    }
}
```

Settings under `connection_info` contains database server definitions in the same format as in ahjo project config file (excluding `target_database_name` parameter, which is not used here).  
Currently in this version ahjo projects should be located under the folder specified in `projects_path` setting.  
Ahjo project names are listed under `projects` section in run order. In this example, the actions of project `ahjo_project_1_name` are executed first and the actions of project `ahjo_project_3_name` are executed last.  
The following settings are defined under the name of the ahjo project(s):

`config` - File path to the project-specific config file  
`actions` - List of project actions to be executed


# Ahjo project upgrade
Database updates can be run with `ahjo-upgrade` command. The command detects automatically the latest installed git version and runs the required database version updates (in order).
The upgrade actions are defined in a JSONC file and its location is defined in `upgrade_actions_file` setting in project config file.
The ahjo actions required for version upgrades are defined with key-value pairs, where key is the git version tag and value is a list of actions.
The list of actions can contain strings of action names or lists of action names and action parameters. 
If the action is defined with parameters, the action name is the first item in the list and the parameters are defined as a dictionary in the second item in the list. 
The dictionary contains the parameters of the action as key-value pairs, where key is the parameter name and value is the parameter value.

Below is an example of upgrade actions file:

```
{
	"v3.0.0": [
		"deploy",
        "data"
	],
    "v3.1.0": [ 
		"deploy",
		[
			"deploy-files",
			{
				"files": [
					"./database/procedures/dbo.procedure_1.sql", 
					"./database/procedures/dbo.procedure_2.sql"
				]
			}
		]
	],
	"v3.1.1": [
        "deploy"
	]
}
```

To upgrade specific version, use `-v` or `--version` flag:
```
ahjo-upgrade -v v3.1.0
```


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

# Building an MSI installation package (optional)

This assumes you have cloned the source code repository and have it open in a shell.

Create a new, empty build venv and install build requirements into it.

**Notice:** at the time of writing this (10/2023), [the latest stable cx_freeze version](https://cx-freeze.readthedocs.io/en/stable) (6.15.10) **does not support Python 3.12** yet. As soon as new cx_freeze version with Python 3.12 support is released, it should be taken in to use.

```
py -3.11 -m venv venv_msi_build
.\venv_msi_build\Scripts\Activate.ps1 
pip install -r .\msi_build_requirements.txt
```

**Notice:** the last command installs ahjo with the most common options. You may need to update msi_build_requirements.txt to suit your needs.

**Notice:** if you make changes to the source code, you must install ahjo into build venv again to have those changes included in the next build. Editable pip install doesn't work here, so don't use it.

With the build venv active, build the MSI package with the following command.

```
python .\msi_build.py bdist_msi
```

Find the built MSI installation package under (automatically created) `dist` directory. 

## Install Guide - MSI installation package

MSI installation package installs everything that is needed to execute ahjo shell commands including the required parts of the Python runtime setup. In other words, the target environment doesn't need to have Python installed and there is no need to create separate venvs for ahjo.

1. Run the msi installer with the default settings it offers
2. Make sure to start a new shell instance (e.g. Windows PowerShell) after the installation
3. After a successful installation the following CLI commands are available in the shell:
    - ahjo
    - ahjo-init-project
    - ahjo-multi-project-build
    - ahjo-upgrade
4. If a new shell instance can't find the executables, ensure that installation path is included in the PATH enviroment variable

# License
Copyright 2019 - 2023 ALM Partners Oy

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
