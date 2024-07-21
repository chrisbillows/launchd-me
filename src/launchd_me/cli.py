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
LOGO = """
 ___      _______  __   __  __    _  _______  __   __  ______     __   __  _______  __ 
|   |    |   _   ||  | |  ||  |  | ||       ||  | |  ||      |   |  |_|  ||       ||  |
|   |    |  |_|  ||  | |  ||   |_| ||       ||  |_|  ||  _    |  |       ||    ___||  |
|   |    |       ||  |_|  ||       ||       ||       || | |   |  |       ||   |___ |  |
|   |___ |       ||       ||  _    ||      _||       || |_|   |  |       ||    ___||__|
|       ||   _   ||       || | |   ||     |_ |   _   ||       |  | ||_|| ||   |___  __ 
|_______||__| |__||_______||_|  |__||_______||__| |__||______|   |_|   |_||_______||__|
"""
CLI_TEXT = {
    "PARSER": {
        "DESCRIPTION": "Easily schedule your scripts on macOS."
        },
    "SUBPARSER": {
        "TITLE": "subcommands",
        "DESCRIPTION": "",
        },
        "COMMANDS": {
            "CREATE": {
                "HELP": "Create a plist file to schedule a given script.",
                "ARGS": {
                    "SCRIPT_PATH_HELP": "path to the script to schedule.",
                    "SCHEDULE_TYPE_HELP": """schedule_type. An 'interval' schedule requires seconds e.g. 300. A 'calendar'  
                                             schedules require a dictionary of fields e.g. {'Weekday': 1, 'Hour': 8}.
                                             Allowed fields are: 'Minute', 'Hour', 'Day', 'Weekday', 'Month'. See the 
                                             documentation for more details.""",
                    "SCHEDULE_DETAILS_HELP": "schedule for running the script e.g. 300 or {'Weekday': 1, 'Hour': 8}.",
                    "DESCRIPTION_HELP": "description of what you're automating e.g. daily downloads tidy.",
                    "MAKE_EXECUTABLE_HELP": "ensure the specified script is executable. defaults to true.",
                    "AUTO_INSTALL_HELP": "load the plist/schedule the script automatically. defaults to true",
                },
            },
            "LIST": {
                "DESCRIPTION": "List all tracked plist files or show a given [plist_id]",
                "HELP": "list all tracked plist files or show a given [plist_id]",
                "ARGS": {"PLIST_ID_HELP": "display details of [plist_id]"},
            },
            "INSTALL": {
                "DESCRIPTION": "Install a given plist file.",
                "HELP": "install a given plist file",
                "ARGS": {
                    "PLIST_ID_HELP": "the plist file to install"
                }
            },
            "UNINSTALL": {
                "HELP": "uninstall a given plist file",
                "ARGS": {
                    "PLIST_ID_HELP": "the plist file to un-install"
                        }
            },
            "RESET": {
                "HELP": "delete the current db and plist directory. currently does not unload or delete existing plist symlinks"
            }
        },
    }


def valid_path(path_str: str) -> Path:
    """Check if the path is a valid file path and convert it to pathlib.Path."""
    path = Path(path_str).resolve()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"Invalid file path: '{path_str}'")
    return path


class ParserCreator:
    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser(
            prog="ldm", description=CLI_TEXT["PARSER"]["DESCRIPTION"]
        )
        self.parser.set_defaults(func=self._default_action)
        self.subparsers = self.parser.add_subparsers(
            title=CLI_TEXT["SUBPARSER"]["TITLE"], 
            description=CLI_TEXT["SUBPARSER"]["DESCRIPTION"],
        )

    def create_parser(self) -> argparse.ArgumentParser:
        self._add_create_command()
        self._add_list_command()
        self._add_install_command()
        self._add_uninstall_command()
        self._add_reset_command()
        return self.parser
    
    def _default_action(self, args: argparse.Namespace) -> None:
        print("ERROR: ldm requires a command. See the help below...\n")
        self.parser.print_help()

    def _add_create_command(self) -> None:
        parser_create = self.subparsers.add_parser(
            "create", 
            help=CLI_TEXT["COMMANDS"]["CREATE"]["HELP"]
            )
        parser_create.set_defaults(func=create_plist)
        parser_create.add_argument(
            "script_path", 
            type=valid_path, 
            help=CLI_TEXT["COMMANDS"]["CREATE"]["ARGS"]["SCRIPT_PATH_HELP"]
        )
        parser_create.add_argument(
            "schedule_type",
            choices=["interval", "calendar"],
            help=CLI_TEXT["COMMANDS"]["CREATE"]["ARGS"]["SCHEDULE_TYPE_HELP"]
        )
        parser_create.add_argument(
            "schedule_details", 
            type=int, 
            help=CLI_TEXT["COMMANDS"]["CREATE"]["ARGS"]["SCHEDULE_DETAILS_HELP"]
        )
        parser_create.add_argument(
            "description", 
            type=str, 
            help=CLI_TEXT["COMMANDS"]["CREATE"]["ARGS"]["DESCRIPTION_HELP"]
        )
        parser_create.add_argument(
            "-m",
            "--make-executable",
            default=True,
            type=bool,
            help=CLI_TEXT["COMMANDS"]["CREATE"]["ARGS"]["MAKE_EXECUTABLE_HELP"]
        )
        parser_create.add_argument(
            "-a", 
            "--auto-install", 
            default=True, 
            type=bool, 
            help=CLI_TEXT["COMMANDS"]["CREATE"]["ARGS"]["AUTO_INSTALL_HELP"]
        )

    def _add_list_command(self) -> None:
        parser_list = self.subparsers.add_parser(
            "list", 
            description=CLI_TEXT["COMMANDS"]["LIST"]["DESCRIPTION"], 
            help=CLI_TEXT["COMMANDS"]["LIST"]["HELP"]
        )
        parser_list.set_defaults(func=list_plists)
        parser_list.add_argument(
            "plist_id", 
            type=int, 
            nargs="?", 
            help=CLI_TEXT["COMMANDS"]["LIST"]["ARGS"]["PLIST_ID_HELP"]
        )

    def _add_install_command(self) -> None:
        parser_install = self.subparsers.add_parser(
            "install", 
            help=CLI_TEXT["COMMANDS"]["INSTALL"]["HELP"]
        )
        parser_install.set_defaults(func=install_plist)
        parser_install.add_argument(
            "plist_id", 
            help="The plist id install")

    def _add_uninstall_command(self) -> None:
        parser_uninstall = self.subparsers.add_parser(
            "uninstall", 
            help=CLI_TEXT["COMMANDS"]["UNINSTALL"]["HELP"]
        )
        parser_uninstall.set_defaults(func=uninstall_plist)
        parser_uninstall.add_argument(
            "plist_id", 
            help="The plist to un-install")

    def _add_reset_command(self) -> None:
        parser_reset = self.subparsers.add_parser(
            "reset",
            help=CLI_TEXT["COMMANDS"]["RESET"]["HELP"]
        )
        parser_reset.set_defaults(func=reset_user)


def create_plist(args: argparse.Namespace) -> None:
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
    db_getter = PlistDbGetters(USER_CONFIG)
    db_setter = PlistDbSetters(USER_CONFIG)
    install_manager = PlistInstallationManager(USER_CONFIG, db_setter)
    db_getter.verify_a_plist_id_is_valid(args.plist_id)
    plist_detail = db_getter.get_a_single_plist_file_details(args.plist_id)
    plist_filename = Path(plist_detail["PlistFileName"])
    plist_file_path = Path(USER_CONFIG.plist_dir) / plist_filename
    install_manager.install_plist(args.plist_id, plist_file_path)


def uninstall_plist(args: argparse.Namespace) -> None:
    """Uninstall a plist file.

    A single plist file argument is required. This is checked for existence in the
    database.

    The detail of the given plist file is extracted and the name of the plist file is
    extracted - this is the same name as the symlink created in the installation step.

    The plist file name is combined with the user's launch agents dir and then the
    uninstall command is called.

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
    logger.debug("Fetching the project directory")
    project_dir = USER_CONFIG.project_dir
    logger.debug(f"Project directory: {project_dir}")
    logger.debug(f"Deleting: {project_dir}")
    shutil.rmtree(project_dir)
    logger.debug("Project directory and contents deleted")


def main():
    user_config = UserConfig()
    ldm = LaunchdMeInit(user_config)
    ldm.initialise_launchd_me()
    parser_creator = ParserCreator()
    parser = parser_creator.create_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except PlistFileIDNotFound as error:
            print(error)
