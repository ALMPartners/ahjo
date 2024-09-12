# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

import copy
import sys
import os
import ahjo.scripts.master_actions
import networkx as nx
import importlib
from ahjo.interface_methods import load_conf, are_you_sure
from ahjo.operations.general.git_version import _get_all_tags, _get_git_version, _get_previous_tag, _checkout_tag
from ahjo.operations.general.db_info import print_db_collation
from ahjo.action import execute_action, import_actions, DEFAULT_ACTIONS_SRC
from ahjo.context import Context
from logging import getLogger


sys.path.append(os.getcwd())
logger = getLogger('ahjo')

def upgrade(config_filename: str, context: Context, version: str = None, skip_confirmation: bool = False) -> bool:
    """Upgrade database with upgrade actions.
    
    Parameters
    ----------
    config_filename : str
        Path to the configuration file.
    context : ahjo.context.Context
        Context object.
    version : str, optional
        Version to be upgraded. If not defined, the next upgradable version is upgraded.
    skip_confirmation : bool, optional
        Skip confirmation prompt. Default is False.
    
    Returns
    -------
    bool
        True if upgrade was successful, otherwise False.
    """
    try:
        # Load settings
        config = load_conf(config_filename)
        upgrade_actions = load_conf(config.get("upgrade_actions_file", f"./upgrade_actions.jsonc"))
        git_table_schema = config.get('git_table_schema', 'dbo')
        git_table = config.get('git_table', 'git_version')
        connectable_type = config.get("context_connectable_type", "engine")
        updated_versions = []

        # Display database collation
        if context.configuration.get("display_db_info", True):
            print_db_collation(context)

        # Get the current git commit from database
        _, _, current_db_version = _get_git_version(context.get_connectable(), git_table_schema, git_table)

        # Get all tags from the git repository
        git_tags = set(_get_all_tags())

        if current_db_version not in git_tags:
            raise ValueError(f"Current version in the database ({current_db_version}) has no corresponding tag in the git repository. The current version should be tagged in the git repository.")

        # Create version dependency graph
        tag_graph = create_version_dependency_graph(git_tags)
        reverse_tag_graph = tag_graph.reverse()

        # Check if database is up to date
        upgradable_versions = set(reverse_tag_graph.neighbors(current_db_version))
        if len(upgradable_versions) == 0:
            logger.info("Database is already up to date. The current database version is " + current_db_version)
            return True

        # Get versions that are older than the current database version
        older_versions = set(nx.descendants(tag_graph, current_db_version))

        # Omit config versions that are older than the current database version
        config_versions = set(upgrade_actions.keys()) - older_versions

        # Get the next version to upgrade
        next_version_upgrade = get_next_version_upgrade(
            next_upgrades_in_config = list(upgradable_versions & config_versions),
            current_db_version = current_db_version,
            upgradable_versions = upgradable_versions
        )

        # Get ordered list of versions to update
        ordered_versions = get_upgrade_version_path(
            tag_graph = tag_graph, 
            config_version_graph = tag_graph.subgraph(config_versions),
            next_version_upgrade = next_version_upgrade
        )

        # Filter upgrade_actions to include only the versions that are in the ordered_versions list
        version_actions = copy.deepcopy(upgrade_actions)
        for v in upgrade_actions:
            if v not in ordered_versions:
                version_actions.pop(v)
 
        # Validate upgrade actions
        validate_upgrade_actions(version_actions)

        # Validate version from user input
        if version is not None:
            version_actions = validate_version(version, version_actions, current_db_version)
        
        if not skip_confirmation:
            # Format are_you_sure message
            are_you_sure_msg = ["You are about to run the following upgrade actions: ", ""]
            for tag in version_actions:
                are_you_sure_msg.append(tag + ":")
                action_names = [action[0] if isinstance(action, list) else action for action in version_actions[tag]]
                are_you_sure_msg.append(" " * 2 + ", ".join(action_names))
            are_you_sure_msg.append("")

            # Confirm action
            if not are_you_sure(are_you_sure_msg, False): return False

        for git_version in version_actions:

            # Checkout the next upgradable git version
            _checkout_tag(git_version)
            config = load_conf(config_filename)

            # Update version info in the database logger
            if config.get("enable_database_logging", True):
                for handler in logger.handlers:
                    if handler.name == "handler_database":
                        handler.flush()
                        handler.db_logger.set_git_commit(git_version)
                        break

            # Reload ahjo actions
            import_actions(
                ahjo_action_files = config.get("ahjo_action_files", DEFAULT_ACTIONS_SRC), 
                reload_module = True
            )

            # Deploy version upgrades
            actions = version_actions[git_version]
            for action in actions:

                # Add parameters
                kwargs = {}
                if isinstance(action, list):
                    action_name = action[0]
                    parameters = action[1]
                    for arg in parameters:
                        kwargs[arg] = parameters[arg]
                else:
                    action_name = action

                # Run action
                execute_action(
                    *[action_name, config_filename, None, True, context],
                    **kwargs
                )

            # Check that the database version was updated
            _, _, db_version = _get_git_version(context.get_connectable(), git_table_schema, git_table)
            if db_version != git_version:
                raise Exception(f"Database (version {db_version}) was not updated to match the git version: {git_version}")
            
            updated_versions.append(db_version)

        if connectable_type == "connection":
            connection = context.get_connectable()
            connection.commit()
            connection.close()

    except Exception as error:
        logger.error('Ahjo project upgrade failed:')
        logger.error(error)
        if connectable_type == "connection":
            logger.error('Aborted upgrade. Changes were not committed to the database.')
        return False

    else:
        logger.info("The following versions were successfully upgraded: ")
        for version in updated_versions:
            logger.info(" " * 2 + version)
        logger.info("------")

    return True


def get_next_version_upgrade(next_upgrades_in_config: list, current_db_version: str, upgradable_versions: set) -> str:
    """Get the next version to upgrade from the current database version.
    
    Parameters
    ----------
    next_upgrades_in_config
        List of upgradable versions in the upgrade actions.
    current_db_version
        Current database version.
    upgradable_versions
        Set of upgradable versions.

    Returns 
    -------
    str
        Next version to upgrade from the current database version.
    """
    upgradable_versions_str = ", ".join(list(upgradable_versions))

    if len(upgradable_versions) == 1:
        next_versions_str = f"The next upgradable version is: {upgradable_versions_str}."
    else:
        next_versions_str = f"The next upgradable versions are: {upgradable_versions_str}."

    if len(next_upgrades_in_config) > 1:
        error_msg = f"""Conflicting upgrade actions found for the current database version ({current_db_version}). 
        {next_versions_str} Only one upgrade version should be defined for the current database version."""
        raise ValueError(error_msg)

    if len(next_upgrades_in_config) == 0:
        raise ValueError(f"The current database version ({current_db_version}) has no upgradable version in the upgrade actions. {next_versions_str}")

    return next_upgrades_in_config[0]


def get_upgrade_version_path(tag_graph: nx.DiGraph, config_version_graph: nx.DiGraph, next_version_upgrade: str) -> list:
    """Get ordered list of versions to upgrade. 

    Parameters
    ----------
    tag_graph
        Tag graph. Each node represents a version and each edge represents a dependency to the previous version.
    config_version_graph
        Version graph. Each node represents a version and each edge represents a dependency to the previous version.
        Versions older than the current database version are omitted in the graph.
    next_version_upgrade
        Next version to upgrade from the current database version. 
        This version is the starting point for the upgrade path.

    Returns
    -------
    list
        Ordered list of versions to upgrade.
    """

    # Check if there are no version gaps in the upgrade actions
    if not nx.is_weakly_connected(config_version_graph):

        # Get nodes that are in the tag graph but not in the config version graph
        tag_diff_nodes = set(tag_graph.nodes) - set(config_version_graph.nodes)
        missing_versions = []

        # Collect missing versions (in upgrade actions) to missing_versions
        for node in tag_diff_nodes:
            node_edges = list(tag_graph.in_edges(node)) + list(tag_graph.out_edges(node))
            for edge in node_edges:
                if edge[1] in config_version_graph.nodes:
                    missing_versions.append(edge[0])
                if edge[0] in config_version_graph.nodes:
                    missing_versions.append(edge[1])

        if len(missing_versions) > 0:
            missing_versions_str = ", ".join(missing_versions)
            error_msg = f"""Upgrade actions are not defined for the following versions: {missing_versions_str}.\nCheck that the upgrade actions are defined correctly."""
            raise ValueError(error_msg)

    # Get the latest version in the upgrade actions (version nodes with no incoming edges)
    latest_versions_in_config = [node for node in config_version_graph.nodes if config_version_graph.in_degree(node) == 0]
    
    if len(latest_versions_in_config) > 1:
        latest_versions_in_config_str = ", ".join(latest_versions_in_config)
        raise ValueError(f"Multiple latest versions found in the upgrade actions: {latest_versions_in_config_str}. Check that the upgrade actions are defined correctly.")
    
    if len(latest_versions_in_config) == 0:
        raise ValueError("No latest version found in the upgrade actions. Check that the upgrade actions are defined correctly.")

    # Get all simple paths from the next_version_upgrade to the latest version in config_version_graph
    config_version_paths = list(
        nx.all_simple_paths(
            config_version_graph.reverse(), 
            source = next_version_upgrade, 
            target = latest_versions_in_config[0]
        )
    )
    
    if len(config_version_paths) > 1:
        config_version_paths_str = "\n".join([", ".join(path) for path in config_version_paths])
        raise ValueError(f"Multiple upgrade paths found in the upgrade actions: {config_version_paths_str}. Check that the upgrade actions are defined correctly.")

    return config_version_paths[0]


def create_version_dependency_graph(versions: set) -> nx.DiGraph:
    """Create a version dependency graph.

    Parameters
    ----------
    versions
        Set of versions.

    Returns
    -------
    nx.DiGraph
        Version dependency graph.
    """
    
    G = nx.DiGraph()
    
    for version in versions:
        try:
            previous_version = _get_previous_tag(version)
        except: # No previous version found.
            continue
        else: # Previous version found
            G.add_edge(version, previous_version)

    return G


def plot_version_dependency_graph(G: nx.DiGraph, current_version: str = None, upgrade_action_versions: list = None, layout: str = "spring") -> None:
    """Plot the version dependency graph.

    Parameters
    ----------
    G
        Version dependency graph.
    """
    plt = importlib.import_module("matplotlib.pyplot")

    if layout == "spring":
        pos = nx.spring_layout(G)
    elif layout == "planar":
        pos = nx.planar_layout(G)
    elif layout == "shell":
        pos = nx.shell_layout(G)
    elif layout == "circular":
        pos = nx.circular_layout(G)
    elif layout == "spectral":
        pos = nx.spectral_layout(G)
    elif layout == "kamada_kawai":
        pos = nx.kamada_kawai_layout(G)
    else:
        pos = nx.spring_layout(G)

    nx.draw(G, pos, with_labels=True, node_color="skyblue")

    if upgrade_action_versions is not None:
        nx.draw_networkx_nodes(G, pos, nodelist=upgrade_action_versions, node_color="orange")

    if current_version is not None:
        nx.draw_networkx_nodes(G, pos, nodelist=[current_version], node_color="green")

    plt.title("Version Dependency Graph")
    plt.show()


def validate_upgrade_actions(upgrade_actions: dict) -> bool:
    """Return a dictionary of upgradable versions and their actions.
    
    Parameters
    ----------
    upgrade_actions
        Dictionary of upgrade actions.
    
    Returns
    -------
    dict
        Dictionary of upgradable versions and their actions.
    """
    for version in upgrade_actions:

        actions = upgrade_actions[version]

        if not isinstance(actions, list):
            raise ValueError(f"Upgrade actions for version {version} are not defined as list.")
        
        if len(actions) == 0:
            raise ValueError(f"Upgrade actions are not defined for version {version}.")
        
        for action in actions:
            if not isinstance(action, str) and not isinstance(action, list):
                raise ValueError(f"Upgrade action is not defined as string or list.")
            else:
                if isinstance(action, list) and len(action) > 0:
                    if not isinstance(action[0], str):
                        raise ValueError(f"Upgrade action name is not defined as string.")
                    if len(action) >= 1 and not isinstance(action[1], dict):
                        raise ValueError(f"Upgrade action parameters are not defined as dictionary.")

    return True


def validate_version(version: str, upgrade_actions: dict, current_db_version: str) -> dict:
    """Validate that the version is upgradable.
    
    Parameters
    ----------
    version
        Version to be upgraded.
    upgrade_actions
        Dictionary of upgrade actions.
    current_db_version
        Current database version.
    
    Returns
    -------
    dict
        Dictionary of upgradable version and their actions
    """
    valid_upgradable_version = list(upgrade_actions.keys())[0]
    if version != valid_upgradable_version:
        raise ValueError(f"Version {version} is not the next upgrade. Current database version is {current_db_version}. Use version {valid_upgradable_version} instead.")
    return {version: upgrade_actions[version]}
