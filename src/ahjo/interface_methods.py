# Ahjo - Database deployment framework
#
# Copyright 2019 - 2025 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import ahjo.util.jsonc as json
import yaml
import os
from logging import getLogger
from pathlib import Path
from re import sub
from typing import Iterable, List, Union


logger = getLogger("ahjo")


def load_conf(conf_file: str, key: str = "BACKEND"):
    """Read configuration from file (JSON, JSONC, YAML or YML)."""
    if not isinstance(conf_file, str):
        conf_file = str(conf_file)
    if conf_file.endswith(".json") or conf_file.endswith(".jsonc"):
        return load_json_conf(conf_file, key)
    elif conf_file.endswith(".yaml") or conf_file.endswith(".yml"):
        return load_yaml_conf(conf_file, key)
    else:
        logger.error(
            "Error: Configuration file must be in JSON, JSONC, YAML or YML format."
        )
        return False


def load_json_conf(conf_file: str, key: str = "BACKEND") -> dict:
    """Read configuration from file (JSON or JSONC).

    Return contents of 'key' block.
    """
    f_path = Path(conf_file)
    if not f_path.is_file():
        logger.error("No such file: " + f_path.absolute().as_posix())
        return None
    with open(f_path, encoding="utf-8") as f:
        raw_data = f.read()
    data = json.loads(raw_data)
    key_value = data.get(key, None)
    if key_value:
        return key_value
    return data


def load_yaml_conf(conf_file: str, key: str = "BACKEND") -> dict:
    """Read configuration from file (YAML).

    Return contents of 'key' block.
    """
    f_path = Path(conf_file)
    if not f_path.is_file():
        logger.error("No such file: " + f_path.absolute().as_posix())
        return None
    with open(f_path, encoding="utf-8") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    if isinstance(data, dict):
        key_value = data.get(key, None)
        if key_value:
            return key_value
    return data


def get_config_path(config_filename: str) -> str:
    """Get configuration filename from environment variable if not given as argument."""
    if config_filename is None and "AHJO_CONFIG_PATH" in os.environ:
        return os.environ.get("AHJO_CONFIG_PATH")
    return config_filename


def are_you_sure(message: Union[str, list], use_logger: bool = True) -> bool:
    """Ask confirmation for action.

    Arguments
    ---------
    message: str or list
        Message(s) to display before user confirmation.
    use_logger: bool
        If false, logger is disabled.

    Returns
    -------
    bool
        True if the action is going to happen, False if the user does not permit the action.
    """
    display_message(message, use_logger)
    display_message("Are you sure you want to proceed?", use_logger)
    choise = input("[Y/N] (N): ")
    if choise == "y" or choise == "Y":
        display_message("confirmed", use_logger)
        return True
    display_message("cancelled", use_logger)
    return False


def verify_input(
    message: Union[str, list],
    input_to_verify: str,
    input_name: str,
    use_logger: bool = True,
) -> bool:
    """Verify input with user.

    Arguments
    ---------
    message: str or list
        Message(s) to display before user confirmation.
    input_to_verify: str
        Value to verify.
    input_name: str
        Name of the input.
    use_logger: bool
        If false, logger is disabled.

    Returns
    -------
    bool
        True if the input is correct, False if input_to_verify does not match the user's input.
    """
    display_message(message, use_logger)
    display_message(f"Please type {input_name} name to continue: \n", use_logger)
    user_input = input()
    if user_input == input_to_verify:
        display_message("confirmed", use_logger)
        return True
    display_message(
        "\nInput does not match the configured value: "
        + input_to_verify
        + ". Cancelling.",
        use_logger,
    )
    return False


def display_message(message: Union[str, list], use_logger: bool = True):
    """Print or log a message (str) or multiple messages (list)."""
    if isinstance(message, list):
        for msg in message:
            logger.info(msg) if use_logger else print(msg)
    else:
        logger.info(message) if use_logger else print(message)


def remove_special_chars(in_string: str) -> str:
    """Return a cleared string, that is, remove all characters except
    - alphabetical (A-Z) characters
    - numerical characters
    - underscores
    """
    out_string = in_string.replace(" ", "_")
    out_string = sub("[^a-zA-Z0-9_]", "", out_string)
    out_string = out_string.lower()
    return out_string


def format_to_table(lst_of_iter: List[Iterable]) -> str:
    """Format list of iterables to nice human-readable table."""
    if not lst_of_iter:
        return "No output."
    col_widths = [0] * len(lst_of_iter[0])
    for row in lst_of_iter:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    col_formats = [f"{{:<{width + 2}}}" for width in col_widths]
    formatted_output = ""
    for row in lst_of_iter:
        for i, cell in enumerate(row):
            formatted_output += col_formats[i].format(str(cell))
        formatted_output += "\n"
    return formatted_output


def rearrange_params(kwarg_map):
    """Decorator for rearranging keyword arguments."""

    def decorator(func):
        def wrapped(*args, **kwargs):
            new_kwargs = {}
            for k, v in kwargs.items():
                if k in kwarg_map:
                    logger.debug(
                        f"Keyword argument '{k}' in '{func.__name__}' is deprecated. Use '{kwarg_map[k]}' instead."
                    )
                new_kwargs[kwarg_map.get(k, k)] = v
            return func(*args, **new_kwargs)

        return wrapped

    return decorator
