import subprocess
import sys
from pathlib import Path
from sqlite3 import Connection, Cursor
from unittest.mock import ANY, MagicMock, patch

import pytest
from launchd_me.plist import (
    PlistCreator,
    PListDbConnectionManager,
    ScheduleType,
)

from tests.conftest import ConfiguredEnvironmentObjects


class TestTheMockEnvironmentFixture:
    """Validate all aspects of the test environment.

    Doubles as a validation of the integration test of `UserConfig` and `LaunchdMeInit`
    represented by `test env`.

    Specifically splits out aspects of the environment outside the user directoy.
    """

    @pytest.fixture(autouse=True)
    def setup_mock_environment(self, mock_environment):
        """Fixture to pass the temp env to all test class methods.

        DO NOT use __init__ in test classes as it inhibits Pytests automatic setup and
        teardown.
        """
        self.mock_environment = mock_environment

    def test_mock_environment_username(self):
        """Test the temp env has the configured user name."""
        assert self.mock_environment.user_config.user_name == "mock_user_name"

    def test_mock_environment_paths_to_application_files_and_directories(self):
        """Test application directory and file paths are correct."""
        user_config = self.mock_environment.user_config
        temp_user_dir = self.mock_environment.temp_user_dir
        assert user_config.user_dir == temp_user_dir
        assert user_config.project_dir == temp_user_dir.joinpath(Path("launchd-me"))
        assert user_config.plist_dir == temp_user_dir.joinpath(
            Path("launchd-me/plist_files")
        )
        assert user_config.ldm_db_file == temp_user_dir.joinpath(
            Path("launchd-me/launchd-me.db")
        )

    def test_mock_environment_application_files_and_directories_are_created(self):
        """Test application directory and files are created.

        Could be combined with checking paths are correct but ensuring the test
        environment behaves as expected is worth the double check.
        """
        user_config = self.mock_environment.user_config
        assert user_config.user_dir.exists()
        assert user_config.project_dir.exists()
        assert user_config.plist_dir.exists()
        assert user_config.ldm_db_file.exists()

    def test_mock_environment_paths_to_system_directory_directories(self):
        """Test required system directory paths are correct."""
        user_config = self.mock_environment.user_config
        temp_user_dir = self.mock_environment.tmp_dir
        assert user_config.launch_agents_dir == temp_user_dir.joinpath(
            "Library/LaunchAgents"
        )

    def test_mock_environment_paths_to_system_directory_directories(self):
        """Test required system directory paths exist as expected."""
        user_config = self.mock_environment.user_config
        temp_user_dir = self.mock_environment.temp_user_dir
        assert user_config.launch_agents_dir == temp_user_dir.joinpath(
            "Library/LaunchAgents"
        )

    def test_mock_environment_paths_to_package_data_files(self):
        """Test non Python files exist."""
        template_file = self.mock_environment.user_config.plist_template_path
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

    def test_mock_environment_data_files_are_accessible(self):
        """Test non Python files are correctly created and therefore readable."""
        template_file = self.mock_environment.user_config.plist_template_path
        with open(template_file, "r") as file_handle:
            content = file_handle.readlines()
        assert content[3] == "<dict>\n"

    def test_mock_environment_database_created_by_launchd_me_init(self):
        ldm_database = self.mock_environment.user_config.ldm_db_file
        assert ldm_database.exists()

    def test_plist_db_connection_manager_created_and_of_the_correct_type(self):
        """Test the PlistDBConnection Manager.

        Checks the ldm_db_file is valid and can be connected to, that the Connection
        and Cursor objects are created and of the correct type.
        """
        user_config = self.mock_environment.user_config
        with PListDbConnectionManager(user_config) as cursor:
            connection = cursor.connection
        assert isinstance(connection, Connection)
        assert isinstance(cursor, Cursor)


class TestPlistCreatorGeneratePlist:
    """Create, validate and install an interval plist. Update the database.

    This tests all the methods called by the `PlistCreator.driver` when passed an
    `interval` schedule. An entire version of the package environment is spun up with
    `temp_env`.

    The fixture `run_plist_creator_driver_in_the_temp_env_environment` generates the
    outcome of running `PlistCreator.driver` and its outputs are passed to every
    test in the class with `autouse`.
    """

    @pytest.fixture(autouse=True)
    def run_plist_creator_driver_in_the_mock_environment(
        self, mock_environment: ConfiguredEnvironmentObjects
    ):
        """Runs `PlistCreator.driver` and all class tests then `autouse` the results.

        Creates `mock_script` that the plist will automate. Makes a `LaunchAgents` dir
        in the temp user_environment to install the plist file symlink into.
        Instantiates a PlistCreator with the details for `mock_script` and with
        `make_exectuable` and `auto_install` set to true.

        The PlistCreator's driver function is called. The call patches
        a PlistInstallationManager's `run_command_line_tool` method so no command line
        calls are made. This means the plist output isn't validated with `plutil` -
        a stand-alone tests calls `plutil -lint` validation (on macOS only).

        DO NOT use __init__ in test classes as it inhibits Pytests automatic setup and
        teardown.
        """
        self.temp_env: ConfiguredEnvironmentObjects = mock_environment
        self.mock_run_command_line_tool: MagicMock = MagicMock()
        self.mock_script: Path = (
            mock_environment.user_config.user_dir / "interval_task.py"
        )
        self.plc: PlistCreator = None
        self.plist_file_path: Path = None

        self.mock_script.touch()
        self.temp_env.user_config.launch_agents_dir.mkdir(parents=True)
        self.plc = PlistCreator(
            self.mock_script,
            ScheduleType.interval,
            300,
            "A description",
            True,
            True,
            mock_environment.user_config,
        )
        with patch(
            "launchd_me.plist.PlistInstallationManager._run_command_line_tool"
        ) as self.mock_run_command_line_tool:
            self.plist_file_path = self.plc.driver()

    def test_plist_driver_created_plist_file(self):
        """Assert a plist file was created."""
        assert self.plist_file_path.exists()

    def test_plist_driver_created_plist_file_with_expected_name(self):
        """Assert the created file has the expected name."""
        assert (
            self.plist_file_path.name == "local.mock_user_name.interval_task_0001.plist"
        )

    @pytest.mark.parametrize(
        "line_index, expected_line_content",
        [
            (0, '<?xml version="1.0" encoding="UTF-8"?>'),
            (5, "<string>local.mock_user_name.interval_task_0001.plist</string>"),
            (9, "<string>interval_task.py</string>"),
        ],
    )
    def test_plist_creator_driver_created_plist_file_with_expected_content(
        self, line_index, expected_line_content
    ):
        """Spot check lines in the created plist file."""
        actual_plist_content = self.plist_file_path.read_text().split("\n")
        assert actual_plist_content[line_index].strip() == expected_line_content

    @pytest.mark.parametrize(
        "line_index, expected_end_string",
        [
            (12, "</string>"),
            (
                16,
                "/launchd-me/logs/local.mock_user_name.interval_task_0001.plist_std_out.log</string>",
            ),
            (
                18,
                "/launchd-me/logs/local.mock_user_name.interval_task_0001.plist_err.log</string>",
            ),
        ],
    )
    def test_plist_creator_driver_created_paths_correctly(
        self, line_index, expected_end_string
    ):
        """Spot checks paths in the plist file constructed from `mock user dir`."""
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
        """Assert the plist file symlink is created in the mock LaunchAgents dir."""
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
            "local.mock_user_name.interval_task_0001.plist",
            "interval_task.py",
        )
        assert all_rows[0][4:7] == ("interval", "300", "running")
