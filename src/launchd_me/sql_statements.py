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


CREATE_TABLE_PLISTFILES = """
CREATE TABLE IF NOT EXISTS PlistFiles (
    PlistFileID INTEGER PRIMARY KEY AUTOINCREMENT,
    PlistFileName TEXT NOT NULL,
    ScriptName TEXT NOT NULL,
    CreatedDate TEXT NOT NULL,
    ScheduleType TEXT NOT NULL,
    ScheduleValue TEXT NOT NULL,
    CurrentState TEXT NOT NULL CHECK (CurrentState IN ('running', 'inactive', 'deleted')),
    Description TEXT,
    PlistFileContent TEXT
);
"""

PLISTFILES_INSERT_RECORD_INTO = """
INSERT INTO PlistFiles (
    PlistFileName,
    ScriptName,
    CreatedDate,
    ScheduleType,
    ScheduleValue,
    CurrentState,
    Description,
    PlistFileContent
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?);
"""


PLISTFILES_COUNT_ALL_ROWS = "SELECT COUNT(*) FROM PlistFiles"
PLISTFILES_SET_CURRENT_STATE_RUNNING = (
    "UPDATE PlistFiles SET CurrentState = 'running' WHERE PlistFileID = ?"
)
PLISTFILES_SET_CURRENT_STATE_INACTIVE = (
    "UPDATE PlistFiles SET CurrentState = 'inactive' WHERE PlistFileID = ?"
)
PLISTFILES_GET_INSTALL_STATUS = (
    "SELECT CurrentState FROM  PlistFiles WHERE plistFileId = ?"
)
PLISTFILES_SELECT_ALL = "SELECT * FROM PlistFiles"
PLISTFILES_SELECT_SINGLE_PLIST_FILE = "SELECT * FROM  PlistFiles WHERE plistFileId = ?"
PLISTFILES_SELECT_ALL_FIELDS_FOR_LIST_COMMAND = (
    "SELECT PlistFileID, PlistFileName, ScriptName, CreatedDate, "
    "ScheduleType, ScheduleValue, CurrentState FROM PlistFiles"
    " ORDER BY PlistFileID"
)
