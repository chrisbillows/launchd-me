import getpass
import logging
import re
import sqlite3
import subprocess
from datetime import datetime
from enum import Enum
from importlib import resources
from pathlib import Path
from typing import Dict, Union

import rich
from rich.console import Console
from rich.table import Row, Table

from launchd_me.logger_config import logger
from launchd_me.sql_statements import PLISTFILES_TABLE_INSERT_INTO


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
    user_name: str
        The current user's name.
    user_dir: Path
        The user's home directory.
    project_dir: Path
        The ``launchd-me`` directory in the user's home directory.
    plist_dir: Path
        The directory for storing plist files as
        ``user_home_dir/launchd-me/plist_files``.
    ldm_db_file: Path
        Path to the SQLite ``launchd-me.db`` file.
    plist_template_path: Path
        Path to the plist template at ``templates.plist_template.txt``
    launch_agents_dir: Path
        Path to the MacOS standard user launch agents directory; plist files saved/
        symlinked in this dir are automatically loaded on restart.
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

    Creates the db if it doesn't already exist. Requires the launchd-me dir to exist
    assuming launchd-me init has already run.

    Raises
    ------
    FileNotFoundError:
        If the launchd-me directory doesn't exist and informs the developer that
        launchd-me init must run first.

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
        if not user_config.project_dir.exists():
            try:
                raise FileNotFoundError(
                    "Launchd-me directory not created. Ensure "
                    "LaunchdMeInit.initialise_launchd_me() is run first."
                )
            except FileNotFoundError as error:
                logging.exception("Application directory is missing.")
                raise
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


class LaunchdMeUninstaller:
    def __init__(self, user_config: UserConfig):
        self._user_config = user_config

    def uninstall_launchd_me(self):
        pass

    def delete_user_info(self):
        pass


class InvalidScheduleType(Exception):
    pass


class PlistCreator:
    """
    Generate a launchd plist files to schedule a script.

    This class handles the creation of plist files for automating scripts on macOS
    using the launchd system, optionally making the script to be automated executable and automatically
    installing the plist file.

    The content of a plist file is stored in user's LaunchdMe database, along with
    installation status and content.

    Parameters
    ----------
    path_to_script_to_automate : Path
        The path to the script to be automated by the plist.
    schedule_type : str
        Specifies the scheduling type: `"interval"` for time intervals or
        `"calendar"` for calendar dates/times.
    schedule : Union[int, Dict[str, int]]
        The scheduling interval in seconds if `schedule_type` is "interval", or a
        dictionary representing specific times if `schedule_type` is "calendar".
    description : str
        The user's description of what the script/plist file is automating.
    make_executable : bool
        Whether to make the script executable if it is not already.
    auto_install : bool
        Whether to automatically install the plist file upon creation.
    user_config : UserConfig
        Configuration for user-specific settings including the application directories
        and the database file.

    Attributes
    ----------
    db_setter : PlistDBSetters
        Interface to update the database when plist creation occurs.

    Methods
    -------
    driver()
        Runs all the functionality of the class. This is the public method to call, for
        interval or calendar scheduling, to create plist files and manage them in a
        user's LaunchdMe database.
    """

    def __init__(
        self,
        path_to_script_to_automate: Path,
        schedule_type: ScheduleType,
        schedule: Union[int, Dict[str, int]],
        description: str,
        make_executable: bool,
        auto_install: bool,
        user_config: UserConfig,
    ) -> None:
        """
        Initialise a new PlistCreator instance.

        Parameters
        ----------
        path_to_script_to_automate : Path
            The path to the script to be automated by the plist.
        schedule_type : ScheduleType
            The type of schedule for the plist (interval or calendar).
        schedule : Union[int, Dict[str, int]]
            Interval in seconds or dictionary for calendar scheduling.
        description : str
            Description of the plist's purpose.
        make_executable : bool
            If True, makes the script executable.
        auto_install : bool
            If True, automatically installs the plist after creation.
        user_config : UserConfig
            Configuration for user-specific settings like directories and database paths.

        Attributes
        ----------
        db_setter : PlistDBSetters
            Interface to update the database when plist creation occurs.
        """

        self.path_to_script_to_automate = path_to_script_to_automate
        self.schedule_type = schedule_type
        self.schedule = schedule
        self.description = description
        self.make_executable = make_executable
        self.auto_install = auto_install
        self.user_config = user_config
        self.db_setter = PlistDbSetters(self.user_config)

    def driver(self, plist_dir=None) -> Path:
        """
        Driver method for all PlistCreator functionality.

        Returns
        -------
        Path
            A Path to the newly created plist file. The plist file is tracked in the
            user's LaunchdMe database and, optionally, the script the plist automates
            is made executable and the plist file itself is installed to run.
        """
        if self.schedule_type == "calendar":
            self._validate_calendar_schedule(self.schedule)
        plist_filename = self._generate_file_name()
        schedule_block = self._create_schedule_block()
        plist_content = self._create_plist_content(plist_filename, schedule_block)
        plist_file_path = Path(self.user_config.plist_dir / plist_filename)
        self._write_file(plist_file_path, plist_content)
        plist_id = self.db_setter.add_newly_created_plist_file(
            plist_filename,
            self.path_to_script_to_automate.name,
            self.schedule_type,
            self.schedule,
            self.description,
        )
        if self.make_executable:
            self._make_script_executable()
        if self.auto_install:
            plist_installer = PlistInstallationManager(self.user_config, self.db_setter)
            plist_installer.install_plist(plist_id, plist_file_path)
        return plist_file_path

    def _generate_file_name(self) -> str:
        """
        Generates the file name for the plist file.

        Important as this is installed in LaunchAgents and needs to be recognisable. The
        filename uses the `local` prefix for easy identification within macOS.

        It attempts to ensure uniqueness by using the next index in the Launchd Me
        database. Plist entries are never deleted, only marked "deleted" so this number
        will be accurate in normal usage (assuming the user doesn't mirror the Launchd
        Me naming conventions).

        Returns
        -------
        str
            The plist filename.
        """

        with PListDbConnectionManager(self.user_config) as cursor:
            cursor.execute("SELECT COUNT(*) FROM PlistFiles")
            row_count = cursor.fetchone()[0]
        plist_id = row_count + 1
        plist_file_name = f"local.{self.user_config.user_name}.{self.path_to_script_to_automate.name.split('.')[0]}_{plist_id:04}.plist"
        logger.debug("Generated plist file name.")
        return plist_file_name

    def _write_file(self, plist_path: Path, plist_content: str) -> None:
        """
        Write content to a file path.
        """
        with open(str(plist_path), "w") as file_handle:
            file_handle.write(plist_content)
        logger.info(f"Plist file created at {plist_path}")

    def _make_script_executable(self) -> None:
        """
        Makes the script to be automated executable by changing its permissions.

        Raises
        ------
        CalledProcessError
            If the subprocess call returns a non-zero (error) status.
        """
        logger.info(f"Ensure {self.path_to_script_to_automate} is executable.")
        subprocess.run(["chmod", "+x", self.path_to_script_to_automate], check=True)

    def _validate_calendar_schedule(self, calendar_schedule: dict) -> None:
        """
        Validate a calendar schedule dictionary.

        For more info see: https://www.launchd.info. Select "Configuration" -
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

    def _create_schedule_block(self) -> str:
        """
        Generates the schedule block for the plist file.

        Contains logic to create both interval and calendar schedule blocks.

        Returns
        -------
        str
            The XML string for the scheduling block of the plist file.

        Raises
        ------
        ValueError
            If `schedule_type` is not one of the expected values ('interval' or
            'calendar').
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
            raise ValueError("Invalid schedule type.")

    def _create_calendar_schedule_block(self) -> str:
        """
        Generates the schedule block for the calendar schedule type.

        Takes a duration dictionary and returns a valid XML block as a string (including
        tabs and new lines).

        Returns
        -------
        str
            The XML string for the scheduling block of the plist file.
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

    def _create_plist_content(self, plist_filename, schedule_block) -> str:
        """Create plist body content.

        Replaces the plist template  `{{PLACEHOLDERS}}` with required details.

        Returns
        -------
        str
            The full content of the plist file based on the parameters passed with the
            `PlistCreator` was instantiated.
        """
        with open(self.user_config.plist_template_path, "r") as file:
            content = file.read()
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
            "{{ABSOLUTE_PATH_TO_PROJECT_DIRECTORY}}", str(self.user_config.project_dir)
        )
        logger.debug("Generated plist file content.")
        return content


class PlistDbSetters:
    def __init__(self, user_config: UserConfig) -> None:
        self.user_config = user_config

    def add_newly_created_plist_file(
        self, plist_filename, script_name, schedule_type, schedule_value, description
    ):
        now = datetime.now().isoformat()
        logger.debug("Adding new plist file to database.")
        with PListDbConnectionManager(self.user_config) as cursor:
            cursor.execute(
                PLISTFILES_TABLE_INSERT_INTO,
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

    def add_running_installation_status(self, file_id):
        with PListDbConnectionManager(self.user_config) as cursor:
            cursor.execute(
                "UPDATE PlistFiles SET CurrentState = 'running' WHERE PlistFileID = ?",
                (file_id,),
            )

    def add_inactive_installation_status(self, file_id):
        with PListDbConnectionManager(self.user_config) as cursor:
            cursor.execute(
                "UPDATE PlistFiles SET CurrentState = 'inactive' WHERE PlistFileID = ?",
                (file_id,),
            )
        logger.debug(f"Plist {file_id} now has 'inactive' status.")


class PlistInstallationManager:
    """Install and un-install plist files"""

    def __init__(self, user_config: UserConfig, plist_db_setters: PlistDbSetters):
        self.user_config = user_config
        self.plist_db_setters = plist_db_setters

    def install_plist(self, plist_id: int, plist_file_path: Path):
        """Driver method."""
        logger.debug("Creating symlink to plist in ~/Library/LaunchAgents")
        symlink_to_plist = self._create_symlink_in_launch_agents_dir(plist_file_path)
        logger.debug("Validating plist file syntax.")
        self._run_command_line_tool("plutil", "-lint", symlink_to_plist)
        logger.debug("Loading plist file.")
        self._run_command_line_tool("launchctl", "load", symlink_to_plist)
        logger.debug("Plist file now active.")
        logger.debug("Updating Plist file installation status.")
        self.plist_db_setters.add_running_installation_status(plist_id)
        logger.debug("Database updated.")

    def uninstall_plist(self, plist_id: int, symlink_to_plist: Path):
        logger.debug("Unload plist file.")
        self._run_command_line_tool("launchctl", "unload", symlink_to_plist)
        logger.debug("Removing symlink")
        symlink_to_plist.unlink()
        logger.debug("Updating database.")
        self.plist_db_setters.add_inactive_installation_status(plist_id)
        logger.info(f"Plist file {plist_id} successfully uninstalled.")

    def _create_symlink_in_launch_agents_dir(self, plist_file_path: Path):
        launch_agents_dir = self.user_config.launch_agents_dir
        if not plist_file_path.exists():
            raise FileNotFoundError(f"The file {plist_file_path} does not exist.")
        if not launch_agents_dir.exists():
            raise FileNotFoundError(
                f"The expected launchd directory {launch_agents_dir} was not found."
            )
        symlink_file = launch_agents_dir / plist_file_path.name
        # Because I can never remember the order: `symlink_file.symlink_to(source_file)`
        symlink_file.symlink_to(plist_file_path)
        return symlink_file

    def _run_command_line_tool(self, tool, command, symlink_to_plist):
        try:
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


class PlistFileIDNotFound(Exception):
    pass


class PlistDbGetters:
    """Getters for database values. For displaying the values use a `DbDisplayer()`."""

    def __init__(self, user_config: UserConfig) -> None:
        """Initializer. ``user_config`` supplies the path to the database.

        Parameters
        ----------
        user_config: UserConfig
            A UserConfig object.
        """
        self._user_config = user_config

    def verify_a_plist_id_is_valid(self, plist_id) -> None:
        """Checks if a plist file ID is valid.

        Attributes
        ----------
        plist_id: int
            A plist_id as an int. Argparse validates the user input as an int.

        Raises
        ------
        PlistFileIDNotFound
            If the given plist id is not in the database.
        """
        logger.debug(f'Checking if plist_id "{plist_id}" is in the database')
        with PListDbConnectionManager(self._user_config) as cursor:
            cursor.execute(
                "SELECT * FROM  PlistFiles WHERE plistFileId = ?", (plist_id,)
            )
            target_row = cursor.fetchall()
            if not target_row:
                message = f"There is no plist file with the ID: {plist_id}"
                logger.error(message)
                raise PlistFileIDNotFound(message)
            logger.debug(f'Plist_id "{plist_id}" is in the database')

    def get_all_tracked_plist_files(self) -> list[tuple]:
        """Get details of all tracked plist files.

        Returns
        -------
        all_rows: list[tuple]
            A list of all database rows as tuples, where tuple[0] =
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

    def get_a_single_plist_file_details(self, plist_id) -> dict:
        """Get all details and column headings of a given plist file.

        The method calls ``verify_a_plist_is_valid`` to verify ``plist_id`` is in the
        database. The method fetches the plist file details then the uses
        `cursor.description` attribute to fetch the column headings. These column
        headings and plist file details are zipped into a dictionary in the format
        ``{"field_name": "value"}``.

        Parameters
        ----------
        plist_id: int
            A plist_id as an int. Argparse validates the user input as an int.

        Returns
        -------
        plist_detail: dict
            A dict of the plist file details in the format ``{'PlistFileID': 1,
            'PlistFileName': 'mock_plist_1' etc}``.
        """
        self.verify_a_plist_id_is_valid(plist_id)
        with PListDbConnectionManager(self._user_config) as cursor:
            cursor.execute(
                "SELECT * FROM  PlistFiles WHERE plistFileId = ?", (plist_id,)
            )
            target_row = cursor.fetchall()
            description = [description[0] for description in cursor.description]
        plist_detail = dict(zip(description, target_row[0]))
        return plist_detail


class DbDisplayer:
    def __init__(self, user_config: UserConfig) -> None:
        self._user_config = user_config

    # TODO: Refactor once we actually have plist file contents in the db.
    def display_plist_detail(self, plist_detail) -> None:
        """Display a detailed overview of a single plist file.

        Note
        ----
        This is currently hardcoded to display the plist file content for every plist.

        Parameters
        ----------
        plist_detail:


        """
        console = Console()
        table = Table()
        table.add_column("Plist File")
        table.add_column("Details")
        for field_name, value in plist_detail.items():
            if isinstance(value, int):
                value = str(value)
            if field_name == "ScriptName":
                table.add_row(field_name, value, style="magenta")
            else:
                table.add_row(field_name, value)
        file = "/Users/chrisbillows/launchd-me/plist_files/local.chrisbillows.whole_new_name_0001.plist"
        table.add_row("________________", "________________")
        table.add_row("PlistFileContent", "")
        with open(file, "r") as file_handle:
            contents = file_handle.readlines()
        for line in contents:
            output = line.replace("\n", "")
            output = self._style_xml_tags(output)
            table.add_row("", output)
        print()  # Just to give an extra line for style.
        console.print(table)

    def display_all_rows_table(self, all_rows: list[tuple]) -> None:
        """Public method to display rows of PlistFileData in a table.

        Parameters
        ----------
        all_rows: list[tuple]
            A list of all database rows as tuples, where tuple[0] =
            "PlistFileID" etc.
        """
        table = self._create_table(all_rows)
        self._table_displayer(table)

    def _format_date(self, iso_date: str) -> str:
        """Reformats an ISO date as YYYY-MM-DD. Expects the ISO date."""
        iso_date = datetime.fromisoformat(iso_date)
        formatted_date = iso_date.strftime("%d-%m-%Y")
        return formatted_date

    def _style_xml_tags(self, text_to_style: str) -> str:
        re_pattern = r"<([^>]+)>"
        matches = re.finditer(re_pattern, text_to_style)
        last_end = 0
        styled_text = ""

        for match in matches:
            start, end = match.span()
            styled_text += text_to_style[last_end:start]
            styled_text += f"[grey69]{text_to_style[start:end]}[/grey69]"
            last_end = end
        styled_text += text_to_style[last_end:]
        return styled_text

    def _table_displayer(self, table: Table) -> None:
        """Print a table to the console.

        Isolated for easy testing.

        Parameters
        ----------
        table: Table
            A rich Table object.
        """
        console = Console()
        console.print("\n", table)

    def _create_table(self, all_rows) -> Table:
        """Create a formatted `rich` Table to display rows of PlistFile data.

        Parameters
        ----------
        all_rows: list[tuple]
            A list of all database rows as tuples, where tuple[0] =
            "PlistFileID" etc.

        Returns
        -------
        table: Table
            A formatted `rich` table containing the ``all_rows`` data.
        """
        table = Table(box=rich.box.SIMPLE, show_header=True)
        table.title = f"  USER `{self._user_config.user_name}` PERSONAL PLIST FILES"
        table.caption = "Run `ldm list <ID> for full plist file details."
        table.title_justify = "left"
        table.title_style = "blue3 bold italic"
        table.add_column("File\nID", justify="center", overflow="wrap")
        table.add_column(
            "Plist Filename", justify="left", overflow="fold", no_wrap=True
        )
        table.add_column(
            "Script Called", justify="center", overflow="fold", style="magenta"
        )
        table.add_column("Plist\nCreated", justify="center", overflow="fold")
        table.add_column("Schedule\nType", justify="center", overflow="fold")
        table.add_column("Schedule\nValue", justify="center", overflow="fold")
        table.add_column("Status", justify="center", overflow="fold")
        for row in all_rows:
            row = list(row)
            row[3] = self._format_date(row[3])
            table.add_row(*[str(item) for item in row])
        return table
