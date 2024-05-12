from datetime import datetime
from enum import Enum
from pathlib import Path
from importlib import resources
import subprocess
import sqlite3


from .logger_config import logger


CREATE_TABLE_PLIST_FILES = """
CREATE TABLE IF NOT EXISTS PlistFiles (
    FileID INTEGER PRIMARY KEY AUTOINCREMENT,
    PlistFileName TEXT NOT NULL, 
    ScriptName TEXT NOT NULL,
    CreatedDate TEXT NOT NULL,
    ScheduleType TEXT NOT NULL,
    ScheduleValue TEXT,
    CurrentState TEXT NOT NULL CHECK (CurrentState IN ('active', 'inactive', 'deleted'))
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

CREATE_TABLE_CURRENT_FILE_SUFFIX = """
CREATE TABLE IF NOT EXISTS FileSuffix (
    FileSuffix INTEGER
)
"""


class ScheduleType(str, Enum):
    interval = "interval"
    calendar = "calendar"


class UserSetUp:
    
    def __init__(self, user_dir: str=None):
        self.user_dir = Path(user_dir) if user_dir else Path.home()
        self.project_dir = Path(self.user_dir / "launchd-me")
        self.plist_dir = Path(self.project_dir / "plist_files")
        self.db_file = Path(self.user_dir / "launchd-me" / "launchd-me.db") 

class PlistDbBase():
    """Base class for objects to handle plist database management operations."""

    def __init__(self, user_setup: UserSetUp):
        self._user_setup = user_setup
        self.plist_db = user_setup.db_file
        self.connection = sqlite3.connect(self.plist_db)
        self.db_cursor = self.connection.cursor()

class PlistDbInit(PlistDbBase):
    """Runs on application installion or reset."""
    
    def __init__(self):
        super().__init__()
     
    def create_db(self):
        logger.debug("Creating database.")
        self.db_cursor.execute(CREATE_TABLE_PLIST_FILES)
        self.db_cursor.execute(CREATE_TABLE_INSTALLATION_EVENTS)
        self.db_cursor.execute(CREATE_TABLE_CURRENT_FILE_SUFFIX)
        logger.debug("Database created.")


    
class LaunchdMeInit():
    
    def __init__(self, user_setup: UserSetUp, db_initialisor: PlistDbInit):
        self._user_setup = user_setup
        self._db_initialisor = db_initialisor
        
    def initialise_launchd_me(self):
        logger.debug("Ensure application directories exist.")
        self._ensure_directories_exist()
        logger.debug("Ensure launchd-me database exists.")
        self._ensure_db_exists()
        logger.debug("Ensure database exists.")
        self._db_initialisor.create_db()
           
    def _ensure_directories_exist(self):
        if not self._ldm_usersetup.project_dir.exists():
            logger.debug("Creating app directories.")
            self._create_app_directories()
        
    def _create_app_directories(self):
        self._ldm_usersetup.project_dir.mkdir(parents=True, exist_ok=True)
        self._ldm_usersetup.plist_dir.mkdir(parents=True, exist_ok=True)
       
    def _ensure_db_exists(self):
        if not self.db_file.exists():
            db_init = PlistDbInit(self.db_file)
            logger.debug("Creating database.")
            db_init.create_db()

class Plist():
    pass


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
        script_name: str,
        schedule_type: ScheduleType,
        schedule: int | dict[str:int],
    ):
        """
        Parameters
        ----------
        script_name : str
            Filename of the script to be executed by the launchd job.
        schedule_type : str
            Specifies the scheduling type: `"interval"` for time intervals or
            `"calendar"` for calendar dates/times.
        schedule : str or int
            The scheduling interval in seconds if `schedule_type` is "interval", or a
            string formatted dictionary representing duration(s) and duration value(s)
            if `schedule_type` is "calendar".

        """
        self.template_path = resources.files("launchd_me.templates").joinpath('plist_template.txt') 
        self.script_name = script_name
        self.schedule_type = schedule_type
        self.schedule = schedule
        self.plist_file_name = f"local.cbillows.{self.script_name.split('.')[0]}.plist"
        self.db_setter = PlistDbSetters()
        
    def generate_plist_file(self, plist_dir=None) -> str:
        """Driver function.
        """
        if self.schedule_type == "calendar":
            self._validate_calendar_schedule(self.schedule)
        plist_content = self._create_plist_content()

        # For testing.
        if not plist_dir:
            plist_dir = self.plist_dir
        plist_file_path = str(Path(plist_dir / self.plist_file_name))
        self._write_file(plist_file_path, plist_content)
        print(f"Plist file created at {plist_file_path}")
        self.db_setter.add_newly_created_plist_file()
        return plist_file_path

    def _write_file(self, plist_path: str, plist_content: str):
        """Write content to a file path.
        """
        with open(plist_path, "w") as file_handle:
            file_handle.write(plist_content)

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

    def _create_plist_content(self):
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
                template = file.read()

            schedule_block = self._create_interval_schedule_block()
            content = template.replace("{{NAME-OF-SCRIPT}}", self.script_name.split(".")[0])
            content = content.replace("{{name_of_script.py}}", self.script_name)
            content = content.replace(
                "{{ABSOLUTE_PATH_TO_PROJECT_DIRECTORY}}", str(self.project_dir)
            )
            content = content.replace("{{SCHEDULE_BLOCK}}", schedule_block)
            return content


class PlistInstallationManager:
    """Install and uninstall plist files"""

    def __init__():
        pass

    def make_script_executable(script_path):
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
        subprocess.run(["chmod", "+x", script_path], check=True)
        print(f"Made script executable: {script_path}")


class PlistDbSetters(PlistDbBase):
   
    def add_newly_created_plist_file(self, plist_filename, script_name, schedule_type, schedule_value):
        now = datetime.now().isoformat()
        insert_sql = """
        INSERT INTO PlistFiles (
            PlistFileName, 
            ScriptName, 
            CreatedDate, 
            ScheduleType, 
            ScheduleValue, 
            CurrentState
        )
        VALUES (?, ?, ?, ?, ?, ?);
        """
        self.db_cursor.execute(insert_sql, (
            plist_filename, script_name, now, schedule_type, schedule_value, 'inactive'
            )
        )
        self.connection.commit()
        
    # So how will the user identify the plist?
    def add_installed_installation_status():
        pass
    
    def add_uninstalled_installation_status():
        pass
    
    def add_deleted_installation_status():
        pass

      
class PlistDbGetters(PlistDbBase):
    
    def _display_all_tracked_plist_files(self):
        """Includes deleted files."""
        
        for row in self.db_cursor.execute("SELECT FileID, PlistFileName, ScriptName, CreatedDate, ScheduleType, ScheduleValue, CurrentState FROM PlistFiles ORDER BY FileID"):
            print(row)

    def display_all_tracked_without_deleted(self):
        for row in self.db_cursor.execute("SELECT FileID, PlistFileName, ScriptName, CreatedDate, ScheduleType, ScheduleValue, CurrentState FROM PlistFiles ORDER BY FileID"):
            # TODO: Add exception for delection statiusif 
            print(row)
            
    def display_plist_by_id(self):
        pass

# plist_path = os.path.expanduser('~/Library/LaunchAgents/com.example.myscript.plist')

# def create_plist(file_path):
#     with open(plist_path, 'w') as plist_file:
#         plist_file.write(plist_content)
#     print(f'Plist created at {plist_path}')

# def load_plist():
#     subprocess.run(['launchctl', 'load', plist])
