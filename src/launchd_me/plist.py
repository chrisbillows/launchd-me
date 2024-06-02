import getpass
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from importlib import resources
from pathlib import Path

import rich
from rich.columns import Columns
from rich.console import Console
from rich.table import Row, Table

from launchd_me.logger_config import logger


class ScheduleType(str, Enum):
    """Enum for specifying plist schedule type."""

    interval = "interval"
    calendar = "calendar"


class UserConfig:
    """Configuration settings for project.

    The UserConfig object can be passed to any object that requires these settings.

    Parameters
    ----------
    user_dir: Path
        Path to a user directory (defaults to None as this is optional for testing).

    Attributes
    ----------
    user_name
    user_dir: Path
        The user's home directory.
    project_dir: Path
        The ``launchd-me`` directory in the user's home directory.
    plist_dir: Path
        The directory for storing plist files as
        ``user_home_dir/launchd-me/plist_files``.
    db_file: Path
        Path to the SQLite ``launchd-me.db`` file.
    plist_template_path: Path
        Path to the plist template at ``templates.plist_template.txt``

    """

    def __init__(self, user_dir: Path = None):
        self.user_name: str = getpass.getuser()
        self.user_dir = Path(user_dir) if user_dir else Path.home()
        self.project_dir = Path(self.user_dir / "launchd-me")
        self.plist_dir = Path(self.project_dir / "plist_files")
        self.ldm_db_file = Path(self.user_dir / "launchd-me" / "launchd-me.db")
        self.plist_template_path = resources.files("launchd_me.templates").joinpath(
            "plist_template.txt"
        )
        self.launch_agents_dir = Path(self.user_dir / "Library" / "LaunchAgents")


class PListDbConnectionManager:
    """Context manager for handling connections to the plist database.

    Creates the db if it doesn't already exist.
    """

    CREATE_TABLE_PLIST_FILES = """
    CREATE TABLE IF NOT EXISTS PlistFiles (
        PlistFileID INTEGER PRIMARY KEY AUTOINCREMENT,
        PlistFileName TEXT NOT NULL,
        ScriptName TEXT NOT NULL,
        CreatedDate TEXT NOT NULL,
        ScheduleType TEXT NOT NULL,
        ScheduleValue TEXT,
        CurrentState TEXT NOT NULL CHECK (CurrentState IN ('running', 'inactive', 'deleted')),
        Description TEXT
    );
    """

    CREATE_TABLE_INSTALLATION_EVENTS = """
    CREATE TABLE IF NOT EXISTS InstallationEvents (
        EventID INTEGER PRIMARY KEY AUTOINCREMENT,
        FileID INTEGER,
        EventType TEXT NOT NULL CHECK (EventType IN ('install', 'uninstall')),
        EventDate TEXT NOT NULL,
        Success INTEGER NOT NULL CHECK (Success IN (0, 1)), -- 0 = False, 1 = True
        FOREIGN KEY (FileID) REFERENCES PlistFiles (FileID)
    );
    """

    def __init__(self, user_config: UserConfig):
        self.db_file = user_config.ldm_db_file
        if not self.db_file.exists():
            self._create_db()
        self.connection = None
        self.cursor = None

    def __enter__(self):
        """Establish the connection and return the cursor."""
        self.connection = sqlite3.connect(self.db_file)
        self.cursor = self.connection.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Commit if no exception, otherwise rollback. Close the connection."""
        if exc_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()
        self.cursor.close()
        self.connection.close()

    def _create_db(self):
        """Create the database files and tables. Only runs if not previously run."""
        with sqlite3.connect(self.db_file) as connection:
            logger.debug("Creating database.")
            cursor = connection.cursor()
            cursor.execute(self.CREATE_TABLE_PLIST_FILES)
            cursor.execute(self.CREATE_TABLE_INSTALLATION_EVENTS)
            connection.commit()
            logger.debug("Database created.")


class LaunchdMeInit:
    """Initialise all required directories and files for launchd-me."""

    def __init__(self, user_config: UserConfig):
        self._user_config = user_config

    def initialise_launchd_me(self):
        """Runs all initialisation methods."""
        logger.debug("Initialising launchd-me")
        logger.debug("Ensure application directory exists.")
        self._create_app_directories()
        logger.debug("Ensure launchd-me database exists.")
        self._ensure_db_exists()

    def _create_app_directories(self):
        """Create the required app directories if they don't already exist."""
        self._user_config.project_dir.mkdir(parents=True, exist_ok=True)
        self._user_config.plist_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("App directories exist.")

    def _ensure_db_exists(self):
        """Create of the ldm database file if it doesn't already exist."""
        if not self._user_config.ldm_db_file.exists():
            PListDbConnectionManager(self._user_config)


@dataclass
class PlistFileObject:
    """I am not finished. Be kind to me."""

    plist_id: int
    plist_file_path: Path
    script_plist_automates: Path
    script_executable: bool
    installed: bool
    schedule_type: str
    schedule: int | dict
    plist_file_content: str  # or list of lines?


class PlistCreator:
    """Create launchd plist files for scheduling Python scripts.

    Attributes
    ----------
    script_name : str
        Python script to be scheduled. E.g. ``"my_script.py"``.
    schedule_type : ScheduleType
        Either ``"ScheduleType.interval"`` for time-based intervals or
        ``"ScheduleType.calendar"`` for specific dates/times.
    schedule : int or dict
        The required schedule. An integer of seconds for ``ScheduleType.interval``, a
        dict of ``"period": "duration"`` for `ScheduleType calendar` e.g.
        `"{'Hour': 15, 'Minute': 15}"`. Only a single date/time supported.

    Methods
    -------
    generate_plist_file():
        Generates the plist file.
    _validate_calendar_schedule():
        Validates a the periods and durations in a calendar schedule.
    _create_schedule_block():
        Creates the scheduling block based on the schedule type and schedule.
    _create_calendar_schedule_block():
        An additional method require to generate more complex calendar schedule blocks.

    Examples
    --------
    >>> plc = PlistCreator('interval_task.py', 'interval', 300)
    >>> plc.generate_plist_file()

    >>> plc = PlistCreator('daily_task.py', 'calendar', "{'Hour': 9, 'Minute': 0}")
    >>> plc.generate_plist_file()

    Example - Calendar Schedules
    ----------------------------
    Every day at 3:15 PM.
    >>> {'Hour': 15, 'Minute': 15}

    Every Monday at 8:00 AM. Weekday is specified with a range from 0 to 6, where 0 is
    Sunday and 6 is Saturday.
    >>> {'Weekday': 1, 'Hour': 8, 'Minute': 0}

    The 1st day of every month at midnight.
    >>> {'Day': 1, 'Hour': 0, 'Minute': 0}

    #### ----NOT SUPPORTED----
    Every 15 minutes during office hours (9 AM to 5 PM) on weekdays. An example
    illustrating the use of arrays for multiple values.
    >>> {
        'Hour': [9, 10, 11, 12, 13, 14, 15, 16],
        'Minute': [0, 15, 30, 45],
        'Weekday': [1, 2, 3, 4, 5]
        }

    On the 15th of June and December at 1:30 PM. Uses an array of dictionaries to
    specify multiple dates.
    >>> [
        {'Month': 6, 'Day': 15, 'Hour': 13, 'Minute': 30},
        {'Month': 12, 'Day': 15, 'Hour': 13, 'Minute': 30}
        ]

    """

    def __init__(
        self,
        path_to_script_to_automate: Path,
        schedule_type: ScheduleType,
        schedule: int | dict[str:int],
        description: str,
        make_executable: bool,
        auto_install: bool,
    ):
        """
        Attributes
        ----------
        path_to_script_to_automate : str
            A verfied, resolved pathlib Path object to a file.
        script_to_automate_name

        schedule_type : str
            Specifies the scheduling type: `"interval"` for time intervals or
            `"calendar"` for calendar dates/times.
        schedule : str or int
            The scheduling interval in seconds if `schedule_type` is "interval", or a
            string formatted dictionary representing duration(s) and duration value(s)
            if `schedule_type` is "calendar".

        """
        self.path_to_script_to_automate: Path = path_to_script_to_automate
        self.script_to_automate_name: str = self.path_to_script_to_automate.name
        self.schedule_type = schedule_type
        self.schedule = schedule
        self.description: str = description
        self.make_executable: bool = make_executable
        self.auto_install: bool = auto_install
        self._user_config: UserConfig = UserConfig()
        self.template_path = self._user_config.plist_template_path
        self.project_dir = self._user_config.project_dir
        self.plist_db_setter: PlistDbSetters = PlistDbSetters()

    def driver(self, plist_dir=None) -> Path:
        """Driver function."""
        if self.schedule_type == "calendar":
            self._validate_calendar_schedule(self.schedule)
        plist_filename = self._generate_file_name()
        plist_content = self._create_plist_content(plist_filename)
        plist_file_path = Path(self._user_config.plist_dir / plist_filename)
        self._write_file(plist_file_path, plist_content)
        plist_id = self.plist_db_setter.add_newly_created_plist_file(
            plist_filename,
            self.path_to_script_to_automate.name,
            self.schedule_type,
            self.schedule,
            self.description,
        )
        if self.make_executable:
            self._make_script_executable()
        if self.auto_install:
            plist_installer = PlistInstaller(plist_id, plist_file_path)
            plist_installer.install_plist(plist_id)
        return plist_file_path

    def _generate_file_name(self):
        with PListDbConnectionManager(self._user_config) as cursor:
            cursor.execute("SELECT COUNT(*) FROM PlistFiles")
            row_count = cursor.fetchone()[0]
        plist_id = row_count + 1
        plist_file_name = f"local.{self._user_config.user_name}.{self.path_to_script_to_automate.name.split('.')[0]}_{plist_id:04}.plist"
        logger.debug("Generated plist file name.")
        return plist_file_name

    def _write_file(self, plist_path: Path, plist_content: str):
        """Write content to a file path."""
        with open(str(plist_path), "w") as file_handle:
            file_handle.write(plist_content)
        logger.info(f"Plist file created at {plist_path}")

    def _make_script_executable(self):
        """
        Makes the specified script executable by changing its permissions.

        Parameters
        ----------
        script_path : str
            The path to the script file to make executable.

        Examples
        --------
        >>> make_script_executable('/path/to/my_script.py')
        This will change the permissions of 'my_script.py' to make it executable.
        """
        logger.info(f"Ensure {self.path_to_script_to_automate} is executable.")
        subprocess.run(["chmod", "+x", self.path_to_script_to_automate], check=True)

    def _validate_calendar_schedule(self, calendar_schedule: dict) -> None:
        """Validate a calendar schedule dictionary.

        For more info see: https://www.launchd.info - "Configruation" -
        "Starting a job at a specific time/date: StartCalendarInterval"
        """
        VALID_DURATIONS = {
            "Month": range(1, 13),
            "Day": range(1, 32),  # 1-31
            "Hour": range(0, 24),  # 0-23
            "Minute": range(0, 60),  # 0-59
            "Weekday": range(0, 7),  # 0-6 (0 is Sunday)
        }

        for period, duration in calendar_schedule.items():
            if period not in VALID_DURATIONS.keys():
                raise Exception(f"{period} is not a valid launchctl period.")
            if duration not in VALID_DURATIONS[period]:
                raise Exception(f"A duration of {duration} is not valid for {period}.")

    def _create_interval_schedule_block(self):
        """Generates the schedule block.

        Generates the scheduling block for the plist file based on `schedule_type` and
        `schedule_value`.

        Returns
        -------
        str
            The XML string for the scheduling part of the plist file.

        Raises
        ------
        ValueError
            If `schedule_type` is not one of the expected values ('interval' or 'calendar').

        """
        if self.schedule_type == "interval":
            schedule_block = (
                f"<key>StartInterval</key>\n\t<integer>{self.schedule}</integer>"
            )
            logger.debug("Generated interval block.")
            return schedule_block
        elif self.schedule_type == "calendar":
            schedule_block = self._create_calendar_schedule_block()
            return schedule_block
        else:
            raise ValueError("Invalid schedule type. Choose 'interval' or 'calendar'.")

    def _create_calendar_schedule_block(self):
        """Generates the schedule block for the calendar schedule type.

        Takes a duration dictionary  and returns a valid
        XML block as a string (including tabs and new lines).

        Returns
        -------
        str
            The XML string for the scheduling part of the plist file.

        Example:
        >>> "{'Hour': 9, 'Minute': 30}"
        <dict>
            <key>Hour</key>
            <integer>9</integer>
            <key>Minute</key>
            <integer>30</integer>
        </dict>

        """
        block_middle = ""
        for period, duration in self.schedule.items():
            block_middle += (
                f"\n\t\t<key>{period}</key>\n\t\t<integer>{duration}</integer>"
            )
        calendar_block = (
            "<key>StartCalendarInterval</key>\n\t<dict>" + block_middle + "\n\t</dict>"
        )
        return calendar_block

    def _create_plist_content(self, plist_filename):
        """Updates plist template with required script and schedule details.

        The new plist file is named after the script (without its extension) with a
        '.plist' extension.

        Examples
        --------
        >>> creator = PlistCreator('my_script.py', 'interval', 3600)
        >>> creator.create_plist()
        Plist file created at <project_dir>/plist_files/local.cbillows.my_script.plist

        """
        with open(self.template_path, "r") as file:
            content = file.read()
        schedule_block = self._create_interval_schedule_block()
        content = content.replace("{{SCHEDULE_BLOCK}}", schedule_block)
        content = content.replace("{{NAME_OF_PLIST_FILE}}", plist_filename)
        content = content.replace(
            "{{name_of_script.py}}", self.path_to_script_to_automate.name
        )
        content = content.replace(
            "{{ABSOLUTE_PATH_TO_WORKING_DIRECTORY}}",
            str(self.path_to_script_to_automate.parent),
        )
        # For log files.
        content = content.replace(
            "{{ABSOLUTE_PATH_TO_PROJECT_DIRECTORY}}", str(self.project_dir)
        )
        logger.debug("Generated plist file content.")
        return content


class PlistInstaller:
    """Install plist files"""

    def __init__(self, plist_id: int, plist_file_path: Path):
        self.plist_id = plist_id
        self.plist_file_path = plist_file_path
        self.user_config = UserConfig()
        self.plist_db_setters = PlistDbSetters()

    def install_plist(self, plist_id: int):
        """Driver method."""
        logger.debug("Creating symlink to plist in ~/Library/LaunchAgents")
        symlink_to_plist = self._create_symlink_in_launch_agents_dir()
        logger.debug("Validating plist file syntax.")
        self._run_command_line_tool("plutil", "-lint", symlink_to_plist)
        logger.debug("Loading plist file.")
        self._run_command_line_tool("launchctl", "load", symlink_to_plist)
        logger.debug("Updating plist installation status.")
        self.plist_db_setters.add_installed_installation_status(plist_id)

    def _create_symlink_in_launch_agents_dir(self):
        launch_agents_dir = self.user_config.launch_agents_dir
        if not self.plist_file_path.exists():
            raise FileNotFoundError(f"The file {self.plist_file_path} does not exist.")
        if not launch_agents_dir.exists():
            raise FileNotFoundError(
                f"The launchd directory {launch_agents_dir} was not found where expected."
            )
        symlink_file = launch_agents_dir / self.plist_file_path.name
        # Because I can never remember the order: `symlink_file.symlink_to(source_file)`
        symlink_file.symlink_to(self.plist_file_path)
        return symlink_file

    def _run_command_line_tool(self, tool, command, symlink_to_plist):
        try:
            logger.debug(f"Running launchctl {command}")
            result = subprocess.run(
                [tool, command, str(symlink_to_plist)],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.debug(f"Ran {tool} {command}")
            logger.debug(f"stdout: {result.stdout}")
            logger.debug(f"stderr: {result.stderr}")

        except subprocess.CalledProcessError as e:
            logger.error(
                f"Failed to run {tool} {command} for plist file: {symlink_to_plist}"
            )
            logger.error(f"Error message: {str(e)}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            raise e


class PlistUninstaller:
    def uninstall_plist():
        pass


class PlistDbSetters:
    @staticmethod
    def add_newly_created_plist_file(
        plist_filename, script_name, schedule_type, schedule_value, description
    ):
        now = datetime.now().isoformat()
        insert_sql = """
        INSERT INTO PlistFiles (
            PlistFileName,
            ScriptName,
            CreatedDate,
            ScheduleType,
            ScheduleValue,
            CurrentState,
            Description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        logger.debug("Adding new plist file to database.")
        with PListDbConnectionManager(UserConfig()) as cursor:
            cursor.execute(
                insert_sql,
                (
                    plist_filename,
                    script_name,
                    now,
                    schedule_type,
                    schedule_value,
                    "inactive",
                    description,
                ),
            )
        return cursor.lastrowid

    @staticmethod
    def add_installed_installation_status(file_id):
        with PListDbConnectionManager(UserConfig()) as cursor:
            cursor.execute(
                "UPDATE PlistFiles SET CurrentState = 'running' WHERE PlistFileID = ?",
                (file_id,),
            )

    def add_uninstalled_installation_status(file_id):
        with PListDbConnectionManager(UserConfig()) as cursor:
            cursor.execute(
                "UPDATE PlistFiles SET CurrentState = 'inactive' WHERE PlistFileID = ?",
                (file_id,),
            )

    def add_deleted_installation_status():
        pass


class PlistDbGetters:
    """Getters for database values. For displaying values use ``DBDisplayer()``."""

    def __init__(self, user_config: UserConfig):
        self._user_config = user_config

    def get_all_tracked_plist_files(self) -> tuple[Row, ...]:
        """Get all details of all tracked plist files, including 'deleted' files.

        Returns
        -------
        all_rows: tuple[Row, ...]
            A tuple of all database rows as SQLite3 Row objects, where Row[0] =
            "PlistFileID" etc.
        """
        with PListDbConnectionManager(self._user_config) as cursor:
            cursor.execute(
                "SELECT PlistFileID, PlistFileName, ScriptName, CreatedDate, "
                "ScheduleType, ScheduleValue, CurrentState FROM PlistFiles"
                " ORDER BY PlistFileID"
            )
            all_rows = cursor.fetchall()
        return all_rows

    def get_a_single_plist_file(self, plist_id) -> tuple[Row, list]:
        """Get column headings and details of a given plist file.

        Uses an SQLite query to get the plist file details then the `cursor.description`
        attribute to get the column headings. These are zipped into a dictionary in the
        format ``{"field_name", value}``.

        Attributes
        ----------
        plist_id: int
            The id of the plist file.

        Returns
        -------
        plist_detail: dict
            A dict of the plist file details in the format ``{"field_name", value}``.
        """
        with PListDbConnectionManager(self._user_config) as cursor:
            cursor.execute(
                "SELECT * FROM  PlistFiles WHERE plistFileId = ?", (plist_id,)
            )
            target_row = cursor.fetchall()
            description = [description[0] for description in cursor.description]
        plist_detail = dict(zip(description, target_row[0]))
        return plist_detail


class DBDisplayerBase:
    def __init__(self) -> None:
        self._user_config = UserConfig()
        self._db_getter = PlistDbGetters(self._user_config)

    def _format_date(self, row: list):
        """Reformats an ISO date as YYYY-MM-DD. Expects the ISO date at index 3."""
        iso_date = datetime.fromisoformat(row[3])
        formatted_date = iso_date.strftime("%d-%m-%Y")
        row[3] = formatted_date
        return row


class DBAllRowsDisplayer(DBDisplayerBase):
    def display_all_rows_table(self, all_rows) -> None:
        console = Console()

        table = self._create_table()
        for row in all_rows:
            row = list(row)
            row = self._format_date(row)
            table.add_row(*[str(item) for item in row])
        print()  # Just to give an extra line for style.
        console.print(table)

    def _create_table(self) -> Table:
        table = Table(box=rich.box.SIMPLE, show_header=True)
        table.title = f"  USER `{self._user_config.user_name}` PERSONAL PLIST FILES"
        table.caption = "Run `ldm list <ID> for full plist file details."
        table.title_justify = "left"
        table.title_style = "blue3 bold italic"
        table.add_column("File\nID", justify="center", overflow="wrap")
        table.add_column(
            "Plist Filename", justify="center", overflow="fold", no_wrap=True
        )
        table.add_column(
            "Script Called", justify="center", overflow="fold", style="magenta"
        )
        table.add_column("Plist\nCreated", justify="center", overflow="fold")
        table.add_column("Schedule\nType", justify="center", overflow="fold")
        table.add_column("Schedule\nValue", justify="center", overflow="fold")
        table.add_column("Status", justify="center", overflow="fold")
        return table

    def display_all_tracked_without_deleted(self):
        # for row in self.db_setup.db_cursor.execute(
        #     "SELECT FileID, PlistFileName, ScriptName, CreatedDate, ScheduleType, ScheduleValue, CurrentState FROM PlistFiles ORDER BY FileID"
        # ):
        # TODO: Add exception for deletion statiusif
        pass


class DBPlistDetailDisplayer(DBDisplayerBase):
    def display_plist_detail(self, plist_detail: dict) -> None:
        console = Console()
        table = Table()
        table.add_column("Field")
        table.add_column("Value")
        table.title_justify = "left"
        table.title_style = "blue3 bold italic"
        for field_name, value in plist_detail.items():
            # TODO: Move this to DBGetter.
            if isinstance(value, int):
                value = str(value)
            # TODO: Need to generalise `_format_date` I guess?
            # if field_name == "CreatedDate":
            #     value = self._format_date(value)
            if field_name == "ScriptName":
                table.add_row(field_name, value, style="magenta")
            else:
                table.add_row(field_name, value)
        print()
        console.print(table)
