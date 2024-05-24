from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection, Cursor

import pytest
from launchd_me.plist import LaunchdMeInit, PListDbConnectionManager, UserConfig


@dataclass
class TempTestEnv:
    # Create an object containing a valid, initialised launchd-me configuration.
    tmp_dir: Path
    user_config: UserConfig
    ldm: LaunchdMeInit


@pytest.fixture
def test_env(tmp_path):
    # Create a valid, initialised launchd-me configuration (application files and db
    # file) with ``tmp_dir`` as the user's home dir.
    tmp_dir = tmp_path
    user_config = UserConfig(tmp_dir)
    ldm_init = LaunchdMeInit(user_config)
    ldm_init.initialise_launchd_me()
    # A TempTestEnv object.
    temp_test_env = TempTestEnv(tmp_dir, user_config, ldm_init)
    return temp_test_env


# Uses the test env configuration.
def test_init_of_user_config_object(test_env):
    # Extract the UserConfig object with ``tmp_dir`` as the user's home dir.
    user_config = test_env.user_config
    # Extract the stand in for the user's home dir to test against.
    tmp_dir = test_env.tmp_dir
    assert user_config.user_dir == tmp_dir
    assert user_config.project_dir == tmp_dir.joinpath(Path("launchd-me"))
    assert user_config.plist_dir == tmp_dir.joinpath(Path("launchd-me/plist_files"))
    assert user_config.ldm_db_file == tmp_dir.joinpath(Path("launchd-me/launchd-me.db"))


# DELETE ME - Uses real Path.home()
def test_init_of_user_config_object_using_cb_local():
    user_config = UserConfig()
    assert str(user_config.user_dir) == "/Users/chrisbillows"
    assert str(user_config.project_dir) == "/Users/chrisbillows/launchd-me"
    assert str(user_config.plist_dir) == "/Users/chrisbillows/launchd-me/plist_files"
    assert (
        str(user_config.ldm_db_file) == "/Users/chrisbillows/launchd-me/launchd-me.db"
    )


def test_launchd_me_init(test_env):
    # Extracts the path to ldm_db_file from test_env's UserConfig object.
    ldm_db_file = test_env.user_config.ldm_db_file
    # Asserts that the ldm_db_file was created in the ``test_env`` fixture.
    assert ldm_db_file.exists()


def test_plist_db_connection_manager(test_env):
    user_config = test_env.user_config
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
