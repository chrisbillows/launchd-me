import getpass
from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection, Cursor

import pytest
from launchd_me.plist import LaunchdMeInit, PListDbConnectionManager, UserConfig

# class TestUserConfigInit():


#     @mark.parametrize


@dataclass
class ConfiguredEnvironmentObjects:
    """An onject for passing an initialised launchd-me configuration.

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

    tmp_dir: Path
    user_config: UserConfig
    ldm_init: LaunchdMeInit


@pytest.fixture
def temp_env(tmp_path):
    # Create a temporary environment with application directories and a db file) with
    # the Pytest tmp_path ``tmp_dir`` as the user's home dir.
    #
    # USE TO RUN THE APPLICATION AS REAL IN ALMOST ALL SCENARIOS.
    #
    tmp_dir = tmp_path
    user_config = UserConfig(tmp_dir)
    ldm_init = LaunchdMeInit(user_config)
    ldm_init.initialise_launchd_me()
    temp_test_env = ConfiguredEnvironmentObjects(tmp_dir, user_config, ldm_init)
    return temp_test_env


def test_tmp_env_username(temp_env):
    # Test the temp env has a configured user name. Name itself doesn't matter.
    assert temp_env.user_config.user_name == getpass.getuser()


def test_temp_env_paths_to_application_files_and_directories(temp_env):
    # Test the paths to the files and directories required by the application are
    # successfully created.

    # Extract the UserConfig object with ``tmp_dir`` set as the user's home dir.
    user_config = temp_env.user_config
    # Extract the stand-in for the user's home dir to test against.
    tmp_dir = temp_env.tmp_dir
    assert user_config.user_dir == tmp_dir
    assert user_config.project_dir == tmp_dir.joinpath(Path("launchd-me"))
    assert user_config.plist_dir == tmp_dir.joinpath(Path("launchd-me/plist_files"))
    assert user_config.ldm_db_file == tmp_dir.joinpath(Path("launchd-me/launchd-me.db"))


def test_temp_env_application_files_and_directories_are_created(temp_env):
    # Test that the actual files and directories are created.  Could be combined with
    # checking paths but a correctly configured test environment is vital enough to
    # warrant the double check.

    # Extract the UserConfig object with ``tmp_dir`` set as the user's home dir.
    user_config = temp_env.user_config
    assert user_config.user_dir.exists()
    assert user_config.project_dir.exists()
    assert user_config.plist_dir.exists()
    assert user_config.ldm_db_file.exists()


def test_temp_env_paths_to_system_directory_directories(temp_env):
    # Test the system directories required are available.
    user_config = temp_env.user_config
    # Extract the stand-in for the user's home dir to test against.
    tmp_dir = temp_env.tmp_dir
    assert user_config.launch_agents_dir == tmp_dir.joinpath("Library/LaunchAgents")


def test_temp_env_paths_to_package_directories(temp_env):
    pass
    # assert temp_env.user_config.plist_template_path == 1


def test_launchd_me_init(temp_env):
    # Extracts the path to ldm_db_file from test_env's UserConfig object.
    ldm_db_file = temp_env.user_config.ldm_db_file
    # Asserts that the ldm_db_file was created in the ``test_env`` fixture.
    assert ldm_db_file.exists()


def test_plist_db_connection_manager(temp_env):
    user_config = temp_env.user_config
    with PListDbConnectionManager(user_config) as cursor:
        connection = cursor.connection
    # Asserts that the ldm_db_file is valid/can be connected to and that a connection
    # and cursor are created and are the correct type.
    assert isinstance(connection, Connection)
    assert isinstance(cursor, Cursor)


# @pytest.fixture
# def plist_creator():
#     plc = PlistCreator()
#     return plc

# def test_plist_creator_init():
#     plc = PlistCreator("pretend.py", "interval", 300)
#     assert plc.script_name == "pretend.py"
#     assert plc.schedule == 1
#     assert plc.template_path == "?"
