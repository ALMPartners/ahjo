import pytest
import copy
import networkx as nx
from ahjo.operations.general.upgrade import AhjoUpgrade


NON_UPGRADABLE_VERSIONS = ["v3.0.3", "v3.1.0", "v3.1.1", "v3.1.2"]
CURRENT_VERSION = "v3.1.2"
UPGRADABLE_VERSIONS = ["v3.1.3", "v3.1.4", "v3.1.5"]
UPGRADE_ACTIONS = {}

for version in NON_UPGRADABLE_VERSIONS:
    UPGRADE_ACTIONS[version] = ["test-action"]

UPGRADE_ACTIONS[CURRENT_VERSION] = ["test-action"]

for version in UPGRADABLE_VERSIONS:
    UPGRADE_ACTIONS[version] = ["test-action"]

class TestAhjoUpgrade():

    @pytest.fixture(scope='function', autouse=True)
    def ahjo_upgrade_setup(self, mssql_sample, ahjo_context):
        self.ahjo_upgrade = AhjoUpgrade(
            config_filename = mssql_sample,
            context = ahjo_context(mssql_sample),
            version = None
        )
        yield

    def test_get_next_version_upgrade_with_valid_input(self):
        next_version = self.ahjo_upgrade.get_next_version_upgrade(
            next_upgrades_in_config = ["b"],
            current_db_version = "a",
            next_git_version_upgrades = ["b", "c", "d"]
        )
        assert next_version == "b"

    def test_get_next_version_upgrade_without_next_upgrade_in_config(self):
        with pytest.raises(ValueError, match=r'The current database version \(a\) has no upgradable version in the upgrade actions. The next upgradable version is: b'):
            self.ahjo_upgrade.get_next_version_upgrade(
                next_upgrades_in_config = [],
                current_db_version = "a",
                next_git_version_upgrades = ["b"]
            )

    def test_get_upgrade_version_path_with_valid_input(self):

        tag_graph = nx.DiGraph()
        tag_graph.add_edge("e", "d")
        tag_graph.add_edge("d", "c")
        tag_graph.add_edge("c", "b")
        tag_graph.add_edge("b", "a")

        upgrade_version_path = self.ahjo_upgrade.get_upgrade_version_path(
            tag_graph = tag_graph,
            config_version_graph =  tag_graph.subgraph({"a", "b", "c", "d", "e"}), 
            next_version_upgrade = "a"
        )
        assert upgrade_version_path == ["a", "b", "c", "d", "e"]

    def test_get_upgrade_version_path_with_missing_version(self):
        
        tag_graph = nx.DiGraph()
        tag_graph.add_edge("e", "d")
        tag_graph.add_edge("d", "c")
        tag_graph.add_edge("c", "b")

        with pytest.raises(ValueError, match=r"Upgrade actions are not defined for the following versions: d.\nCheck that the upgrade actions are defined correctly."):
            self.ahjo_upgrade.get_upgrade_version_path(
                tag_graph = tag_graph,
                config_version_graph =  tag_graph.subgraph({"b", "c", "e"}), 
                next_version_upgrade = "b"
            )

    def test_get_upgrade_version_path_with_multiple_heads(self):
                
        tag_graph = nx.DiGraph()
        tag_graph.add_edge("d2", "c")
        tag_graph.add_edge("d1", "c")
        tag_graph.add_edge("c", "b")
        tag_graph.add_edge("b", "a")


        with pytest.raises(ValueError, match=r"Multiple latest versions found in the upgrade actions: d2, d1. Check that the upgrade actions are defined correctly."):
            self.ahjo_upgrade.get_upgrade_version_path(
                tag_graph = tag_graph,
                config_version_graph =  tag_graph.subgraph({"a", "b", "c", "d1", "d2"}), 
                next_version_upgrade = "a"
            )

    def test_validate_version_should_return_only_given_versions_actions(self):
        version_actions = self.ahjo_upgrade.validate_version(
            "v3.1.3", 
            {"v3.1.3": ["test-action"], "v3.1.4": ["test-action"]}, 
            "v3.1.2"
        )
        assert version_actions == {"v3.1.3": ["test-action"]}

    def test_validate_version_should_raise_error_if_version_is_not_next_upgrade(self):
        with pytest.raises(ValueError, match=f"Version invalid_tag is not the next upgrade. Current database version is v3.1.2. Use version v3.1.3 instead."):
            self.ahjo_upgrade.validate_version(
                version = "invalid_tag", 
                upgrade_actions = {"v3.1.3": ["test-action"]}, 
                current_db_version = "v3.1.2"
            )

    def test_validate_upgrade_actions_with_valid_input(self):
        assert self.ahjo_upgrade.validate_upgrade_actions(upgrade_actions = UPGRADE_ACTIONS) == True

    def test_validate_upgrade_actions_with_invalid_type_int(self):
        with pytest.raises(ValueError, match="Upgrade actions for version v3.1.3 are not defined as list."):
            self.ahjo_upgrade.validate_upgrade_actions({"v3.1.3": 1})

    def test_validate_upgrade_actions_with_invalid_type_str(self):
        with pytest.raises(ValueError, match="Upgrade actions for version v3.1.3 are not defined as list."):
            self.ahjo_upgrade.validate_upgrade_actions({"v3.1.3": "invalid"})

    def test_validate_upgrade_actions_with_empty_list(self):
        with pytest.raises(ValueError, match="Upgrade actions are not defined for version v3.1.3."):
            self.ahjo_upgrade.validate_upgrade_actions({"v3.1.3": []})

    def test_validate_upgrade_action_with_invalid_type_int(self):
        with pytest.raises(ValueError, match="Upgrade action is not defined as string or list."):
            self.ahjo_upgrade.validate_upgrade_actions({"v3.1.3": [1]})

    def test_validate_upgrade_action_with_invalid_type(self):
        with pytest.raises(ValueError, match="Upgrade action name is not defined as string."):
            self.ahjo_upgrade.validate_upgrade_actions({"v3.1.3": [[1]]})

    def test_validate_upgrade_action_with_valid_input(self):
        assert self.ahjo_upgrade.validate_upgrade_actions({"v3.1.3": ["test-action"]}) == True

    def test_validate_upgrade_action_with_invalid_action_parameter_type(self):
        with pytest.raises(ValueError, match="Upgrade action parameters are not defined as dictionary."):
            self.ahjo_upgrade.validate_upgrade_actions({"v3.1.3": [["test-action", 1]]})