from enum import Enum
from pathlib import Path
from importlib import resources


class ScheduleType(str, Enum):
    interval = "interval"
    calendar = "calendar"


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
        self.script_name = script_name
        self.schedule_type = schedule_type
        self.schedule = schedule
        self.template_path = resources.files("launchd_me.templates").joinpath('plist_template.txt')
        self.project_dir = Path(__file__).resolve().parent
        self.plist_dir = Path(self.project_dir / "plist_files")
        self.plist_file_name = f"local.cbillows.{self.script_name.split('.')[0]}.plist"

if __name__ == "__main__":
    print("hello")
