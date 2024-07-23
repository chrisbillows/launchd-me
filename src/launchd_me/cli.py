import argparse
import shutil
from pathlib import Path

from launchd_me.logger_config import logger
from launchd_me.plist import (
    DbDisplayer,
    LaunchdMeInit,
    PlistCreator,
    PlistDbGetters,
    PlistDbSetters,
    PlistFileIDNotFound,
    PlistInstallationManager,
    UserConfig,
)

USER_CONFIG = UserConfig()
LOGO_ART = """
 ___       _______   __   __   __    _   _______   __   __   ______      __   __   _______   __
|   |     |   _   | |  | |  | |  |  | | |       | |  | |  | |      |    |  |_|  | |       | |  |
|   |     |  |_|  | |  | |  | |   |_| | |       | |  |_|  | |  _    |   |       | |    ___| |  |
|   |     |       | |  |_|  | |       | |       | |       | | | |   |   |       | |   |___  |  |
|   |___  |       | |       | |  _    | |      _| |       | | |_|   |   |       | |    ___| |__|
|       | |   _   | |       | | | |   | |     |_  |   _   | |       |   | ||_|| | |   |___   __
|_______| |__| |__| |_______| |_|  |__| |_______| |__| |__| |______|    |_|   |_| |_______| |__|
"""
LOGO_DIVIDER = "=" * 96
LOGO_TEXT = "Easily schedule your scripts on macOS!".center(96, " ")
LOGO = f"{LOGO_ART}\n{LOGO_DIVIDER}\n{LOGO_TEXT}\n{LOGO_DIVIDER}\n\n"
CLI_TEXT = {
    "PARSER": {"DESCRIPTION": "Easily schedule your scripts on macOS."},
    "SUBPARSER": {
        "TITLE": "subcommands",
        "DESCRIPTION": "",
    },
    "COMMANDS": {
        "CREATE": {
            "DESCRIPTION": "Create a plist file to schedule a given script.",
            "HELP": "create a plist file to schedule a given script.",
            "ARGS": {
                "SCRIPT_PATH_HELP": "path to the script to schedule.",
                "SCHEDULE_TYPE_HELP": """schedule_type. An 'interval' schedule requires seconds e.g. 300. A 'calendar'
                                         schedules require a dictionary of fields e.g. {'Weekday': 1, 'Hour': 8}.
                                         Allowed fields are: 'Minute', 'Hour', 'Day', 'Weekday', 'Month'. See the
                                         documentation for more details.""",
                "SCHEDULE_DETAILS_HELP": "schedule for running the script e.g. 300 or {'Weekday': 1, 'Hour': 8}.",
                "DESCRIPTION_HELP": "description of what you're automating e.g. daily downloads tidy.",
                "MAKE_EXECUTABLE_HELP": "ensure the specified script is executable. defaults to true.",
                "AUTO_INSTALL_HELP": "load the plist file to schedule the script automatically. defaults to true",
            },
        },
        "LIST": {
            "DESCRIPTION": "List all tracked plist files or show a given plist_id.",
            "HELP": "list all tracked plist files or show a given plist_id",
            "ARGS": {"PLIST_ID_HELP": "display details of plist_id"},
        },
        "INSTALL": {
            "DESCRIPTION": "Install a given plist file.",
            "HELP": "install a given plist file",
            "ARGS": {"PLIST_ID_HELP": "the plist file to install"},
        },
        "UNINSTALL": {
            "DESCRIPTION": "Uninstall a given plist file.",
            "HELP": "uninstall a given plist file",
            "ARGS": {"PLIST_ID_HELP": "the plist file to un-install"},
        },
        "RESET": {
            "DESCRIPTION": "Delete the current db and plist directory. Currently does not unload or delete existing plist symlinks.",
            "HELP": "delete the current db and plist directory. currently does not unload or delete existing plist symlinks",
        },
    },
}


def valid_path(path_str: str) -> Path:
    """Check a string is a valid file path and convert it to a pathlib.Path.

    Attributes
    ----------
    path_str: str
        A string representing a path to a file.

    Returns
    -------
    Path
        The string as a Pathlib path.

    Raises
    ------
    argparse.ArgumentTypeError
        If the passed string is not a path to a file.
    """
    path = Path(path_str).resolve()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"Invalid file path: '{path_str}'")
    return path


class CLIArgumentParser:
    """A class to create and manage the CLI parser for the launchd_me tool.

    Attributes
    ----------
    parser : argparse.ArgumentParser
        The main argument parser for the CLI.
    subparsers : _SubParsersAction
        The subparsers for different CLI commands.

    Methods
    -------
    create_parser: argparse.ArgumentParser
        Creates and returns the main argument parser with all subcommands.
    """

    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser(
            prog="ldm",
            description=LOGO,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        self.parser.set_defaults(func=self._default_action)
        self.subparsers = self.parser.add_subparsers(
            title=CLI_TEXT["SUBPARSER"]["TITLE"],
            description=CLI_TEXT["SUBPARSER"]["DESCRIPTION"],
        )

    def create_parser(self) -> argparse.ArgumentParser:
        """Add subcommands to the main argument parser.

        Returns
        -------
        argparse.ArgumentParser
            The configured argument parser with all subcommands added.
        """
        self._add_create_command()
        self._add_list_command()
        self._add_install_command()
        self._add_uninstall_command()
        self._add_reset_command()
        return self.parser

    def _default_action(self, args: argparse.Namespace) -> None:
        """The default action to execute when no subcommand is provided.

        This method is called when the user does not provide any subcommand. It prints
        an error message and displays the help message for the main parser.

        Parameters
        ----------
        args : argparse.Namespace
            The arguments passed to the command-line interface.
        """
        print("ERROR: ldm requires a command. See the help below...\n")
        self.parser.print_help()

    def _add_create_command(self) -> None:
        """Add the 'create' subcommand to the argument parser.

        This method configures the 'create' subcommand, which allows users to create a
        plist file to schedule a given script. It sets the default function to be called
        when this subcommand is used and defines the necessary arguments for the
        subcommand.

        The 'create' subcommand includes the following arguments:
        - script_path: The path to the script to schedule.
        - schedule_type: The type of schedule ('interval' or 'calendar').
        - schedule_details: The details of the schedule (e.g., interval in seconds or a
          dictionary for calendar).
        - description: A description of what is being automated.
        - make_executable: A flag to ensure the specified script is executable (defaults
          to True).
        - auto_install: A flag to automatically load the plist file to schedule the
          script (defaults to True).
        """
        parser_create = self.subparsers.add_parser(
            "create",
            help=CLI_TEXT["COMMANDS"]["CREATE"]["HELP"],
            description=CLI_TEXT["COMMANDS"]["CREATE"]["DESCRIPTION"],
        )
        parser_create.set_defaults(func=create_plist)
        parser_create.add_argument(
            "script_path",
            type=valid_path,
            help=CLI_TEXT["COMMANDS"]["CREATE"]["ARGS"]["SCRIPT_PATH_HELP"],
        )
        parser_create.add_argument(
            "schedule_type",
            choices=["interval", "calendar"],
            help=CLI_TEXT["COMMANDS"]["CREATE"]["ARGS"]["SCHEDULE_TYPE_HELP"],
        )
        parser_create.add_argument(
            "schedule_details",
            type=int,
            help=CLI_TEXT["COMMANDS"]["CREATE"]["ARGS"]["SCHEDULE_DETAILS_HELP"],
        )
        parser_create.add_argument(
            "description",
            type=str,
            help=CLI_TEXT["COMMANDS"]["CREATE"]["ARGS"]["DESCRIPTION_HELP"],
        )
        parser_create.add_argument(
            "-m",
            "--make-executable",
            default=True,
            type=bool,
            help=CLI_TEXT["COMMANDS"]["CREATE"]["ARGS"]["MAKE_EXECUTABLE_HELP"],
        )
        parser_create.add_argument(
            "-a",
            "--auto-install",
            default=True,
            type=bool,
            help=CLI_TEXT["COMMANDS"]["CREATE"]["ARGS"]["AUTO_INSTALL_HELP"],
        )

    def _add_list_command(self) -> None:
        """Add the 'list' subcommand to the argument parser.

        This method configures the 'list' subcommand, which allows users to list all
        tracked plist files or show details of a specific plist file by its ID. It sets
        the default function to be called when this subcommand is used and defines the
        necessary arguments for the subcommand.

        The 'list' subcommand includes the following argument:
        - plist_id: An optional ID of the plist file to display details for.
        """
        parser_list = self.subparsers.add_parser(
            "list",
            description=CLI_TEXT["COMMANDS"]["LIST"]["DESCRIPTION"],
            help=CLI_TEXT["COMMANDS"]["LIST"]["HELP"],
        )
        parser_list.set_defaults(func=list_plists)
        parser_list.add_argument(
            "plist_id",
            type=int,
            nargs="?",
            help=CLI_TEXT["COMMANDS"]["LIST"]["ARGS"]["PLIST_ID_HELP"],
        )

    def _add_install_command(self) -> None:
        """Add the 'install' subcommand to the argument parser.

        This method configures the 'install' subcommand, which allows users to install
        a given plist file. It sets the default function to be called when this
        subcommand is used and defines the necessary argument for the subcommand.

        The 'install' subcommand includes the following argument:
        - plist_id: The ID of the plist file to install.
        """
        parser_install = self.subparsers.add_parser(
            "install",
            description=CLI_TEXT["COMMANDS"]["INSTALL"]["DESCRIPTION"],
            help=CLI_TEXT["COMMANDS"]["INSTALL"]["HELP"],
        )
        parser_install.set_defaults(func=install_plist)
        parser_install.add_argument(
            "plist_id", help=CLI_TEXT["COMMANDS"]["INSTALL"]["ARGS"]["PLIST_ID_HELP"]
        )

    def _add_uninstall_command(self) -> None:
        """Add the 'uninstall' subcommand to the argument parser.

        This method configures the 'uninstall' subcommand, which allows users to
        uninstall a given plist file. It sets the default function to be called when
        this subcommand is used and defines the necessary argument for the subcommand.

        The 'uninstall' subcommand includes the following argument:
        - plist_id: The ID of the plist file to uninstall.
        """
        parser_uninstall = self.subparsers.add_parser(
            "uninstall",
            description=CLI_TEXT["COMMANDS"]["UNINSTALL"]["DESCRIPTION"],
            help=CLI_TEXT["COMMANDS"]["UNINSTALL"]["HELP"],
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser_uninstall.set_defaults(func=uninstall_plist)
        parser_uninstall.add_argument("plist_id", help="The plist to un-install")

    def _add_reset_command(self) -> None:
        """Add the 'reset' subcommand to the argument parser.

        This method configures the 'reset' subcommand, which allows users to delete the
        current database and plist directory. It sets the default function to be called
        when this subcommand is used.
        """
        parser_reset = self.subparsers.add_parser(
            "reset",
            description=CLI_TEXT["COMMANDS"]["RESET"]["DESCRIPTION"],
            help=CLI_TEXT["COMMANDS"]["RESET"]["HELP"],
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser_reset.set_defaults(func=reset_user)


def create_plist(args: argparse.Namespace) -> None:
    """Create a plist file to schedule a given script.

    This function is called when the 'create' subcommand is used. It initializes a
    PlistCreator instance with the provided arguments and calls its driver method to
    create the plist file.

    Parameters
    ----------
    args : argparse.Namespace
        The arguments passed to the 'create' subcommand. Expected attributes are:
        - script_path: Path to the script to schedule.
        - schedule_type: Type of schedule ('interval' or 'calendar').
        - schedule_details: Details of the schedule (e.g., interval in seconds or a
          dictionary for calendar).
        - description: Description of what is being automated.
        - make_executable: Flag to ensure the specified script is executable.
        - auto_install: Flag to automatically load the plist file to schedule the script.
    """
    logger.debug("Instantiating PlistCreator.")
    plc = PlistCreator(
        args.script_path,
        args.schedule_type,
        args.schedule_details,
        args.description,
        args.make_executable,
        args.auto_install,
        USER_CONFIG,
    )
    logger.debug("Calling PlistCreator.driver()")
    plc.driver()


def list_plists(args: argparse.Namespace) -> None:
    """List all tracked plist files or shows details of a specific plist file by its ID.

    This function is called when the 'list' subcommand is used. It retrieves and
    displays information about plist files from the database. If a plist ID is provided,
    it shows details for that specific plist file. Otherwise, it lists all tracked plist
    files.

    Parameters
    ----------
    args : argparse.Namespace
        The arguments passed to the 'list' subcommand. Expected attributes are:
        - plist_id: An optional ID of the plist file to display details for.
    """
    db_getters = PlistDbGetters(USER_CONFIG)
    if args.plist_id:
        logger.debug("Displaying a single plist file detail.")
        db_displayer = DbDisplayer(USER_CONFIG)
        row = db_getters.get_a_single_plist_file_details(args.plist_id)
        db_displayer.display_single_plist_file_detail_table(row)
    else:
        logger.debug("Displaying all plist files.")
        all_rows = db_getters.get_all_tracked_plist_files()
        db_all_rows_displayer = DbDisplayer(USER_CONFIG)
        db_all_rows_displayer.display_all_tracked_plist_files_table(all_rows)


def install_plist(args: argparse.Namespace) -> None:
    """Install a given plist file.

    This function is called when the 'install' subcommand is used. It verifies the
    provided plist ID, retrieves the plist file details, and installs the plist file
    using the PlistInstallationManager.

    Parameters
    ----------
    args : argparse.Namespace
        The arguments passed to the 'install' subcommand. Expected attributes are:
        - plist_id: The ID of the plist file to install.
    """
    db_getter = PlistDbGetters(USER_CONFIG)
    db_setter = PlistDbSetters(USER_CONFIG)
    install_manager = PlistInstallationManager(USER_CONFIG, db_setter)
    db_getter.verify_a_plist_id_is_valid(args.plist_id)
    plist_detail = db_getter.get_a_single_plist_file_details(args.plist_id)
    plist_filename = Path(plist_detail["PlistFileName"])
    plist_file_path = Path(USER_CONFIG.plist_dir) / plist_filename
    install_manager.install_plist(args.plist_id, plist_file_path)


def uninstall_plist(args: argparse.Namespace) -> None:
    """Uninstall a given plist file.

    This function is called when the 'uninstall' subcommand is used. It verifies the
    provided plist ID, retrieves the plist file details, and uninstalls the plist file
    using the PlistInstallationManager.

    Parameters
    ----------
    args : argparse.Namespace
        The arguments passed to the 'uninstall' subcommand. Expected attributes are:
        - plist_id: The ID of the plist file to uninstall.
    """
    db_getter = PlistDbGetters(USER_CONFIG)
    db_setter = PlistDbSetters(USER_CONFIG)
    install_manager = PlistInstallationManager(USER_CONFIG, db_setter)
    db_getter.verify_a_plist_id_is_valid(args.plist_id)
    plist_detail = db_getter.get_a_single_plist_file_details(args.plist_id)
    plist_file_name = Path(plist_detail["PlistFileName"])
    symlink_to_plist = USER_CONFIG.launch_agents_dir / plist_file_name
    install_manager.uninstall_plist(args.plist_id, symlink_to_plist)


def reset_user(args: argparse.Namespace) -> None:
    """Delete the current database and plist directory.

    This function is called when the 'reset' subcommand is used. It fetches the project
    directory from the user configuration and deletes it along with all its contents.

    Parameters
    ----------
    args : argparse.Namespace
        The arguments passed to the 'reset' subcommand. This function does not expect
        any specific attributes in the args.
    """
    logger.debug("Fetching the project directory")
    project_dir = USER_CONFIG.project_dir
    logger.debug(f"Project directory: {project_dir}")
    logger.debug(f"Deleting: {project_dir}")
    shutil.rmtree(project_dir)
    logger.debug("Project directory and contents deleted")


def main() -> None:
    """The main entry point for the launchd_me CLI tool.

    This function initializes the user configuration and the launchd_me environment,
    creates the argument parser with all subcommands, parses the command-line arguments,
    and executes the appropriate function based on the provided subcommand.

    If an invalid plist ID is provided, it catches the PlistFileIDNotFound exception
    and prints the error message.
    """
    user_config = UserConfig()
    ldm = LaunchdMeInit(user_config)
    ldm.initialise_launchd_me()
    parser_creator = CLIArgumentParser()
    parser = parser_creator.create_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except PlistFileIDNotFound as error:
        print(error)
