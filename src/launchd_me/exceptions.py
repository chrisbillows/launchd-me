"""A module containing exceptions used in Launchd Me."""


class InvalidScheduleType(Exception):
    pass


class PlistFileIDNotFound(Exception):
    pass


class UnexpectedInstallationStatus(Exception):
    """User expected a status of True when it's False, or False when it's True."""

    pass
