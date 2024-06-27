from dataclasses import dataclass
from pathlib import Path

import pytest
from launchd_me.plist import (
    LaunchdMeInit,
    UserConfig,
)


@dataclass
class ConfiguredEnvironmentObjects:
    """An object for passing an initialised launchd-me configuration.

    Allows tests to access all objects used to create the test environment.

    Attributes
    ----------
    tmp_dir: Path
        Use to pass a Pytest `tmp_path` object that can stand-in for a user's root dir.
    user_config: UserConfig
        A initialised UserConfiguaration object.
    ldm_init: LaunchdMeInit
        The object used to Initialise the LaunchdMe application structure.
    """

    temp_user_dir: Path
    user_config: UserConfig
    ldm_init: LaunchdMeInit


@pytest.fixture
def mock_environment(tmp_path) -> ConfiguredEnvironmentObjects:
    """Provide a configured mock environment for testing.

    Doubles as an integration test for `UserConfig` and `LaunchdMeInit`.

    Creates a temporary environment with application directories and a db file using a
    Pytest `tmp_path` as the user's home dir. Overwrites the loaded `user_name` with
    `mock.user` for consistency.

    This can be used to allow real reading and writing to a database during testing and
    minimise the need for mocking.

    Returns
    -------
    mock_environment_configuration: ConfiguredEnvironmentObjects
        A ConfiguredEnvironmentObjects object making all aspects of the configuration
        accessible to any test.
    """
    temp_user_dir = tmp_path
    user_config = UserConfig(temp_user_dir)
    user_config.user_name = "mock_user_name"
    ldm_init = LaunchdMeInit(user_config)
    ldm_init.initialise_launchd_me()
    mock_environment_configuration = ConfiguredEnvironmentObjects(
        temp_user_dir, user_config, ldm_init
    )
    return mock_environment_configuration
