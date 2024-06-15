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

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection, Cursor
from unittest.mock import MagicMock, Mock, patch

import pytest
from launchd_me.plist import (
    LaunchdMeInit,
    PlistCreator,
    PListDbConnectionManager,
    PlistInstallationManager,
    ScheduleType,
    UserConfig,
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

    def test_plist_installation_manager_insantiates_as_expected(self):
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
        assert plc_interval.make_executable == True
        assert plc_interval.auto_install == True

    def test_plist_creator_initialisation_with_calendar_schedule(self, plc_calendar):
        assert plc_calendar.path_to_script_to_automate == Path("calendar_task.py")
        assert plc_calendar.schedule_type == ScheduleType.calendar
        assert plc_calendar.schedule == {"Day": 15, "Hour": 15}
        assert plc_calendar.description == "A description"
        assert plc_calendar.make_executable == True
        assert plc_calendar.auto_install == True

    # TODO: Move to integration tests - are we building as a part of this? Now driver.
    # def test_generate_plist_file_interval(plc_interval, tmp_path):
    #     temp_plist_dir = tmp_path
    #     plc_interval.generate_plist_file(temp_plist_dir)

    #     temp_plist_file_path = str(Path(tmp_path / plc_interval.plist_file_name))
    #     plutil_verdict = subprocess.run(
    #         ["plutil", temp_plist_file_path], capture_output=True, text=True
    #     )
    #     actual_returncode = plutil_verdict.returncode
    #     actual_stdout_suffix = re.search(r":\s*(.*)", plutil_verdict.stdout).group(1)

    #     assert actual_returncode == 0
    #     assert actual_stdout_suffix == "OK"

    # def test_generate_plist_file_calendar(plc_calendar, tmp_path):
    #     temp_plist_dir = tmp_path
    #     plc_calendar.generate_plist_file(temp_plist_dir)

    #     temp_plist_file_path = str(Path(tmp_path / plc_calendar.plist_file_name))
    #     plutil_verdict = subprocess.run(
    #         ["plutil", temp_plist_file_path], capture_output=True, text=True
    #     )
    #     actual_returncode = plutil_verdict.returncode
    #     actual_stdout_suffix = re.search(r":\s*(.*)", plutil_verdict.stdout).group(1)

    #     assert actual_returncode == 0
    #     assert actual_stdout_suffix == "OK"

    # def test_generate_plist_file_interval_returns_file_path(plc_interval, tmp_path):
    #     temp_plist_dir = tmp_path
    #     actual = plc_interval.generate_plist_file(temp_plist_dir)
    #     temp_plist_file_path = str(Path(tmp_path / plc_interval.plist_file_name))
    #     assert actual == temp_plist_file_path

    def test_generate_file_name(self):
        pass

    def test_write_file(self):
        pass

    def test_make_script_executable(self):
        pass

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

    def test_create_interval_schedule_block(self, plc_interval):
        expected = "<key>StartInterval</key>\n\t<integer>300</integer>"
        actual = plc_interval._create_interval_schedule_block()
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

    def test_create_plist_content(self):
        pass
