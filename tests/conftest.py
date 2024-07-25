import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pytest
from launchd_me.plist import (
    LaunchdMeInit,
    UserConfig,
)
from launchd_me.sql_statements import PLISTFILES_TABLE_INSERT_INTO


@dataclass
class ConfiguredEnvironmentObjects:
    """An object for passing an initialised launchd-me configuration.

    Allows tests to access all objects used to create the test environment.

    Attributes
    ----------
    tmp_dir: Path
        Use to pass a Pytest `tmp_path` object that can stand-in for a user's root dir.
    user_config: UserConfig
        A initialised UserConfiguration object.
    ldm_init: LaunchdMeInit
        The object used to Initialise the LaunchdMe application structure.
    """

    temp_user_dir: Path
    user_config: UserConfig
    ldm_init: LaunchdMeInit


@pytest.fixture
def mock_environment(tmp_path) -> ConfiguredEnvironmentObjects:
    """Provide a configured mock environment for testing.

    Doubles as an integration test for `UserConfig` and `LaunchdMeInit`.

    Creates a temporary environment with application directories and a db file using a
    Pytest `tmp_path` as the user's home dir. The database is empty and no plist files
    exist in the application directories. Overwrites the loaded `user_name` with
    `mock.user` for consistency.

    This can be used to allow real reading and writing to a database during testing and
    minimise the need for mocking.

    Returns
    -------
    mock_environment_configuration: ConfiguredEnvironmentObjects
        A ConfiguredEnvironmentObjects object making all aspects of the configuration
        accessible to any test.
    """
    temp_user_dir = tmp_path
    user_config = UserConfig(temp_user_dir)
    user_config.user_name = "mock_user_name"
    ldm_init = LaunchdMeInit(user_config)
    ldm_init.initialise_launchd_me()
    mock_environment_configuration = ConfiguredEnvironmentObjects(
        temp_user_dir, user_config, ldm_init
    )
    return mock_environment_configuration


def add_three_plist_file_entries_to_a_plist_files_table(ldm_db_file_path: Path) -> None:
    """
    Add entries for three synthetic plist files to the plist database table.

    Parameters
    ----------
    `ldm_db_file_path`
        Path to a db file. This is likely to be via a UserConfig object's ldm_db_file
        attribute, where the UserConfig object is configured to a Pytest `tmp_path`.
    """
    mock_plist_db_data = (
        (
            "mock_plist_1",
            "script_1",
            "2024-03-28T08:30:00Z",
            "interval",
            300,
            "running",
            "Mock plist file number 1",
            "<plist>\n<dict>\n<string>placeholder_content</string>\n</dict>\n</plist>",
        ),
        (
            "mock_plist_2",
            "script_2",
            "2024-04-28T09:30:00Z",
            "calendar",
            "{Hour: 15}",
            "running",
            "Mock plist file number 2",
            "<plist>\n<dict>\n<string>placeholder_content</string>\n</dict>\n</plist>",
        ),
        (
            "mock_plist_3",
            "script_3",
            "2024-04-28T09:30:00Z",
            "interval",
            1000,
            "inactive",
            "Mock plist file number 3",
            "<plist>\n<dict>\n<string>placeholder_content</string>\n</dict>\n</plist>",
        ),
    )
    connection = sqlite3.connect(ldm_db_file_path)
    cursor = connection.cursor()

    for plist_file in mock_plist_db_data:
        cursor.execute(
            PLISTFILES_TABLE_INSERT_INTO,
            (
                plist_file[0],
                plist_file[1],
                plist_file[2],
                plist_file[3],
                plist_file[4],
                plist_file[5],
                plist_file[6],
                plist_file[7],
            ),
        )
    connection.commit()
    connection.close()
