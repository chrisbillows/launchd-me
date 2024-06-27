INSERT_INTO_PLISTFILES_TABLE = """
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
