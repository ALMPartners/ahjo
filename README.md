Ahjo Framework
====================

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ahjo)](https://pypi.org/project/ahjo/) [![PyPI](https://img.shields.io/pypi/v/ahjo)](https://pypi.org/project/ahjo/)

# <u>Description</u>

Ahjo is a database project framework and a deployment script. It is made to unify database project deployment and development practices and to give basic tooling for such projects. 

Ahjo provides a base scripts for database deployment with simple commands ("actions"), and the possibility to define custom actions for project's special needs. The scripts are designed to reduce accidental operations to production environments. The actions and their parts are logged by Ahjo.

Database tooling is currently based on sqlalchemy/alembic and SQL scripts. Support for other backends than Microsoft SQL Server is currently limited.

# <u>Dependencies</u>
## Common
* [alembic](https://pypi.org/project/alembic/)
* [pyparsing](https://pypi.org/project/pyparsing/)
* [SQL Alchemy](https://pypi.org/project/SQLAlchemy/)
* [PyYAML](https://pypi.org/project/PyYAML/)
* [lark](https://pypi.org/project/lark/)

## Platform-specific

### mssql
* [pyodbc](https://pypi.org/project/pyodbc/)

### azure
* [azure-identity](https://pypi.org/project/azure-identity/)

# <u>Install Guide</u>

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

## Install Guide 3 - MSI installation package

### Building an MSI installation package

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

### Installing the MSI package

MSI installation package installs everything that is needed to execute ahjo shell commands including the required parts of the Python runtime setup. In other words, the target environment doesn't need to have Python installed and there is no need to create separate venvs for ahjo.

1. Run the msi installer with the default settings it offers
2. Make sure to start a new shell instance (e.g. Windows PowerShell) after the installation
3. After a successful installation the following CLI commands are available in the shell:
    - ahjo
    - ahjo-init-project
    - ahjo-multi-project-build
    - ahjo-upgrade
    - ahjo-scan
    - ahjo-install-git-hook
    - ahjo-config
4. If a new shell instance can't find the executables, ensure that installation path is included in the PATH enviroment variable

# <u>Project Initialization</u>
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

# <u>Usage Example</u>

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

# <u>Scripts</u>

Below is a list of available scripts and their descriptions.

| Script  | Description |
| --- | --- |
| `ahjo` | Main script for running Ahjo actions. |
| `ahjo-init-project` | Script for initializing new Ahjo project. |
| `ahjo-multi-project-build` | Script for running actions from multiple projects at once. |
| `ahjo-upgrade` | Script for running version upgrades. |
| `ahjo-scan` | Script for searching matches with defined search rules from files in the working directory or git staging area. |
| `ahjo-install-git-hook` | Script for installing Ahjo scan command as a pre-commit hook. |
| `ahjo-config` | Script for converting config files between JSON/JSONC and YAML formats. |

# <u>Actions</u>

## Running actions
Ahjo actions are run with `ahjo` command. The command syntax with positional arguments is:
```
ahjo <action> <config_filename>
```
where `<action>` is the name of the action to be run and `<config_filename>` is the path to the project-specific config file. The config parameter is optional if the path is defined in environment variable `AHJO_CONFIG_PATH`.

The rest of the optional parameters are listed below.

| Argument  | Shorthand | Description | Default Value |
| --- | --- | --- | --- |
| `list` | | List all available actions and their descriptions. | |
| `--non-interactive` | `-ni` | Skip confirmation for actions that affect the database. | `False` |
| `--files` | | List of files to be used in action. | |
| `--object_type` | | Type of database object. | |
| `--skip-metadata-update` | `-sm` | Skip updating documented extended properties to database. | `False` |
| `--skip-alembic-update` | `-sa` | Skip running alembic migrations. | `False` |
| `--skip-git-update` | `-sg` | Skip updating current git version to git version table. | `False` |



It is also possible to pass custom command-line arguments and their values to actions. 

For example, to pass a custom argument `--example-arg` with values `x` and `y` to action `example-action`, use the following command:
```bash
ahjo example-action --example-arg x y
```

In the action, the values of the custom argument can be accessed from the context object:
```python
example_arg_values = context.get_command_line_arg("example-arg") # Returns a list of strings ["x", "y"]
```

## Pre-defined actions

## init-config
Initializes local configuration file. This file is intended to hold configurations that should not be versioned.

## init
Creates the database. Database is created with module [create_db.py](./ahjo/operations/tsql/create_db.py). Required configurations are *target_database_name*, *target_server_hostname* and *sql_port*. For optional configurations, see config file cheat sheet below.

## structure
Creates database structure, that is schemas, tables and constraints. Primary method runs all SQL files under directories *./database/schemas*, *./database/tables* and *./database/constraints*. Alternate method runs SQL script *./database/create_db_structure.sql*. If structure can't be created with primary method (one of the listed directories does not exists etc.), alternate method is attempted.

## deploy
Runs alembic migrations, creates views, procedures and functions. First, runs *alembic upgrade head*. Second, creates functions, views and procedures by executing all SQL files under directories *./database/functions*, *./database/views* and *./database/procedures*. Third, attempts to update documented extended properties to database. Finally, updates current GIT version (`git describe`) to GIT version table.

## deploy-files
Runs *alembic upgrade head*, creates database objects by executing all SQL files listed in --files argument and updates current GIT version (`git describe`) to GIT version table. 
Example usage: `ahjo deploy-files .\config_development.jsonc --files ./database/procedures/dbo.procedure.sql ./database/functions/dbo.function.sql` .

## data
Runs data insertion scripts. Runs all SQL files under *./database/data*.

## testdata
Inserts data for testing into database. Runs all SQL files under *./database/data/testdata*.

## complete-build
Runs actions init, deploy, data, testdata and test in order.

## drop
Drops all views, procedures, functions, clr-procedures and assemblies that are listed in directory *./database*. Drops are executed with TRY-CATCH.

## drop-files
Drops database objects from locations that are listed in --files argument. Database objects can be views, procedures, functions or assemblies. Object type is read from --object_type argument. Acceptable --object_type parameters: view, procedure, function, assembly.
Example usage: `ahjo drop-files .\config_development.jsonc --files ./database/procedures/dbo.procedure_1.sql ./database/procedures/dbo.procedure_2.sql --object_type procedure` .

## downgrade
Reverts the database back to basic structure.
First, drops all views, procedures, functions, clr-procedures and assemblies that are listed in directory *./database*. Drops are executed with TRY-CATCH. Second, runs `alembic downgrade base`.

## version
Prints the alembic- and git-version currently in the database.
Alembic version is read from *alembic_version_table*. GIT version is read from *git_table*.

## update-file-obj-prop
Write objects and their extended properties (only SQL Server) to JSON files under *./docs* directory.
Documented schemas are listed in *metadata_allowed_schemas*.

## update-db-obj-prop
Update documented extended properties (only SQL Server) from JSON files under *./docs* directory to database.
Updated schemas are listed in *metadata_allowed_schemas*.

## test
Runs tests and returns the results.
Runs all SQL scripts under *./database/tests*.

## list
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

# <u>Config File</u>
Ahjo requires config file to be JSON, JSONC (JSON with comments) or YAML format. Ahjo configs are located in *BACKEND* section of file. 
Below is an example of config file (in both JSONC and YAML format) and a cheat sheet for config file parameters.

## JSONC config file
```jsonc
{
    "BACKEND": {
        "allowed_actions": "ALL",
        //Git repository and git version table information
        "url_of_remote_git_repository": "https:\\\\github.com\\user\\projectx\\",
        "git_table": "git_version",
        "git_table_schema": "dbo",
        //Database connection information
        "sql_port": 1433,
        "sql_driver": "ODBC Driver 17 for SQL Server",
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

## YAML config file
```yaml
BACKEND:
  ## List of allowed Ahjo actions. If all actions are allowed use "ALL" option.
  allowed_actions: ALL
  ## Git repository url and git version table information.
  url_of_remote_git_repository: ''
  git_table: git_version
  git_table_schema: dbo
  ## Database connection information.
  sql_port: 14330
  sql_driver: ODBC Driver 17 for SQL Server
  sql_dialect: mssql+pyodbc
  target_server_hostname: localhost
  target_database_name: DB_NAME
```

## Config file cheat sheet
| Parameter  | Required | Description | Type | Default Value |
| --- | --- | --- | --- | --- |
| `alembic_version_table` | No | Name of Alembic version table. Table holds the current revision number. | `str` | `"alembic_version"` |
| `alembic_version_table_schema` | No | Schema of Alembic version table. | `str` | `"dbo"` |
| `allowed_actions` | Yes | List of actions Ahjo is allowed to execute. If all actions are allowed, use `"ALL"`. | str or list of str | |
| `skipped_actions` | No | List of actions that are skipped. | list of str | `[]` |
| `azure_authentication` | No | Authentication type to Azure AD. Possible values are `"ActiveDirectoryPassword"`, `"ActiveDirectoryInteractive"`, `"ActiveDirectoryIntegrated"` and `"AzureIdentity"`. | `str` | |
| `azure_identity_settings` | No | A dictionary containing parameters for azure-identity library (used only if azure_authentication is `"AzureIdentity"`). Dictionary holds a key: `"token_url"` (str). Note: currently ahjo supports only AzureCliCredential authentication method. | `dict` | |
| `database_collation` | No | Collation of database. If the defined collation is different from the database collation, a warning is logged. | `str` | `"Latin1_General_CS_AS"` |
| `database_compatibility_level` | No | Compatibility level of database. | `int` | Depends on server. SQL Server 2017 default is `140`. |
| `database_data_path` | No | Path of database data file. | `str` | |
| `database_file_growth` | No | The size (MB) of how much database data file will grow when it runs out of space. | `int` | `500` |
| `database_init_size` | No | Initial size (MB) of database data file. | `int` | `100` |
| `database_log_path` | No | Path of database log file. | `str` | |
| `database_max_size` | No | Maximum size (MB) of database data file. | `int` | `10000` |
| `enable_db_logging` | No | Enable logging to database. | `boolean` | `true` |
| `log_table_schema` | No | Schema of log table. | `str` | `"dbo"` |
| `log_table` | No | Name of ahjo log table. | `str` | `"ahjo_log"` |
| `git_table` | No | Name of git hash table. Table holds current branch, commit hash and URL of remote repository. | `str` | `"git_version"` |
| `git_table_schema` | No | Schema of git hash table. | `str` | `"dbo"` |
| `metadata_allowed_schemas` | No | List of schemas that extended properties will be written to JSON files and updated to database. If list left empty, nothing is documented or updated. | list of str | |
| `password_file` | No | Path of file where password will be stored. If no path given, credentials are asked everytime any database altering action is run. | `str` | |
| `sql_dialect` | No | Dialect used by SQL Alchemy. | `str` | `"mssql+pyodbc"` |
| `sql_driver` | No | Name of ODBC driver. | `str` | |
| `sql_port` | Yes | Port number of target database server. | `int` | |
| `target_database_name` | Yes | Name of target database. | `str` | |
| `target_server_hostname` | Yes | Host name of target database server. | `str` | |
| `url_of_remote_git_repository` | No | URL of project's remote repository. | `str` | |
| `username_file` | No | Path of file where username will be stored. If no path given, credentials are asked everytime any database altering action is run. | `str` | |
| `db_permissions` | No | List of dictionaries containing file locations & scripting variables for setting up database permissions from sql file(s). Dictionary holds keys: "source" (`str`) and "variables" (`dict`). | `list` of `dict` | |
| `db_permission_invoke_method` | No | Invoke method for setting up database permissions. Available options: `"sqlcmd"` or `"sqlalchemy"` (default). | `str` | `"sqlalchemy"` |
| `upgrade_actions_file` | No | Configuration file for upgrade actions. | `str` | `"./upgrade_actions.jsonc"` |
| `catalog_collation_type_desc` | No | Catalog collation setting of database. If the defined setting is different from the database setting, a warning is logged. Applies only to Azure SQL Database | `str` | `"DATABASE_DEFAULT"` |
| `display_db_info` | No | Print database collation information to console before running actions. | `boolean` | `true` |
| `context_connectable_type` | No | Type of SQLAlchmey object returned by Context.get_connectable(). Possible values are `"engine"` and `"connection"`. | `str` | `"engine"` |
| `transaction_mode` | No | Transaction management style for ahjo actions. Applied only if context_connectable_type is `"connection"`. Possible values are `"begin_once"` and `"commit_as_you_go"`. If `"begin_once"`, a transaction is started before running actions and committed after all actions are run. If `"commit_as_you_go"`, a transaction is started before running actions but not committed automatically. | `str` | `"begin_once"` |
| `git_version_info_path` | No | Path to git version info file. Retrieve git commit information from this file if git repository is not available. JSON file format: `{"repository": "<url>", "commit": "<commit hash>", "branch": "<branch name>"}` | `str` | |
| `windows_event_log` | No | Log Ahjo events to Windows Event Log. | `boolean` | `false` |
| `ahjo_action_files` | No | Defines the location and name of project-specific Ahjo actions files. | list of dict | |
| `sqlalchemy.url` | No | SQLAlchemy database URL. If defined, overrides the values of `dialect`, `sql_port`, `sql_driver`, `target_server_hostname` and `target_database_name`. | `str` | |
| `sqlalchemy.*` | No | Items under sqlalchemy.* are passed as parameters to SQLAlchemy's [create_engine](https://docs.sqlalchemy.org/en/20/core/engines.html#sqlalchemy.create_engine) function. For example `sqlalchemy.pool_size: 10` is passed as pool_size=10 to `create_engine` function. | `dict` | If `dialect` is `mssql+pyodbc`: `"sqlalchemy.use_insertmanyvalues": false`, `"sqlalchemy.use_setinputsizes": false` |
| `sqla_url_query_map` | No | A dictionary containing [SQLAlchemy URL query connection parameters](https://docs.sqlalchemy.org/en/20/core/engines.html#sqlalchemy.engine.URL.query). | `dict` | If ODBC Driver 18: `{"Encrypt" : "yes", "LongAsMax": "Yes"}`. If ODBC Driver 17 or older: `{"Encrypt" : "no"}`. Else: `{}` |
| `enable_sqlalchemy_logging` | No | Enable [SQLAlchemy logging](https://docs.sqlalchemy.org/en/20/core/engines.html#configuring-logging). | `boolean` | `false` |

## Config conversion
Config file can be converted from JSON/JSONC to YAML or vice versa with `ahjo-config` command: 
```
ahjo-config --convert-to <target_format> --config <config_file_path> --output <output_file_path>
```


# <u>Using Alembic with Ahjo</u>
Alembic upgrade HEAD is used in deploy action, but for many use cases other alembic commands are needed. For these needs Ahjo comes with a [env.py](./ahjo/resources/files/env.py) file that enables running Alembic commands without running Ahjo.

The env.py modifications provide logging integration to Ahjo, default naming schema and possibility to run alembic according to project configuration. The engines are created according to configuration, and there is no need for storing plain-text connection strings in the project.

Usage example:
```
alembic -x main_config=config_development.jsonc downgrade -1
```

The [env.py](./ahjo/resources/files/env.py) is created in initialize-project command.


# <u> Authentication </u>
Depending on the configuration, the database credentials can be stored into files or be asked when needed, once per application run. The credential handling is shared with alembic with custom [env.py](./ahjo/resources/files/env.py) file. The username and password files can be defined in the config file with the keys `username_file` and `password_file`. If no path is given, credentials are asked every time any database altering action is run. The password and username files are created automatically if they do not exist.

## Microsoft Entra
Ahjo supports authentication with Microsoft Entra / Azure AD. The authentication type is defined in the config file with the key `azure_authentication`. The possible values are `"ActiveDirectoryPassword"`, `"ActiveDirectoryInteractive"`, `"ActiveDirectoryIntegrated"` and `"AzureIdentity"`. The authentication type `"AzureIdentity"` is used for authentication with azure-identity library (see [Azure-identity](#Azure-identity)).

## Azure-identity
Instructions for enabling azure identity authentication in ahjo:

1. Install [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) & [azure-identity](https://pypi.org/project/azure-identity/) 
2. Set the config variable `azure_authentication` to `AzureIdentity`

Sign in interactively through your browser with the `az login` command.
If the login is successful, ahjo will use Azure credentials for creating an engine that connects to an Azure SQL database.


# <u>Running actions from multiple projects</u>
To run all selected actions from different projects at once, a single command "ahjo-multi-project-build" can be used:

```
ahjo-multi-project-build path/to/config_file.jsonc
```

Use `-c` or `--confirm` flag to enable confirmation messages for ahjo actions.  
Below is an example of JSONC config file. With the following definition, multi-project-build command executes complete-build actions of three ahjo projects:

```json
{
    "projects_path": "path/to/projects_folder",
    "connection_info": {
        "sql_port": 14330,
        "sql_driver": "ODBC Driver 17 for SQL Server",
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


# <u>Ahjo project upgrade</u>
Database updates can be run with `ahjo-upgrade` command. The command detects automatically the latest installed git version and runs the required database version updates (in order).
The upgrade actions are defined in a JSONC file and its location is defined in `upgrade_actions_file` setting in project config file.
The ahjo actions required for version upgrades are defined with key-value pairs, where key is the git version tag and value is a list of actions.
The list of actions can contain strings of action names or lists of action names and action parameters. 
If the action is defined with parameters, the action name is the first item in the list and the parameters are defined as a dictionary in the second item in the list. 
The dictionary contains the parameters of the action as key-value pairs, where key is the parameter name and value is the parameter value.

Below is an example of upgrade actions file:

```json
{
	"v3.0.0": ["deploy", "data"],
	"v3.1.0": ["deploy", ["deploy-files", {"files": ["./database/procedures/dbo.procedure_1.sql", "./database/procedures/dbo.procedure_2.sql"]}]],
	"v3.1.1": ["deploy"]
}
```

To upgrade specific version, use `-v` or `--version` flag:
```
ahjo-upgrade -v v3.1.0
```

# <u>Ahjo scan</u>
`ahjo-scan` command can be used to search for matches with defined search rules from files in the working directory or git staging area. The search results are printed to the console and logged to a file. The command can be used to search e.g. illegal database object modifications, sensitive information or custom regex patterns defined by the user. 

| Argument  | Shorthand | Description | Required | Default Value |
| --- | --- | --- | --- | --- |
| `--search-rules`  | `-r` | Path to YAML file that defines the search rules. | No | `./ahjo_scan_rules.yaml` |
| `--stage` | `-st` | Scan files in git staging area instead of working directory. | No | `False` |
| `--ignore-config` | `-ig` | Path to YAML file that defines the ignore rules. | No | `./ahjo_scan_ignore.yaml` |
| `--init` | `-in` | Initialize config files for scan rules and ignored scan results. | No | `False` |

The search rules are defined as a list of dictionaries. Each dictionary contains a search rule name, a list of file paths to be searched and parameters for the search rule. It is also possible to define a custom regex pattern for the search rule instead of using predefined search rules. The regex pattern is defined as a string in the `pattern` parameter.

## Built-in search rules

| Rule name | Description | Acceptable parameters |
| --- | --- | --- |
| `hetu` | Finnish Personal Identity Number | `filepath` |
| `email` | Email address | `filepath` |
| `sql_object_modification` | Database object modification (SQL Server). The search rule searches for database object modifications from SQL files. The search rule can be configured to search for modifications of specific database object types (e.g. `PROCEDURE`) and/or specific database object schemas and/or specific database objects (e.g. table names). If no parameters are defined, the search rule searches for modifications of all database object types, all schemas and all objects. | `object_types`, `schemas`, `objects`, `filepath` |
| `alembic_table_modification` | Database table modification (Alembic). The search rule searches for database table modifications from alembic migrations. If no parameters are defined, the search rule searches for modifications of all schemas and all tables. | `schemas`, `filepath` |
| `sql_insert` | Database insert (SQL Server). The search rule searches for database inserts from SQL files. The search rule can be configured to search for inserts to specific database object schemas and/or specific database tables. If no parameters are defined, the search rule searches for inserts to all schemas and all tables. | `schemas`, `tables`, `filepath` |

## Rule parameters
| Parameter  | Description | Type |
| --- | --- | --- |
| `filepath` | List of file paths. | `list` |
| `pattern` | Custom regex pattern. | `str` |
| `schemas` | List of database object schemas. | `list` |
| `object_types` | List of database object types. | `list` |
| `objects` | List of database objects. | `list` |
| `tables` | List of database tables. | `list` |

## Search rules file
The search rules are defined in a YAML file. The file can be initialized with `--init` or `-in` flag. By default, the search rules are defined in `./ahjo_scan_rules.yaml` file. Use `--search-rules` or `-r` flag to define a different path for the search rules file.

Here is an example of search rules file:
```yaml
- name: sql_object_modification
  filepath: 
    - database/
  object_types:
    - PROCEDURE
  schemas:
    - dummy
    - utils
- name: hetu
  filepath: 
    - database/
    - alembic/versions/
- name: select_star # Custom rule
  filepath: 
    - database/
  pattern: SELECT \* # This is a regular expression
```

## Ignoring scan results
To filter out false positives, scan results can be ignored by defining ignore rules in a YAML file. The ignore rules are defined as a list of dictionaries. Each dictionary contains a file path and a list of matches or rules to be ignored. The file can be initialized with `--init` or `-in` flag. By default, the ignore rules are defined in `./ahjo_scan_ignore.yaml` file. Use `--ignore-config` or `-ig` flag to define a custom path for the ignore results file.

Below is an example of ignore results file:
```yaml
- file_path: database/data/persons.sql
  matches:
    - 010106A921P
    - 130202A904N
- file_path: database/data/addresses.sql
  rules:
    - sql_object_modification
```

## Scan as a pre-commit hook
Ahjo scan command can be used as a pre-commit hook to prevent committing files that contain e.g. sensitive information or illegal database object modifications.
This can be accomplished by utilizing a Git pre-commit hook script that automatically executes ahjo-scan command on each commit and prevents the commit if the scan finds matches with the defined search rules. To use the hook, you need to have the `ahjo-scan.exe` accessible as a shell command. (e.g. the tool is installed from an MSI package, see Installation Guide 3).

### Setting up the hook
To install the hook, run the following command in the project root directory:
```
ahjo-install-git-hook
```
The script creates a file named `pre-commit` to Git hooks directory. By default, Git hooks are located in the `.git/hooks` directory of the repository. This can be changed by setting the `core.hooksPath` configuration variable to the desired path. See [Git documentation](https://git-scm.com/docs/githooks) for more information.


# <u>Logging</u>
### Log files
Everything Ahjo prints to console, is also written into log file `ahjo.log` in the project root directory. The log files are created automatically if they do not exist.

### Database log
Actions that affect the database are logged to a database table by default (can be disabled by setting `enable_db_logging` to `false` in config file). The name and schema of the log table can be defined in the config file. The log table is created automatically if it does not exist. 

### Windows Event Log
Logging can be done to Windows Event Log by setting `windows_event_log` to `true` in config file. This feature can be utilized for Azure Monitor activities, for example. 

### SQLAlchemy log
SQL Alchemy logging can be enabled by setting `enable_sqlalchemy_logging` to `true` in config file. The logging is done to a file named `sqlalchemy.log` in the project root directory. The log files are created automatically if they do not exist.

# <u>Customization</u>

## Setting up custom action files
Every default Ahjo action and multiaction can be overwritten in project's Ahjo actions file. By default, the file is located in `ahjo_actions.py`, but the location can be changed in config file with key `ahjo_action_files`. It is possible to define multiple Ahjo actions files. This can be useful for example when you want to use different actions for different environments or separate actions that are compatible with MSI-installed ahjo from actions that are compatible with pip-installed ahjo. The action files are loaded in order, so if you define multiple actions for the same action name, the last loaded action file will be used. If a multi-action uses actions from different files, remember to load all the subactions before the multi-action. Here is an example of `ahjo_action_files` configuration:
```jsonc
"ahjo_action_files": [
    {
        "source_file": "ahjo_prod_actions.py", // The location is relative to project root directory.
        "name": "Example project Ahjo actions (prod)" // Name is used in logging.
    },
    {
        "source_file": "ahjo_dev_actions.py", 
        "name": "Example project Ahjo actions (dev)"
    }
]
```

## Overwriting default Ahjo actions

In example below, *'init'* and *'complete-build'* actions are overwritten.
```python
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

# <u>License</u>
Copyright 2019 - 2024 ALM Partners Oy

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
