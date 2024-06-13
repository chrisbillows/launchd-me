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
    EXPECTED_COLUMNS_PLIST_FILES = [
        {"name": "PlistFileID", "type": "INTEGER"},
        {"name": "PlistFileName", "type": "TEXT"},
        {"name": "ScriptName", "type": "TEXT"},
        {"name": "CreatedDate", "type": "TEXT"},
        {"name": "ScheduleType", "type": "TEXT"},
        {"name": "ScheduleValue", "type": "TEXT"},
        {"name": "CurrentState", "type": "TEXT"},
        {"name": "Description", "type": "TEXT"},
    ]

    EXPECTED_COLUMNS_INSTALLATION_EVENTS = [
        {"name": "EventID", "type": "INTEGER"},
        {"name": "FileID", "type": "INTEGER"},
        {"name": "EventType", "type": "TEXT"},
        {"name": "EventDate", "type": "TEXT"},
        {"name": "Success", "type": "INTEGER"},
    ]

    @pytest.fixture(autouse=True)
    def setup_temp_env(self, tmp_path):
        """Create a valid `user_config` with database. Auto use in all class methods.

        Manually creates the required application directories (normally handled by
        LaunchdMeInit).  Sets the `user-dir` to a Pytest `tmp_path` object.

        DO NOT use __init__ in test classes as it inhibits Pytests automatic setup and
        teardown.
        """
        self.mock = temp_env
        self.mock_user_dir = Path(tmp_path)
        self.user_config = UserConfig(self.mock_user_dir)
        self.mock_app_dir = self.mock_user_dir / "launchd-me"
        self.mock_app_dir.mkdir(parents=True, exist_ok=True)

    def test_init_creates_db_file(self):
        """Test connection manager init creates the db if it doesn't exit."""
        self.pdlcm = PListDbConnectionManager(self.user_config)
        assert Path(self.user_config.ldm_db_file).exists()

    def get_database_tables(self) -> dict:
        """Non-test function returning all tables in the current ldm_db_file database.

        Creates an independent connection. i.e. doesn't use pldbcm. Extracts all the
        table data and creates a dictionary of the results.

        Returns
        -------
        table_info: dict
            A dictionary in the format {
                <table_name> :
                    "name": <column_name>,
                    "type": <column_type>
                    }
        """
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
        return table_info

    def test_init_creates_db_tables_correctly(self):
        """Test connection manager creates the db tables correctly on init."""
        self.pdlcm = PListDbConnectionManager(self.user_config)
        table_info = self.get_database_tables()
        assert table_info["PlistFiles"] == self.EXPECTED_COLUMNS_PLIST_FILES
        assert (
            table_info["InstallationEvents"]
            == self.EXPECTED_COLUMNS_INSTALLATION_EVENTS
        )

    def test_create_db__function_creates_tables_correctly(self):
        """Test the `_create_db` function creates the db and tables correctly.

        The `PListDbConnectionManager` _init_ is coupled to running `_create_db`. In
        that configuration this test is moot. However, if that init were to be changed
        this would test the `_create_db` function directly.
        """
        self.pdlcm = PListDbConnectionManager(self.user_config)
        self.pdlcm._create_db()
        table_info = self.get_database_tables()
        assert table_info["PlistFiles"] == self.EXPECTED_COLUMNS_PLIST_FILES
        assert (
            table_info["InstallationEvents"]
            == self.EXPECTED_COLUMNS_INSTALLATION_EVENTS
        )

    def test_dunder_enter(self):
        """Test the enter method returns a Cursor object with a valid DB connection.

        Use the basic SQL command "SELECT 1" which is commonly used for testing; it
        instructs SQL to return 1.
        """
        expected = (1,)
        pldbcm = PListDbConnectionManager(self.user_config)
        cursor = pldbcm.__enter__()
        assert isinstance(cursor, Cursor)
        try:
            cursor.execute("SELECT 1")
            cursor = cursor.fetchone()
            assert cursor == expected
        finally:
            pldbcm.cursor.close()
            pldbcm.connection.close()
