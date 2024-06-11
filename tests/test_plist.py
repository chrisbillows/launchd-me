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
        temp_user_dir = self.temp_env.tmp_dir
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
        template_dir = template_file.parent
        launchd_me_install_dir = template_dir.parent
        print("The path to the template file should be", str(template_file))
        print("The template directory exists:", template_dir.exists())
        print("The launchd_me directory exists", launchd_me_install_dir.exists())

        for item in launchd_me_install_dir.iterdir():
            print(item)

        for item in template_dir.iterdir():
            print(item)

        assert (
            template_file.exists()
        ), f"Template file does not exist at: {template_file}"

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


class TestPlistDBConnectionManager:
    @pytest.fixture(autouse=True)
    def setup_temp_env(self, tmp_path):
        """A valid user_config with app dirs created and user_dir set to a tmp_path.

        DO NOT use __init__ in test classes as it inhibits Pytests automatic setup and
        teardown.
        """
        self.mock = temp_env
        self.mock_user_dir = Path(tmp_path)
        self.user_config = UserConfig(self.mock_user_dir)
        self.mock_app_dir = self.mock_user_dir / "launchd-me"
        self.mock_app_dir.mkdir(parents=True, exist_ok=True)

    def test_init_creates_db_file(self):
        """Test connection manager creates the db if it doesn't exit."""
        pldbcm = PListDbConnectionManager(self.user_config)
        assert Path(self.user_config.ldm_db_file).exists()

    def test_init_creates_db_tables(self):
        """Test connection manager creates the db tables correctly."""
        expected_table_plist_files = [
            {"name": "PlistFileID", "type": "INTEGER"},
            {"name": "PlistFileName", "type": "TEXT"},
            {"name": "ScriptName", "type": "TEXT"},
            {"name": "CreatedDate", "type": "TEXT"},
            {"name": "ScheduleType", "type": "TEXT"},
            {"name": "ScheduleValue", "type": "TEXT"},
            {"name": "CurrentState", "type": "TEXT"},
            {"name": "Description", "type": "TEXT"},
        ]
        expected_table_installation_events = [
            {"name": "EventID", "type": "INTEGER"},
            {"name": "FileID", "type": "INTEGER"},
            {"name": "EventType", "type": "TEXT"},
            {"name": "EventDate", "type": "TEXT"},
            {"name": "Success", "type": "INTEGER"},
        ]
        pldbcm = PListDbConnectionManager(
            self.user_config
        )  # This creates the database.
        connection = Connection(self.user_config.ldm_db_file)
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_info = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            table_info[table_name] = [
                {"name": col[1], "type": col[2]} for col in columns
            ]
        cursor.close()
        connection.close()
        print(table_info)
        assert table_info["PlistFiles"] == expected_table_plist_files
        assert table_info["InstallationEvents"] == expected_table_installation_events

    def test_dunder_enter(self):
        """Tests the"""
        pass
