import argparse
from pathlib import Path

from launchd_me.logger_config import logger
from launchd_me.plist import (
    LaunchdMeInit,
    PlistCreator,
    PlistDbGetters,
    PlistInstaller,
    ScheduleType,
    UserConfig,
)


def valid_path(path_str):
    """Check if the path is a valid file path and convert it to pathlib.Path."""
    path = Path(path_str).resolve()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"Invalid file path: '{path_str}'")
    return path


def get_args():
    """Get command line args."""
    parser = argparse.ArgumentParser(
        prog="ldm", description="Create and manage plist files."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_create = subparsers.add_parser(
        "create", help="Create a plist file from a given script."
    )
    parser_list = subparsers.add_parser("list", help="List all tracked plist files.")
    parser_install = subparsers.add_parser(
        "install", help="Install a given plist file."
    )
    parser_uninstall = subparsers.add_parser(
        "uninstall", help="Uninstall a given plist file."
    )
    parser_show = subparsers.add_parser("show", help="Show a given plist file.")

    parser_create.add_argument(
        "script_path", type=valid_path, help="path to the script to automate."
    )
    parser_create.add_argument(
        "schedule_type",
        choices=["interval", "calendar"],
        help="""schedule_type. 'interval' schedules are defined seconds
                . 'calendar' schedules are defined usings times, days,
                weeks etc. See Documentation for more details.""",
    )
    parser_create.add_argument(
        "schedule_details",
        type=int,
        help="How often the script is run. E.g. `300` for 'interval'. ",
    )
    parser_create.add_argument(
        "description",
        type=str,
        help="A description of what you're automating. Enter x if you're just going to remember. Ha ha.",
    )
    parser_create.add_argument(
        "-m",
        "--make-executable",
        default=True,
        type=bool,
        help="""Ensure the specified script is executable. Defaults to
                True.""",
    )
    parser_create.add_argument(
        "-a",
        "--auto-install",
        default=True,
        type=bool,
        help="Automatically load the plist file into OSX once created. Defaults to True.",
    )
    parser_list.add_argument(
        "-p", "--plist-id", help="Display details of given plist file."
    )
    parser_install.add_argument("plist-id", help="The plist id install.")
    parser_uninstall.add_argument("plist-id", help="The plist to un-install.")
    parser_show.add_argument("plist-id", help="The plist to display.")
    args = parser.parse_args()
    return args


def create_plist(args):
    # So PlistCreator generates the plist, does the install, does the execute, returns
    # the final thing and updates the db.  It's simpler to have all that logic in one
    # function to avoid having to PASS it around in partial state.
    # i.e. we'd have the file generated but no id yet etc.
    logger.debug("Instantiating PlistCreator.")
    plc = PlistCreator(
        args.script_path,
        args.schedule_type,
        args.schedule_details,
        args.description,
        args.make_executable,
        args.auto_install,
    )
    logger.debug("Calling PlistCreator.driver()")
    plc.driver()


def list_plists(args):
    if args.plist_id:
        print(f"Listing details for plist id: {args.plist_id}")
    else:
        logger.debug("Calling 'display_all_tracked_plist_files().")
        db_getter = PlistDbGetters()
        db_getter.display_all_tracked_plist_files()


def install_plist(args):
    print(f"Installing plist id: {args.plist_id}")


def uninstall_plist(args):
    print(f"Uninstalling plist id: {args.plist_id}")


def show_plist(args):
    print(f"Showing plist id: {args.plist_id}")


def main():
    user_config = UserConfig()
    ldm = LaunchdMeInit(user_config)
    ldm.initialise_launchd_me()
    args = get_args()
    command_dispatcher = {
        "create": create_plist,
        "list": list_plists,
        "install": install_plist,
        "uninstall": uninstall_plist,
        "show": show_plist,
    }
    command = args.command
    if command in command_dispatcher:
        command_dispatcher[command](args)
    else:
        print(f"Unknown command: {command}")
