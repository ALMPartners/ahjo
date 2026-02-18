# Ahjo - Database deployment framework
#
# Copyright 2019 - 2026 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import os
import yaml
import ahjo.util.jsonc as json

from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typing import Optional


class Config:
    """Class for handling configuration."""

    def __init__(
        self,
        config_filename: str,
        key: str = "BACKEND",
        cli_args: dict = None,
        validate=False,
    ):
        """Initialize Config object by loading configuration from file.

        Arguments:
        ----------
        config_filename: str
            Path to the configuration file (JSON, JSONC, YAML or YML).
        key: str
            Key of the configuration block to be loaded. If None or empty,
            the entire configuration will be loaded.
        cli_args: dict, optional
            Command-line arguments that can extend or override the configuration file settings.
        validate: bool, optional
            Whether to validate the configuration after loading. Default is False.
        """
        self.config_filename = config_filename
        self.configuration = self.load_conf(config_filename, key)
        self.cli_args = cli_args or {}
        if key == "BACKEND" and validate:
            self.validate()

    def as_dict(self) -> dict:
        """Get the loaded configuration as a dictionary."""
        return self.configuration

    def load_conf(self, conf_file: str, key: str = "BACKEND"):
        """Read configuration from file (JSON, JSONC, YAML or YML)."""
        if not isinstance(conf_file, str):
            conf_file = str(conf_file)
        if conf_file.endswith(".json") or conf_file.endswith(".jsonc"):
            return self.load_json_conf(conf_file, key)
        elif conf_file.endswith(".yaml") or conf_file.endswith(".yml"):
            return self.load_yaml_conf(conf_file, key)
        else:
            raise FileNotFoundError(
                "Error: Configuration file must be in JSON, JSONC, YAML or YML format."
            )

    def _validate_path(self, conf_file: str) -> Path:
        """Validate that the config file exists and return a Path object."""
        f_path = Path(conf_file)
        if not f_path.is_file():
            raise FileNotFoundError(f"Config file not found: {f_path.resolve()}")
        return f_path

    def _extract_block(self, data: dict, key: str) -> dict:
        """Extract a config block by key."""
        if isinstance(data, dict):
            block = data.get(key, None)
            if block:
                return block
        return data

    def load_json_conf(self, conf_file: str, key: str = "BACKEND") -> dict:
        """Read configuration from file (JSON or JSONC).

        Return contents of 'key' block.
        """
        f_path = self._validate_path(conf_file)

        try:
            with open(f_path, encoding="utf-8") as f:
                raw_data = f.read()
        except Exception as e:
            raise IOError(f"Error reading config file: {e}")

        try:
            data = json.loads(raw_data)
        except Exception as e:
            raise ValueError(f"Error parsing JSON config file: {e}")

        return self._extract_block(data, key)

    def load_yaml_conf(self, conf_file: str, key: str = "BACKEND") -> dict:
        """Read configuration from file (YAML).

        Return contents of 'key' block.
        """
        f_path = self._validate_path(conf_file)

        try:
            with open(f_path, encoding="utf-8") as f:
                data = yaml.load(f, Loader=yaml.FullLoader)
        except Exception as e:
            raise IOError(f"Error reading or parsing YAML config file: {e}")

        return self._extract_block(data, key)

    def validate(self):

        config = self.as_dict()

        class AhjoConfig(BaseModel):
            model_config = ConfigDict(extra="allow")

            # Required fields
            allowed_actions: str | list[str]
            sql_port: int
            target_database_name: str
            target_server_hostname: str

            # Optional fields
            alembic_version_table: Optional[str] = "alembic_version"
            alembic_version_table_schema: Optional[str] = "dbo"
            skipped_actions: Optional[list[str]] = None
            azure_authentication: Optional[str] = None
            azure_identity_settings: Optional[dict] = None
            database_collation: Optional[str] = "Latin1_General_CS_AS"
            database_compatibility_level: Optional[int] = None
            database_data_path: Optional[str] = None
            database_file_growth: Optional[int] = 500
            database_init_size: Optional[int] = 100
            database_log_path: Optional[str] = None
            database_max_size: Optional[int] = 10000
            enable_database_logging: Optional[bool] = False
            log_table_schema: Optional[str] = "dbo"
            log_table: Optional[str] = "ahjo_log"
            git_table: Optional[str] = "git_version"
            git_table_schema: Optional[str] = "dbo"
            metadata_allowed_schemas: Optional[list[str]] = None
            password_file: Optional[str] = None
            sql_dialect: Optional[str] = "mssql+pyodbc"
            sql_driver: Optional[str] = None
            target_database_protected: Optional[bool] = False
            url_of_remote_git_repository: Optional[str] = None
            username_file: Optional[str] = None
            db_permissions: Optional[list[dict]] = None
            db_permission_invoke_method: Optional[str] = "sqlalchemy"
            upgrade_actions_file: Optional[str] = "./upgrade_actions.jsonc"
            catalog_collation_type_desc: Optional[str] = "DATABASE_DEFAULT"
            display_db_info: Optional[bool] = True
            context_connectable_type: Optional[str] = "engine"
            transaction_mode: Optional[str] = "begin_once"
            git_version_info_path: Optional[str] = None
            windows_event_log: Optional[bool] = False
            ahjo_action_files: Optional[list[dict]] = None
            sqla_url_query_map: Optional[dict] = None
            enable_sqlalchemy_logging: Optional[bool] = False
            save_test_results_to_db: Optional[bool] = False
            test_table_schema: Optional[str] = "dbo"
            test_table_name: Optional[str] = "ahjo_tests"
            exit_on_test_failure: Optional[bool] = False
            create_test_table_if_not_exists: Optional[bool] = True
            test_view_name: Optional[str] = "vwAhjoTests"
            test_view_schema: Optional[str] = "dbo"
            connect_resiliently: Optional[bool] = True
            connect_retry_count: Optional[int] = 20
            connect_retry_interval: Optional[int] = 10

        try:
            AhjoConfig(**config)
        except Exception:
            raise

        non_interactive = self.cli_args.get("non_interactive", False)

        if non_interactive:

            azure_auth = config.get("azure_authentication", None)

            if azure_auth is not None:
                if azure_auth == "ActiveDirectoryInteractive":
                    raise ValueError(
                        "Azure authentication method ActiveDirectoryInteractive is not supported in non-interactive mode."
                    )
            else:
                if config.get("username_file") is None:
                    raise ValueError(
                        "Username file is required in non-interactive mode."
                    )
                if config.get("password_file") is None:
                    raise ValueError(
                        "Password file is required in non-interactive mode."
                    )

    def save_config(self, output_path: str, format: str = "jsonc") -> bool:
        """Save the current configuration to a file in the specified format."""
        try:
            if format in ["json", "jsonc"]:
                with open(output_path, "w+", encoding="utf-8") as file:
                    json.dump(self.configuration, file, indent=4)
            elif format in ["yaml", "yml"]:
                with open(output_path, "w+", encoding="utf-8") as file:
                    yaml.dump(self.configuration, file, default_flow_style=False)
            else:
                raise ValueError(
                    f"Unsupported format '{format}'. Use 'json' or 'yaml'."
                )
            return True
        except Exception as err:
            raise IOError(f"Could not save config file: {err}")

    @staticmethod
    def get_config_path(config_filename: str) -> str:
        """Get configuration filename from environment variable if not given as argument."""
        if config_filename is None and "AHJO_CONFIG_PATH" in os.environ:
            return os.environ.get("AHJO_CONFIG_PATH")
        return config_filename

    @staticmethod
    def merge_config_files(config_filename: str) -> dict:
        """Return the contents of config_filename or merged contents,
        if there exists a link to another config file in config_filename.
        """
        config = Config(config_filename, key="")
        config_data = config.as_dict()
        local_path = config_data.get("LOCAL", None)
        if local_path is not None:
            try:
                local_data = Config(local_path, key="").as_dict()
                if local_data is not None:
                    merged_configs = Config.merge_nested_dicts(config_data, local_data)
                    return merged_configs
            except Exception as err:
                print(f"Could not open local config file {local_path}: {err}")
        return config_data

    @staticmethod
    def merge_nested_dicts(dict_a: dict, dict_b: dict, path: str = None) -> dict:
        """Merge dictionary b to dictionary a.

        If keys conflict, that is, the same key exists in both dictionaries,
        overwrite the value of dictionary a with the value of dictionary b.
        """
        if path is None:
            path = []
        for key in dict_b:
            if key in dict_a:
                if isinstance(dict_a[key], dict) and isinstance(dict_b[key], dict):
                    Config.merge_nested_dicts(
                        dict_a[key], dict_b[key], path + [str(key)]
                    )
                elif dict_a[key] == dict_b[key]:
                    pass  # same leaf value
                else:
                    # replace dict_a value with dict_b value
                    dict_a[key] = dict_b[key]
            else:
                dict_a[key] = dict_b[key]
        return dict_a
