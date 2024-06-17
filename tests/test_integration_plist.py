import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection, Cursor
from unittest.mock import ANY, MagicMock, patch

import pytest
from launchd_me.plist import (
    LaunchdMeInit,
    PlistCreator,
    PListDbConnectionManager,
    ScheduleType,
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
def temp_env(tmp_path) -> ConfiguredEnvironmentObjects:
    """Provide a configured environment for testing.

    Doubles as an integration test for `UserConfig` and `LaunchdMeInit`.

    Creates a temporary environment with application directories and a db file using a
    Pytest `tmp_path` as the user's home dir. Overwrites the loaded `user_name` with
    `mock.user` for consistency.

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
    user_config.user_name = "mockuser"
    ldm_init = LaunchdMeInit(user_config)
    ldm_init.initialise_launchd_me()
    temp_env = ConfiguredEnvironmentObjects(temp_user_dir, user_config, ldm_init)
    return temp_env


class TestTheTempEnvTestEnvironment:
    """Validate all aspects of the test environment.

    Doubles as a validation of the integration test of `UserConfig` and `LaunchdMeInit`
    represented by `test env`.

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
        """Test the temp env has the configured user name."""
        assert self.temp_env.user_config.user_name == "mockuser"

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


class TestPlistCreatorGeneratePlist:
    """Create, validate and install an interval plist. Update the database.

    Creates `mock_script` that the plist will automate. Makes a `LaunchAgents` dir
    in the temp user_environment to install the plist file symlink into. I
    nstantiates a PlistCreator with the details for `mock_script` and with
    `make_exectuable` and `auto_install` set to true.

    The PlistCreator's driver function is called. The call patches
    # a PlistInstallationManager's `run_command_line_tool` method so no command line
    # calls are made. This means the plist output isn't validated with `plutil` so
    # `plutil` validation is added as an assertion when run on macOS.

    # The test asserts the plist file is created with spot checks of selected content.
    # When run on macOS the test asserts the plist file is valid.

    # The test asserts that a symlink to the plist was created in the mock
    # `LaunchAgents` dir.

    # It assets `_run_command_line_tool` was called with the plist installation
    # commands. And it asserts that the database now contains details of the
    # generated plist (it does not check the plist creation date).
    """

    @pytest.fixture(autouse=True)
    def run_plist_creator_driver_in_the_temp_env_environment(self, temp_env):
        # TODO: Should just be docstrings left. Again!
        """Fixture to pass the temp env to all test class methods.

        DO NOT use __init__ in test classes as it inhibits Pytests automatic setup and
        teardown.
        """
        self.temp_env = temp_env
        self.mock_run_command_line_tool = MagicMock()
        self.mock_script = temp_env.user_config.user_dir / "interval_task.py"
        self.mock_script.touch()
        self.temp_env.user_config.launch_agents_dir.mkdir(parents=True)

        self.plc = PlistCreator(
            self.mock_script,
            ScheduleType.interval,
            300,
            "A description",
            True,
            True,
            temp_env.user_config,
        )
        with patch(
            "launchd_me.plist.PlistInstallationManager._run_command_line_tool"
        ) as self.mock_run_command_line_tool:
            self.plist_file_path = self.plc.driver()

    def test_plist_driver_created_plist_file(self):
        """Assert a file was created."""
        assert self.plist_file_path.exists()

    def test_plist_driver_created_plist_file_with_expected_name(self):
        """Assert the created file has the expected name."""
        assert self.plist_file_path.name == "local.mockuser.interval_task_0001.plist"

    @pytest.mark.parametrize(
        "line_index, expected_line_content",
        [
            (0, '<?xml version="1.0" encoding="UTF-8"?>'),
            (5, "<string>local.mockuser.interval_task_0001.plist</string>"),
            (9, "<string>interval_task.py</string>"),
        ],
    )
    def test_plist_creator_driver_created_plist_file_with_expected_content(
        self, line_index, expected_line_content
    ):
        """Assert the created file has spot checks of selected content."""
        actual_plist_content = self.plist_file_path.read_text().split("\n")
        assert actual_plist_content[line_index].strip() == expected_line_content

    @pytest.mark.parametrize(
        "line_index, expected_end_string",
        [
            (12, "</string>"),
            (
                16,
                "/launchd-me/logs/local.mockuser.interval_task_0001.plist_std_out.log</string>",
            ),
            (
                18,
                "/launchd-me/logs/local.mockuser.interval_task_0001.plist_err.log</string>",
            ),
        ],
    )
    def test_plist_creator_driver_created_paths_correctly(
        self, line_index, expected_end_string
    ):
        actual_plist_content = self.plist_file_path.read_text().split("\n")
        working_dir = self.temp_env.user_config.user_dir
        assert (
            actual_plist_content[line_index].strip()
            == f"<string>{working_dir}{expected_end_string}"
        )

    @pytest.mark.skipif(sys.platform != "darwin", reason="Test runs only on macOS")
    def test_plist_creator_created_a_valid_plist_file(self):
        """Uses `plutil -lint` which tests the created plist file is valid."""
        assert subprocess.run(["plutil", "-lint", self.plist_file_path])

    def test_plist_creator_created_a_symlink_in_the_mock_launch_agents_dir(self):
        """Assert the plist file symlink is created in LaunchAgents."""
        assert (
            self.temp_env.user_config.launch_agents_dir / self.plist_file_path.name
        ).exists()
        assert (
            self.temp_env.user_config.launch_agents_dir / self.plist_file_path.name
        ).is_symlink()

    def test_plist_creator_called_the_command_to_load_the_plist_correctly(self):
        """Assert the `subprocess` command line call was made correctly."""
        self.mock_run_command_line_tool.assert_called_with("launchctl", "load", ANY)

    def test_ldm_database_contains_the_expected_plist_data(self):
        """Assert the expected values have been added to the ldm database."""
        connection = Connection(self.temp_env.user_config.ldm_db_file)
        cursor = connection.cursor()
        cursor.execute(
            "SELECT PlistFileID, PlistFileName, ScriptName, CreatedDate, "
            "ScheduleType, ScheduleValue, CurrentState FROM PlistFiles"
            " ORDER BY PlistFileID"
        )
        all_rows = cursor.fetchall()
        cursor.close()
        connection.close()
        # Exclues [4] which is the plist creation timestamp.
        assert all_rows[0][0:3] == (
            1,
            "local.mockuser.interval_task_0001.plist",
            "interval_task.py",
        )
        assert all_rows[0][4:7] == ("interval", "300", "running")
