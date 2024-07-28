CREATE_TABLE_PLIST_FILES = """
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

PLISTFILES_TABLE_INSERT_INTO = """
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

PLISTFILES_TABLE_SELECT_ALL = "SELECT * FROM PlistFiles"
PLISTFILES_TABLE_SELECT_SINGLE_PLIST_FILE = (
    "SELECT * FROM  PlistFiles WHERE plistFileId = ?"
)

PLISTFILES_TABLE_GET_INSTALL_STATUS = (
    "SELECT CurrentState FROM  PlistFiles WHERE plistFileId = ?"
)
