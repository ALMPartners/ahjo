import pytest
import copy
from ahjo.operations.general.upgrade import get_upgradable_version_actions, validate_version

NON_UPGRADABLE_VERSIONS = ["v3.0.3", "v3.1.0", "v3.1.1", "v3.1.2"]
CURRENT_VERSION = "v3.1.2"
UPGRADABLE_VERSIONS = ["v3.1.3", "v3.1.4", "v3.1.5"]
UPGRADE_ACTIONS = {}

for version in NON_UPGRADABLE_VERSIONS:
    UPGRADE_ACTIONS[version] = ["test-action"]

UPGRADE_ACTIONS[CURRENT_VERSION] = ["test-action"]

for version in UPGRADABLE_VERSIONS:
    UPGRADE_ACTIONS[version] = ["test-action"]

@pytest.mark.nopipeline
def test_old_versions_should_be_filtered_out():
    version_actions = get_upgradable_version_actions(UPGRADE_ACTIONS, CURRENT_VERSION)
    upgradable_versions = list(version_actions.keys())
    assert any(version in upgradable_versions for version in NON_UPGRADABLE_VERSIONS) == False

@pytest.mark.nopipeline
def test_only_upgradable_versions_should_be_included():
    version_actions = get_upgradable_version_actions(UPGRADE_ACTIONS, CURRENT_VERSION)
    upgradable_versions = list(version_actions.keys())
    assert all(version in upgradable_versions for version in UPGRADABLE_VERSIONS) == True

@pytest.mark.nopipeline
def test_version_not_in_repository_should_raise_error():
    with pytest.raises(ValueError, match="Current version this_tag_is_not_in_repository does not exist in the repository."):
        get_upgradable_version_actions(UPGRADE_ACTIONS, "this_tag_is_not_in_repository")

@pytest.mark.nopipeline
def test_upgrade_version_not_in_repository_should_raise_error():
    version_actions = copy.deepcopy(UPGRADE_ACTIONS)
    version_actions["this_tag_is_not_in_repository"] = ["test-action"]
    with pytest.raises(ValueError, match="Git tag this_tag_is_not_in_repository does not exist in the repository."):
        get_upgradable_version_actions(version_actions, CURRENT_VERSION)

@pytest.mark.nopipeline
def test_upgrade_versions_in_incorrect_order_should_raise_error():
    with pytest.raises(ValueError, match="Git versions in upgrade_actions are not listed in the correct order: v3.1.3 -> v3.1.2"):
        get_upgradable_version_actions(
            {
                "v3.1.3": ["test-action"],
                "v3.1.2": ["test-action"],
                "v3.1.4": ["test-action"]
            }, 
            CURRENT_VERSION
        )

@pytest.mark.nopipeline
def test_upgrade_version_with_no_actions_should_raise_error():
    with pytest.raises(ValueError, match="Upgrade actions are not defined for version v3.1.3."):
        get_upgradable_version_actions({"v3.1.3": []}, CURRENT_VERSION)

@pytest.mark.nopipeline
def test_upgrade_version_with_wrong_action_format_should_raise_error():
    with pytest.raises(ValueError, match="Upgrade actions for version v3.1.3 are not defined as list."):
        get_upgradable_version_actions({"v3.1.3": 1}, CURRENT_VERSION)

@pytest.mark.nopipeline
def test_upgrade_version_with_wrong_action_name_format_should_raise_error():
    with pytest.raises(ValueError, match="Upgrade action is not defined as string or list."):
        get_upgradable_version_actions({"v3.1.3": [1]}, CURRENT_VERSION)

@pytest.mark.nopipeline
def test_upgrade_version_with_wrong_action_name_should_raise_error():
    with pytest.raises(ValueError, match="Upgrade action name is not defined as string."):
        get_upgradable_version_actions({"v3.1.3": [[1]]}, CURRENT_VERSION)

@pytest.mark.nopipeline
def test_action_parameters_with_wrong_format_should_raise_error():
    with pytest.raises(ValueError, match="Upgrade action parameters are not defined as dictionary."):
        get_upgradable_version_actions({"v3.1.3": [["test-action", 1]]}, CURRENT_VERSION)

@pytest.mark.nopipeline
def test_action_parameters_with_correct_format():
    upgrade_actions = {"v3.1.3": [["test-action", {"test-parameter": 1}]]}
    version_actions = get_upgradable_version_actions(upgrade_actions, CURRENT_VERSION)
    assert version_actions == upgrade_actions

@pytest.mark.nopipeline
def test_actions_without_parameters():
    upgrade_actions = {"v3.1.3": ["test-action"]}
    version_actions = get_upgradable_version_actions(upgrade_actions, CURRENT_VERSION)
    assert version_actions == upgrade_actions

@pytest.mark.nopipeline
def test_upgrade_version_with_up_to_date_version_should_raise_error():
    with pytest.raises(ValueError, match="Database is already up to date."):
        get_upgradable_version_actions({"v3.1.3": ["test-action"]}, "v3.1.3")

@pytest.mark.nopipeline
def test_validate_version_should_return_only_given_versions_actions():
    version_actions = validate_version(
        "v3.1.3", 
        {"v3.1.3": ["test-action"], "v3.1.4": ["test-action"], "v3.1.5": ["test-action"]}, 
        UPGRADE_ACTIONS, 
        "v3.1.2"
    )
    assert version_actions == {"v3.1.3": ["test-action"]}

@pytest.mark.nopipeline
def test_validate_version_should_raise_error_if_version_not_in_upgrade_actions():
    with pytest.raises(ValueError, match="Version invalid_tag actions are not defined in upgrade actions config file."):
        validate_version("invalid_tag", {"v3.1.3": ["test-action"]}, UPGRADE_ACTIONS, "v3.1.2")

@pytest.mark.nopipeline
def test_validate_version_should_raise_error_if_version_is_not_next_upgrade():
    with pytest.raises(ValueError, match="Version v3.1.3 is not the next upgrade."):
        validate_version("v3.1.3", {"v3.1.5": ["test-action"]}, UPGRADE_ACTIONS, "v3.1.3")