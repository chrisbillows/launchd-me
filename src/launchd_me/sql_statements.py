PLISTFILES_TABLE_INSERT_INTO = """
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

PLISTFILES_TABLE_SELECT_ALL = "SELECT * FROM PlistFiles"
