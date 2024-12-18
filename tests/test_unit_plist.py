"""Unit tests for plist classes.

A number of test classes use a `pytest.fixture` to supply test objects to every test
in the class. E.g.

```
@pytest.fixture(autouse=True)
def setup_temp_env(self, tmp_path):
```

This serves the same pass as an `__init__` method. An autouse fixture is used as it
allows Pytest to carry out automatic setup and teardown.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import rich.box
from launchd_me.exceptions import UnexpectedInstallationStatus
from launchd_me.plist import (
    DbDisplayer,
    LaunchdMeInit,
    PlistCreator,
    PListDbConnectionManager,
    PlistDbGetters,
    PlistDbSetters,
    PlistFileIDNotFound,
    PlistInstallationManager,
    ScheduleType,
    UserConfig,
)
from launchd_me.sql_statements import (
    PLISTFILES_SELECT_ALL,
    PLISTFILES_SELECT_SINGLE_PLIST_FILE,
)
from rich.table import Column, Row

from tests.conftest import (
    ConfiguredEnvironmentObjects,
    add_three_plist_file_entries_to_a_plist_files_table,
)


@pytest.fixture
def mock_user_config(tmp_path) -> UserConfig:
    """Create a valid UserConfig for testing.

    Uses a `tmp path` for the user's root directory.
    """
    mock_user_dir = tmp_path
    mock_user_config = UserConfig(mock_user_dir)
    mock_user_config.user_name = "mock_user_name"
    return mock_user_config


class TestUserConfig:
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
        {"name": "PlistFileContent", "type": "TEXT"},
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
        LaunchdMeInit). Sets the `user-dir` to a Pytest `tmp_path` object.
        """
        # self.mock = temp_env
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
        connection = sqlite3.Connection(self.user_config.ldm_db_file)
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
        assert isinstance(cursor, sqlite3.Cursor)
        try:
            cursor.execute("SELECT 1")
            cursor = cursor.fetchone()
            assert cursor == expected
        finally:
            pldbcm.cursor.close()
            pldbcm.connection.close()


class TestLaunchdMeInit:
    def test_launchd_me_init_instantiates_as_expected(self, mock_user_config):
        """Test `LaunchdMeInit()` instantiates as expected.

        Passes the expected arguments and checks the instantiated object has the
        expected attributes.
        """
        ldm_init = LaunchdMeInit(mock_user_config)
        assert isinstance(ldm_init._user_config, UserConfig)

    def test_initialise_launchd_me(self):
        """Calls multiple methods so tested in integration tests."""

    def test_create_app_directories(self, mock_user_config):
        """Checks `_create_app_directores` behaves as expected."""
        ldm = LaunchdMeInit(mock_user_config)
        ldm._create_app_directories()
        assert mock_user_config.plist_dir.exists()
        assert mock_user_config.project_dir.exists()

    def test_ensure_db_exists(self, mock_user_config):
        """Test creates database.

        Creates an empty `project_dir` and checks the method creates the database file
        when it finds it is absent.
        """
        mock_user_config.project_dir.mkdir()
        ldm = LaunchdMeInit(mock_user_config)
        ldm._ensure_db_exists()
        assert mock_user_config.ldm_db_file.exists()


class TestPlistInstallationManager:
    @pytest.fixture(autouse=True)
    def setup_temp_env(self, tmp_path):
        """Auto use objects throughout class.

        Creates a `UserConfig` with a `tmp_path` as the user directory. Creates an empty
        Mock PlistDBSetter, necessary for instantiating a PlistInsallationManager.

        Creates an empty file in the `mock_user_dir` called `mock_plist` as a stand-in
        plist file.
        """
        self.mock_user_dir = Path(tmp_path)
        self.user_config = UserConfig(self.mock_user_dir)
        self.db_setter = Mock()
        self.plim = PlistInstallationManager(self.user_config, self.db_setter)

        self.mock_plist_filename = "my_mock_plist.plist"
        self.mock_plist = self.mock_user_dir / self.mock_plist_filename
        self.mock_plist.touch()

    def test_plist_installation_manager_instantiates_as_expected(self):
        """Instantiate using expected arguments and with expected attributes."""
        assert self.plim.user_config is not None
        assert self.plim.plist_db_setters is not None

    def test_install_plist(self):
        """Uses multiple methods so tested in integration tests."""
        pass

    def test_uninstall_plist(self):
        """Uses multiple methods so tested in integration tests."""
        pass

    def test_create_symlink_in_launch_agents_dir(self):
        """Test the creation of symlink in the launch agents directory.

        `LaunchAgents` exists by default in `usr/Library/LaunchAgents`. This test
        creates that directory in `mock_user_dir`.

        The test passes `mock_plist` for symlink creation. The test
        asserts that `expected_symlink_path` has been created and is a symlink.
        """
        mock_launch_agents_dir = self.mock_user_dir / "Library" / "LaunchAgents"
        mock_launch_agents_dir.mkdir(parents=True, exist_ok=True)
        self.plim._create_symlink_in_launch_agents_dir(self.mock_plist)

        expected_symlink_path = mock_launch_agents_dir / self.mock_plist_filename

        assert expected_symlink_path.exists()
        assert expected_symlink_path.is_symlink()

    @patch("subprocess.run")
    def test_run_command_line_tool_success(self, mock_run):
        """Assert `run command line tool` calls subprocess with expected commands.

        Patches `subprocess.run` with `mock_run` and gives it a valid return value
        with the MagicMock `mock_result`.
        """
        mock_result = MagicMock()
        mock_result.stdout = "success message"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        tool = "some_tool"
        command = "some_command"
        symlink_to_plist = "/some_path"
        self.plim._run_command_line_tool(tool, command, symlink_to_plist)
        mock_run.assert_called_once_with(
            [tool, command, str(symlink_to_plist)],
            check=True,
            capture_output=True,
            text=True,
        )

    def test_run_command_line_tool_returns_error(self):
        """Assert an generic non-zero CLI call raises an error."""
        with pytest.raises(subprocess.CalledProcessError):
            self.plim._run_command_line_tool("grep", "hello", self.mock_plist)


@pytest.fixture
def plc_interval(mock_user_config) -> PlistCreator:
    mock_script = Path("interval_task.py")
    plc = PlistCreator(
        mock_script,
        ScheduleType.interval,
        300,
        "A description",
        True,
        True,
        mock_user_config,
    )
    return plc


@pytest.fixture
def plc_calendar(mock_user_config) -> PlistCreator:
    mock_script = Path("calendar_task.py")
    plc = PlistCreator(
        mock_script,
        ScheduleType.calendar,
        {"Day": 15, "Hour": 15},
        "A description",
        True,
        True,
        mock_user_config,
    )
    return plc


class TestPlistCreator:
    def test_plist_creator_initialisation_with_interval_schedule(self, plc_interval):
        assert plc_interval.path_to_script_to_automate == Path("interval_task.py")
        assert plc_interval.schedule_type == ScheduleType.interval
        assert plc_interval.schedule == 300
        assert plc_interval.description == "A description"
        assert plc_interval.make_executable is True
        assert plc_interval.auto_install is True

    def test_plist_creator_initialisation_with_calendar_schedule(self, plc_calendar):
        assert plc_calendar.path_to_script_to_automate == Path("calendar_task.py")
        assert plc_calendar.schedule_type == ScheduleType.calendar
        assert plc_calendar.schedule == {"Day": 15, "Hour": 15}
        assert plc_calendar.description == "A description"
        assert plc_calendar.make_executable is True
        assert plc_calendar.auto_install is True

    def test_generate_file_name(self, plc_interval):
        """Test file name generation.

        Attributes
        ----------
        plc_interval: PlistCreator
            A fixture providing an instantiated PlistCreator instance. The instance
            uses a fixture providing a UserConfig instance where the `user_dir` is
            a tmp_path and the attribute user_name has been manually overwritten as
            `mock_user_name`
        """
        ldm_init = LaunchdMeInit(plc_interval.user_config)
        ldm_init.initialise_launchd_me()
        actual = plc_interval._generate_file_name()
        expected = "local.mock_user_name.interval_task_0001.plist"
        assert actual == expected

    def test_write_file_and_make_script_executable(self, plc_interval, tmp_path):
        """Test writing mock content to a mock file.

        Creates an empty mock file, writes content to it then makes it an executable.
        """
        mock_file = tmp_path / "mock_file"
        mock_content = "123\n456\n789"
        plc_interval._write_file(mock_file, mock_content)
        plc_interval.path_to_script_to_automate = mock_file
        plc_interval._make_script_executable()
        assert mock_file.exists()
        assert mock_file.read_text() == mock_content
        assert os.access(mock_file, os.X_OK)

    @pytest.mark.parametrize(
        "calendar_schedule",
        [
            {"Month": 12},
            {"Day": 31},
            {"Hour": 22},
            {"Minute": 55},
            {"Weekday": 0},
            {"Day": 15, "Hour": 15},
            {"Month": 12, "Day": 31, "Hour": 22, "Minute": 55},
        ],
    )
    def test_validate_calendar_schedule_with_valid_keys_values(
        self, plc_calendar, calendar_schedule
    ):
        expected = None
        actual = plc_calendar._validate_calendar_schedule(calendar_schedule)
        assert actual == expected

    @pytest.mark.parametrize(
        "calendar_schedule",
        [
            {"": 1},
            {"Invalid": 1},
            {"HOUR": 1},
            {"month": 1},
            {"wEEkdAy": 1},
        ],
    )
    def test_validate_calendar_schedule_with_invalid_keys(
        self, plc_calendar, calendar_schedule
    ):
        with pytest.raises(Exception):
            plc_calendar._validate_calendar_schedule(calendar_schedule)

    @pytest.mark.parametrize(
        "calendar_schedule",
        [
            {"Month": 15},
            {"Day": 0},
            {"Hour": 25},
            {"Minute": -2},
            {"Weekday": 8},
        ],
    )
    def test_validate_calendar_schedule_with_invalid_values(
        self, plc_calendar, calendar_schedule
    ):
        with pytest.raises(Exception):
            plc_calendar._validate_calendar_schedule(calendar_schedule)

    def test_create_schedule_block(self, plc_interval):
        expected = "<key>StartInterval</key>\n\t<integer>300</integer>"
        actual = plc_interval._create_schedule_block()
        assert actual == expected

    def test_create_calendar_schedule_block(self, plc_calendar):
        expected = (
            "<key>StartCalendarInterval</key>"
            "\n\t<dict>"
            "\n\t\t<key>Day</key>\n\t\t<integer>15</integer>"
            "\n\t\t<key>Hour</key>\n\t\t<integer>15</integer>"
            "\n\t</dict>"
        )
        actual = plc_calendar._create_calendar_schedule_block()
        assert actual == expected

    def test_create_plist_content(self, plc_interval):
        mock_schedule_block = "<key>StartInterval</key>\n\t<integer>1000</integer>"
        content = plc_interval._create_plist_content(
            "file_to_schedule", mock_schedule_block
        )
        content_lines = content.split("\n")
        line_idx_5 = "        <string>file_to_schedule</string>"
        line_idx_9 = "                <string>interval_task.py</string>"
        line_idx_18_ends = "launchd-me/logs/file_to_schedule_err.log</string>"
        assert content_lines[5] == line_idx_5
        assert content_lines[9] == line_idx_9
        assert content_lines[18].endswith(line_idx_18_ends)
        if sys.platform == "darwin":
            plist_file = plc_interval.user_config.plist_dir / "test.plist"
            plist_file.parent.mkdir(parents=True)
            plist_file.write_text(content)
            assert subprocess.run(["plutil", "-lint", str(plist_file)])


class TestDBSetters:
    """
    Tests for DBSetters.

    The tests in this class are run using the `mock_environment` Pytest fixture which
    provides a configured, empty database and application directories in a `tmp_path`
    directory.

    """

    def test_DBSetters_init(self, mock_environment: ConfiguredEnvironmentObjects):
        """Test the object initialises as expected."""
        dbs = PlistDbSetters(mock_environment.user_config)
        assert dbs.user_config.user_name == "mock_user_name"

    def test_add_newly_created_plist_file(
        self, mock_environment: ConfiguredEnvironmentObjects
    ):
        """Test adding a Plist file record to the PlistFiles database table.

        The test calls `add_newly_created_plist_file`, with placeholder data, to add a
        plist file entry to the empty database in the mock environment.

        The test creates an independent sqlite3 connection to the database and asserts
        that the database now contains the passed placeholder data.

        The value at index 3 is `created_time` which is ignored in the assert
        statements.
        """
        dbs = PlistDbSetters(mock_environment.user_config)
        dbs.add_newly_created_plist_file(
            "a plist_filename",
            "a script_name",
            "a schedule_type",
            "a schedule_value",
            "a description",
            "plist file content",
        )
        connection = sqlite3.connect(mock_environment.user_config.ldm_db_file)
        cursor = connection.cursor()
        cursor.execute(PLISTFILES_SELECT_ALL)
        actual = cursor.fetchall()
        connection.close()
        expected = [
            (
                1,
                "a plist_filename",
                "a script_name",
                "IGNORE ME AS TIME WILL ALWAYS BE THE CURRENT TIME",
                "a schedule_type",
                "a schedule_value",
                "inactive",
                "a description",
                "plist file content",
            )
        ]
        assert actual[0][0:3] == expected[0][0:3]
        assert actual[0][4:7] == expected[0][4:7]

    def test_add_running_installation_status(
        self, mock_environment: ConfiguredEnvironmentObjects
    ):
        """Test changing a plist record's installation status to "running".

        The test calls a helper function to add synthetic plist data to the empty
        database created in the mock environment. The test retrieves the CurrentState
        column value for PlistFileID 3 and asserts it is 'inactive'.

        The test then calls the `add_running_installation_status` method on PlistFileID
        3. The test asserts that this record has been correctly changed in the
        database.

        """
        add_three_plist_file_entries_to_a_plist_files_table(
            mock_environment.user_config.ldm_db_file
        )
        connection = sqlite3.connect(mock_environment.user_config.ldm_db_file)
        cursor = connection.cursor()
        cursor.execute("SELECT CurrentState FROM PlistFiles WHERE PlistFileID=3;")
        initial_status = cursor.fetchall()
        assert initial_status == [("inactive",)]

        dbs = PlistDbSetters(mock_environment.user_config)
        dbs.add_running_installation_status(3)
        cursor.execute("SELECT CurrentState FROM PlistFiles WHERE PlistFileID=3;")
        updated_status = cursor.fetchall()
        assert updated_status == [("running",)]

    def test_add_inactive_installation_status(
        self, mock_environment: ConfiguredEnvironmentObjects
    ):
        """Test changing a plist record's installation status to "running".

        The test calls a helper function to add synthetic plist data to the empty
        database created in the mock environment. The test retrieves the CurrentState
        column value for PlistFileID 1 and asserts it is 'running'.

        The test then calls the `add_inactive_installation_status` method on PlistFileID
        1. The test asserts that this record has been correctly changed in the
        database.
        """
        add_three_plist_file_entries_to_a_plist_files_table(
            mock_environment.user_config.ldm_db_file
        )
        connection = sqlite3.connect(mock_environment.user_config.ldm_db_file)
        cursor = connection.cursor()
        cursor.execute("SELECT CurrentState FROM PlistFiles WHERE PlistFileID=1;")
        initial_status = cursor.fetchall()
        assert initial_status == [("running",)]

        dbs = PlistDbSetters(mock_environment.user_config)
        dbs.add_inactive_installation_status(3)
        cursor.execute("SELECT CurrentState FROM PlistFiles WHERE PlistFileID=3;")
        updated_status = cursor.fetchall()
        assert updated_status == [("inactive",)]


class TestDbGetters:
    """Tests for DBGetters.

    The tests in this class are provided with a PlistDbGetters instance with an empty
    database via ``self.dbg``. This is configured with the autouse fixture
    ``provide_populated_db_for_all_tests_in_class``.

    This autouse fixture instantiates a ``PlistDbGetters`` using the
    ``mock_environment`` Pytest fixture. The ``mock_environment` Pytest fixture provides
    a configured, empty database and application directories in a `tmp_path` directory.

    Tests that require a populated database individually call
    ``add_three_plist_file_entries_to_a_plist_files_table`` to add synthetic data to the
    database.
    """

    @pytest.fixture(autouse=True)
    def provide_empty_db_for_all_tests_in_class(self, mock_environment):
        """Fixture to instantiate a ``PlistDbGetters`` instance with an empty database
        and automatically pass it to all tests in the class via ``self.dbg``.
        """
        self.dbg = PlistDbGetters(mock_environment.user_config)

    def test_init(self):
        """Test ``PlistDbGetters`` initialises as expected, with an expected value."""
        assert self.dbg._user_config.user_name == "mock_user_name"

    def test_verify_a_plist_id_is_valid_does_not_raise_for_a_valid_id(self):
        """Test ``verify_a_plist_id_is_valid`` doesn't raise on a valid PlistFileID for
        a row of synthetic data.
        """
        add_three_plist_file_entries_to_a_plist_files_table(
            self.dbg._user_config.ldm_db_file
        )
        assert self.dbg.verify_a_plist_id_is_valid(1) is None

    def test_verify_a_plist_id_is_valid_raises_for_an_invalid_id(self):
        """Test ``verify_a_plist_id_is_valid`` raises for an invalid PlistFileID. The
        test looks for a PlistFileID of `4` but the database only contains three
        synthetic rows.
        """
        add_three_plist_file_entries_to_a_plist_files_table(
            self.dbg._user_config.ldm_db_file
        )
        with pytest.raises(PlistFileIDNotFound):
            assert self.dbg.verify_a_plist_id_is_valid(4) is None

    @pytest.mark.parametrize(
        "plist_id, expected_installation_status",
        [(1, "running"), (2, "running"), (3, "inactive")],
    )
    def test_verify_a_plist_id_installation_doesnt_raise_for_an_expected_status(
        self, plist_id, expected_installation_status
    ):
        """Test the method doesn't raise an error for an expected installation status."""
        add_three_plist_file_entries_to_a_plist_files_table(
            self.dbg._user_config.ldm_db_file
        )
        actual = self.dbg.verify_a_plist_id_installation_status(
            plist_id, expected_installation_status
        )
        assert actual is None

    @pytest.mark.parametrize(
        "plist_id, expected_installation_status",
        [(1, "inactive"), (2, "inactive"), (3, "running")],
    )
    def test_verify_a_plist_id_installation_raises_for_an_unexpected_status(
        self, plist_id, expected_installation_status
    ):
        """Test the method raises for an unexpected installation status."""
        add_three_plist_file_entries_to_a_plist_files_table(
            self.dbg._user_config.ldm_db_file
        )
        with pytest.raises(UnexpectedInstallationStatus):
            self.dbg.verify_a_plist_id_installation_status(
                plist_id, expected_installation_status
            )

    def test_get_all_tracked_plist_files_for_three_rows_of_data(self):
        """Test `get_all_tracked_plist_files` works correctly with three synthetic rows
        of data.
        """
        add_three_plist_file_entries_to_a_plist_files_table(
            self.dbg._user_config.ldm_db_file
        )
        expected = [
            (
                1,
                "mock_plist_1",
                "script_1",
                "2024-03-28T08:30:00Z",
                "interval",
                "300",
                "running",
            ),
            (
                2,
                "mock_plist_2",
                "script_2",
                "2024-04-28T09:30:00Z",
                "calendar",
                "{Hour: 15}",
                "running",
            ),
            (
                3,
                "mock_plist_3",
                "script_3",
                "2024-04-28T09:30:00Z",
                "interval",
                "1000",
                "inactive",
            ),
        ]
        actual = self.dbg.get_all_tracked_plist_files()
        assert actual == expected

    def test_get_all_tracked_plist_files_return_type_is_a_list(self):
        """Assert the return type of ``get_all_tracked_plist_files`` is a list."""
        add_three_plist_file_entries_to_a_plist_files_table(
            self.dbg._user_config.ldm_db_file
        )
        actual = self.dbg.get_all_tracked_plist_files()
        assert isinstance(actual, list)

    def test_get_all_tracked_plist_files_returns_a_list_of_tuples(self):
        """Assert ``get_all_tracked_plist_files`` returns a list of tuples."""
        add_three_plist_file_entries_to_a_plist_files_table(
            self.dbg._user_config.ldm_db_file
        )
        actual = self.dbg.get_all_tracked_plist_files()
        assert all(isinstance(item, tuple) for item in actual)

    def test_get_all_tracked_plist_files_on_an_empty_database(self):
        """Assert ``get_all_tracked_plist_files`` returns an empty list for an empty
        database. This test uses the mock environment fixture which has a valid, empty
        db.
        """
        actual = self.dbg.get_all_tracked_plist_files()
        expected = []
        assert actual == expected

    def test_get_all_tracked_plist_files_if_the_db_doesnt_exist(self):
        """Test ``get_all_tracked_plist_files`` if the database doesn't exist (a user
        could delete the db manually, for example).

        The test uses Path.unlink() to delete the file, then attempts to collect data -
        which creates a new empty database from which the method returns no data.
        """
        self.dbg._user_config.ldm_db_file.unlink()
        actual = self.dbg.get_all_tracked_plist_files()
        expected = []
        assert actual == expected

    def test_get_a_single_plist_file_details_for_a_valid_plist_file_id(self):
        """Test ``get_a_single_plist_file`` works for a valid ID from three synthetic
        rows of data.
        """
        add_three_plist_file_entries_to_a_plist_files_table(
            self.dbg._user_config.ldm_db_file
        )
        actual = self.dbg.get_a_single_plist_file_details(1)
        expected = {
            "PlistFileID": 1,
            "PlistFileName": "mock_plist_1",
            "ScriptName": "script_1",
            "CreatedDate": "2024-03-28T08:30:00Z",
            "ScheduleType": "interval",
            "ScheduleValue": "300",
            "CurrentState": "running",
            "Description": "Mock plist file number 1",
            "PlistFileContent": "<plist>\n<dict>\n<string>placeholder_content</string>\n</dict>\n</plist>",
        }
        assert actual == expected

    def test_get_a_single_plist_file_details_returns_a_dictionary(
        self,
    ):
        """Test ``get_a_single_plist_file`` for valid ID returns a dictionary."""
        add_three_plist_file_entries_to_a_plist_files_table(
            self.dbg._user_config.ldm_db_file
        )
        actual = self.dbg.get_a_single_plist_file_details(1)
        assert isinstance(actual, dict)

    def test_get_a_single_plist_file_details_for_an_invalid_plist_file_id(self):
        """Test `get_a_single_plist_file` for a plist id not in the database.

        `get_a_single_plist_file` calls `verify_a_plist_id_is_valid` which will raise
        an error if the plist is not in the database.
        """
        with pytest.raises(PlistFileIDNotFound):
            self.dbg.get_a_single_plist_file_details(1)


class TestDbDisplayer:
    """Test class general methods. Specific outputs (e.g. tables) are tested extensively
    under their own test classes."""

    @pytest.mark.parametrize(
        "iso_date_string, expected",
        [
            ("2024-07-15T12:34:56+09:00", "2024-07-15"),
            ("2024-06-21T08:22:31-04:00", "2024-06-21"),
            ("2024-09-10T17:45:12+01:00", "2024-09-10"),
            ("2024-09-10T17:45:12Z", "2024-09-10"),
        ],
    )
    def test_format_date_with_various_iso_formats(
        self, iso_date_string, expected, mock_environment
    ):
        """Test ``_format_date`` on a random selection of ISO formatted datetime
        strings. ``_format_date`` expects valid ISO formatted strings.

        Tests against a Z formatted datetime string. These are not natively supported by
        ``datetime.fromisoformat`` before Python 3.11. The ``_format_date`` method
        reformats Z formatted datetime strings.
        """
        db_displayer = DbDisplayer(mock_environment.user_config)
        actual = db_displayer._format_date(iso_date_string)
        assert actual == expected

    @pytest.mark.parametrize(
        "xml_formatted_string, expected",
        [
            (
                '<?xml version="1.0" encoding="UTF-8"?>',
                '[grey69]<?xml version="1.0" encoding="UTF-8"?>[/grey69]',
            ),
            (
                "<key>ProgramArguments</key>",
                "[grey69]<key>[/grey69]ProgramArguments[grey69]</key>[/grey69]",
            ),
            ("<dict>", "[grey69]<dict>[/grey69]"),
            ("</plist>", "[grey69]</plist>[/grey69]"),
        ],
    )
    def test_style_xml_tags_with_various_xml_strings(
        self, xml_formatted_string, expected, mock_environment
    ):
        """Test ``_style_xml_tags`` adds ``rich`` renderable formatting to any opening
        or closing XML tag."""
        db_displayer = DbDisplayer(mock_environment.user_config)
        actual = db_displayer._style_xml_tags(xml_formatted_string)
        assert actual == expected

    def test_table_displayer_creates_console_output(self, mock_environment):
        """Test ``_table_displayer`` which passes the table to console output.

        The test asserts that a console was created and that print was called on the
        Console object with the expected values.
        """
        with patch("launchd_me.plist.Console") as MockConsole:
            mock_console = MockConsole.return_value
            dba = DbDisplayer(mock_environment.user_config)
            dba._table_displayer("a_table_object")
            MockConsole.assert_called_once()
            mock_console.print.assert_called_once_with("\n", "a_table_object")


class TestDbDisplayerSinglePlistFileDetailTable:
    @pytest.fixture(autouse=True)
    def setup_for_all_tests_in_class(self, mock_environment):
        """Create a ``DbDisplayer`` instance and a formatted Table for all tests.

        They are accessible in all tests in the class via ``self.db_displayer`` and
        ``self.actual_single_plist_table``.

        This fixture uses ``mock_environment`` to create an empty database and populates
        it with three rows of synthetic data using
        ``add_three_plist_file_entries_to_a_plist_files_table``.

        A connection is manually created to retrieve ``target_row``, which is then
        formatted as the method under test expects. The SQLite command is the same used
        by the ``DbGetter`` method that normally supplies the data.
        """
        add_three_plist_file_entries_to_a_plist_files_table(
            mock_environment.user_config.ldm_db_file
        )
        connection = sqlite3.connect(mock_environment.user_config.ldm_db_file)
        cursor = connection.cursor()
        cursor.execute(PLISTFILES_SELECT_SINGLE_PLIST_FILE, ("1",))
        target_row = cursor.fetchall()
        description = [description[0] for description in cursor.description]
        plist_detail = dict(zip(description, target_row[0]))
        self.db_displayer = DbDisplayer(mock_environment.user_config)
        self.actual_single_plist_table = (
            self.db_displayer._create_single_plist_file_detail_table(plist_detail)
        )

    def test_init_initializes_db_displayer_correctly(self):
        """Sense check to ensure a DbDisplayer initialises as expected."""
        assert self.db_displayer._user_config.user_name == "mock_user_name"

    def test_create_single_plist_file_detail_table_basic_attributes_early_warning(self):
        """A quick early warning that an attribute has been changed. This is not
        exhaustive.
        """
        nuns = [
            "title",
            "caption",
            "width",
            "min_width",
            "safe_box",
            "border_style",
            "title_style",
            "caption_style",
        ]
        none = ["style"]
        trues = ["pad_edge", "show_header"]
        falses = [
            "_expand",
            "show_footer",
            "show_lines",
            "collapse_padding",
            "highlight",
        ]
        centers = ["title_justify", "caption_justify"]
        for key, actual_value in self.actual_single_plist_table.__dict__.items():
            if key in nuns:
                expected = None
            elif key in none:
                expected = "none"
            elif key in trues:
                expected = True
            elif key in falses:
                expected = False
            elif key in centers:
                expected = "center"
            else:
                continue
            assert actual_value == expected

    def test_create_single_plist_file_detail_table_has_correct_row_count(self):
        """Test the expected number of rows in the table"""
        assert self.actual_single_plist_table.row_count == 11

    def test_create_single_plist_file_detail_table_has_correct_rows(self):
        """Test the row object attributes. Only one row has different styling."""
        magenta_row = Row(style="magenta", end_section=False)
        expected_rows = [Row(style=None, end_section=False) for num in range(11)]
        expected_rows[2] = magenta_row
        assert self.actual_single_plist_table.rows == expected_rows

    def create_expected_columns_for_single_plist_file_detail_table(self):
        """Helper function to create expected columns."""
        cells_column_1 = [
            "PlistFileID",
            "PlistFileName",
            "ScriptName",
            "CreatedDate",
            "ScheduleType",
            "ScheduleValue",
            "CurrentState",
            "Description",
            "________________",
            "",
            "PlistFileContent",
        ]
        cells_column_2 = [
            "1",
            "mock_plist_1",
            "script_1",
            "2024-03-28",
            "interval",
            "300",
            "running",
            "Mock plist file number 1",
            "________________",
            "",
            "[grey69]<plist>[/grey69]\n[grey69]<dict>[/grey69]\n[grey69]<string>[/grey69]placeholder_content[grey69]</string>[/grey69]\n[grey69]</dict>[/grey69]\n[grey69]</plist>[/grey69]",
        ]
        column_1 = Column(
            header="Plist File",
            footer="",
            header_style="",
            footer_style="",
            style="",
            justify="left",
            vertical="top",
            overflow="ellipsis",
            width=None,
            min_width=None,
            max_width=None,
            ratio=None,
            no_wrap=False,
            _index=0,
            _cells=cells_column_1,
        )
        column_2 = Column(
            header="Details",
            footer="",
            header_style="",
            footer_style="",
            style="",
            justify="left",
            vertical="top",
            overflow="ellipsis",
            width=None,
            min_width=None,
            max_width=None,
            ratio=None,
            no_wrap=False,
            _index=1,
            _cells=cells_column_2,
        )
        return [column_1, column_2]

    def test_create_single_plist_file_detail_table_has_correct_columns(self):
        """Test columns attribute in its entirety as this is the vital output of the
        method.
        """
        expected = self.create_expected_columns_for_single_plist_file_detail_table()
        assert self.actual_single_plist_table.columns == expected


class TestDbDisplayerAllTrackedPlistFilesTable:
    @pytest.fixture(autouse=True)
    def setup_for_all_tests_in_class(self, mock_environment):
        """Create a ``DbDisplayer`` instance and a formatted Table for all tests.

        They are accessible in all tests in the class via ``self.db_displayer`` and
        ``self.actual_single_plist_table``.

        This fixture uses ``mock_environment`` to create an empty database and populates
        it with three rows of synthetic data using
        ``add_three_plist_file_entries_to_a_plist_files_table``.

        A connection is manually created to retrieve all the data as ``all_rows``.
        The SQLite command is the same used by the ``DbGetter`` method that normally
        supplies the data.
        """
        add_three_plist_file_entries_to_a_plist_files_table(
            mock_environment.user_config.ldm_db_file
        )
        connection = sqlite3.connect(mock_environment.user_config.ldm_db_file)
        cursor = connection.cursor()
        cursor.execute(PLISTFILES_SELECT_ALL)
        all_rows = cursor.fetchall()
        self.db_displayer = DbDisplayer(mock_environment.user_config)
        self.actual_all_tracked_table = (
            self.db_displayer._create_all_tracked_plist_files_table(all_rows)
        )

    def test_init_initializes_db_displayer_correctly(self):
        """Sense check to ensure a DbDisplayer initialises as expected."""
        assert self.db_displayer._user_config.user_name == "mock_user_name"

    @pytest.mark.parametrize(
        "attribute, expected_value",
        [
            ("box", rich.box.SIMPLE),
            ("title", "  USER `mock_user_name` PERSONAL PLIST FILES"),
            ("title_justify", "left"),
            ("title_style", "blue3 bold italic"),
            ("caption", "Run `ldm list <ID>` for full plist file details."),
            ("row_count", 3),
            ("rows", [Row(style=None, end_section=False) for num in range(3)]),
        ],
    )
    def test_create_all_tracked_plist_files_table_has_expected_attributes(
        self, attribute, expected_value
    ):
        """Assert that a Table has the expected attributes (excluding columns)."""
        assert getattr(self.actual_all_tracked_table, attribute) == expected_value

    def test_create_all_tracked_plist_files_table_first_column_attributes(self):
        """Assert that a Table object has the expected column styling and attributes.
        Each column is a Column objected and is tested individually in full.

        Tests the styling and contents of the first column.
        """
        expected_first_column = Column(
            header="File\nID",
            footer="",
            header_style="",
            footer_style="",
            style="",
            justify="center",
            vertical="top",
            overflow="wrap",
            width=None,
            min_width=None,
            max_width=None,
            ratio=None,
            no_wrap=False,
            _index=0,
            _cells=["1", "2", "3"],
        )
        actual_first_column = self.actual_all_tracked_table.columns[0]
        assert actual_first_column == expected_first_column

    def test_create_all_tracked_plist_files_table_second_column_attributes(self):
        """Test the styling and contents of the second column."""
        expected_column = Column(
            header="Plist Filename",
            justify="left",
            vertical="top",
            overflow="fold",
            width=None,
            min_width=None,
            max_width=None,
            ratio=None,
            no_wrap=True,
            _index=1,
            _cells=["mock_plist_1", "mock_plist_2", "mock_plist_3"],
        )
        actual_first_column = self.actual_all_tracked_table.columns[1]
        assert actual_first_column == expected_column

    def test_create_all_tracked_plist_files_table_third_column_attributes(self):
        """Test the styling and contents of the third column."""
        expected_column = Column(
            header="Script Called",
            footer="",
            header_style="",
            footer_style="",
            style="magenta",
            justify="center",
            vertical="top",
            overflow="fold",
            width=None,
            min_width=None,
            max_width=None,
            ratio=None,
            no_wrap=False,
            _index=2,
            _cells=["script_1", "script_2", "script_3"],
        )
        actual_first_column = self.actual_all_tracked_table.columns[2]
        assert actual_first_column == expected_column

    def test_create_all_tracked_plist_files_table_fourth_column_attributes(self):
        """Test the styling and contents of the fourth column."""
        expected_column = Column(
            header="Plist\nCreated",
            footer="",
            header_style="",
            footer_style="",
            style="",
            justify="center",
            vertical="top",
            overflow="fold",
            width=None,
            min_width=None,
            max_width=None,
            ratio=None,
            no_wrap=False,
            _index=3,
            _cells=["2024-03-28", "2024-04-28", "2024-04-28"],
        )
        actual_first_column = self.actual_all_tracked_table.columns[3]
        assert actual_first_column == expected_column

    def test_create_all_tracked_plist_files_table_fifth_column_attributes(self):
        """Test the styling and contents of the fifth column."""
        expected_column = Column(
            header="Schedule\nType",
            footer="",
            header_style="",
            footer_style="",
            style="",
            justify="center",
            vertical="top",
            overflow="fold",
            width=None,
            min_width=None,
            max_width=None,
            ratio=None,
            no_wrap=False,
            _index=4,
            _cells=["interval", "calendar", "interval"],
        )
        actual_first_column = self.actual_all_tracked_table.columns[4]
        assert actual_first_column == expected_column

    def test_create_all_tracked_plist_files_table_sixth_column_attributes(self):
        """Test the styling and contents of the sixth column."""
        expected_column = Column(
            header="Schedule\nValue",
            footer="",
            header_style="",
            footer_style="",
            style="",
            justify="center",
            vertical="top",
            overflow="fold",
            width=None,
            min_width=None,
            max_width=None,
            ratio=None,
            no_wrap=False,
            _index=5,
            _cells=["300", "{Hour: 15}", "1000"],
        )
        actual_first_column = self.actual_all_tracked_table.columns[5]
        assert actual_first_column == expected_column

    def test_create_all_tracked_plist_files_table_seventh_column_attributes(self):
        """Test the styling and contents of the seventh column."""
        expected_column = Column(
            header="Status",
            footer="",
            header_style="",
            footer_style="",
            style="",
            justify="center",
            vertical="top",
            overflow="fold",
            width=None,
            min_width=None,
            max_width=None,
            ratio=None,
            no_wrap=False,
            _index=6,
            _cells=["running", "running", "inactive"],
        )
        actual_first_column = self.actual_all_tracked_table.columns[6]
        assert actual_first_column == expected_column
