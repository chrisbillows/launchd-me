import getpass
from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection, Cursor

import pytest
from launchd_me.plist import LaunchdMeInit, PListDbConnectionManager, UserConfig


class TestAllProjectObjectsInitialiseAsExpected:
    """Basic tests that ensure all objects initialise as future tests expect.

    Newly added classes should be added here.
    """

    def test_user_config_initialises_with_correct_attributes(self):
        """Initialise UserConfig object correctly.

        Checks all expected attributes are present and there are no unexpected
        attributes.
        """
        expected_attributes = {
            "user_name",
            "user_dir",
            "project_dir",
            "plist_dir",
            "ldm_db_file",
            "plist_template_path",
            "launch_agents_dir",
        }
        user_config = UserConfig()
        actual_attributes = set(user_config.__dict__.keys())
        assert expected_attributes == actual_attributes

    def test_launchd_me_init_initialises_with_correct_attributes(self):
        """Initialise LaunchdMeInit object correctly.

        Checks all expected attributes are present and there are no unexpected attributes.
        """
        user_config = UserConfig()
        ldm_init = LaunchdMeInit(user_config)
        assert isinstance(ldm_init._user_config, UserConfig)


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
def temp_env(tmp_path) -> ConfiguredEnvironmentObjects:
    """A fixture provided a configured environment for use in tests.

    Create a temporary environment with application directories and a db file using a
    Pytest tmp_path as the user's home dir.

    This can be used to allow real reading and writing to a database during testing and
    minimise the need for mocking.

    Returns
    -------
    temp_test_env: ConfiguredEnvironmentObjects
        A ConfiguredEnvironmentObjects object making all aspects of the configuration
        accessible to any test.
    """
    temp_user_dir = tmp_path
    user_config = UserConfig(temp_user_dir)
    ldm_init = LaunchdMeInit(user_config)
    ldm_init.initialise_launchd_me()
    temp_env = ConfiguredEnvironmentObjects(temp_user_dir, user_config, ldm_init)
    return temp_env


class TestTheTempEnvTestEnvironment:
    """Validate all aspects of the test environment.

    Specifically splits out aspects of the environment outside the user directoy.
    """

    @pytest.fixture(autouse=True)
    def setup_temp_env(self, temp_env):
        """Fixture to pass the temp env to all test class methods.

        DO NOT use __init__ in test classes as it inhibits Pytests automatic setup and
        teardown.
        """
        self.temp_env = temp_env

    def test_tmp_env_username(self):
        """Test the temp env has a configured user name. Name itself doesn't matter.

        Primarily to see if test machines e.g. GitHub actions VM, docker builds can be
        relied upon to have this set.
        """
        assert self.temp_env.user_config.user_name == getpass.getuser()

    def test_temp_env_paths_to_application_files_and_directories(self):
        """Test application directory and file paths are correct."""
        user_config = self.temp_env.user_config
        temp_user_dir = self.temp_env.temp_user_dir
        assert user_config.user_dir == temp_user_dir
        assert user_config.project_dir == temp_user_dir.joinpath(Path("launchd-me"))
        assert user_config.plist_dir == temp_user_dir.joinpath(
            Path("launchd-me/plist_files")
        )
        assert user_config.ldm_db_file == temp_user_dir.joinpath(
            Path("launchd-me/launchd-me.db")
        )

    def test_temp_env_application_files_and_directories_are_created(self):
        """Test application directory and files are created.

        Could be combined with checking paths are correct but ensuring the test
        environment behaves as expected is worth the double check.
        """
        user_config = self.temp_env.user_config
        assert user_config.user_dir.exists()
        assert user_config.project_dir.exists()
        assert user_config.plist_dir.exists()
        assert user_config.ldm_db_file.exists()

    def test_temp_env_paths_to_system_directory_directories(self):
        """Test required system directory paths are correct."""
        user_config = self.temp_env.user_config
        temp_user_dir = temp_env.tmp_dir
        assert user_config.launch_agents_dir == temp_user_dir.joinpath(
            "Library/LaunchAgents"
        )

    def test_temp_env_paths_to_system_directory_directories(self):
        """Test required system directory paths exist as expected."""
        user_config = self.temp_env.user_config
        temp_user_dir = self.temp_env.temp_user_dir
        assert user_config.launch_agents_dir == temp_user_dir.joinpath(
            "Library/LaunchAgents"
        )

    def test_temp_env_paths_to_package_data_files(self):
        """Test non Python files exist."""
        template_file = self.temp_env.user_config.plist_template_path
        assert template_file.exists()

    def test_temp_env_data_files_are_accessible(self):
        """Test non Python files are correctly created and therefore readable."""
        template_file = self.temp_env.user_config.plist_template_path
        with open(template_file, "r") as file_handle:
            content = file_handle.readlines()
        assert content[3] == "<dict>\n"

    def test_database_created_by_launchd_me_init(self):
        ldm_database = self.temp_env.user_config.ldm_db_file
        assert ldm_database.exists()

    def test_plist_db_connection_manager_created_and_of_the_correct_type(self):
        """Test the PlistDBConnection Manager.

        Checks the ldm_db_file is valid and can be connected to, that the Connection
        and Cursor objects are created and of the correct type.
        """
        user_config = self.temp_env.user_config
        with PListDbConnectionManager(user_config) as cursor:
            connection = cursor.connection
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
