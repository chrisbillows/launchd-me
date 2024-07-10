import argparse
import shutil
from pathlib import Path

from launchd_me.logger_config import logger
from launchd_me.plist import (
    DbAllRowsDisplayer,
    DbPlistDetailDisplayer,
    LaunchdMeInit,
    PlistCreator,
    PlistDbGetters,
    PlistDbSetters,
    PlistFileIDNotFound,
    PlistInstallationManager,
    ScheduleType,
    UserConfig,
)

USER_CONFIG = UserConfig()


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

    parser_list = subparsers.add_parser("list", help="List all tracked plist files.")
    parser_list.add_argument(
        "-p", "--plist-id", type=int, help="Display details of given plist file."
    )

    parser_install = subparsers.add_parser(
        "install", help="Install a given plist file."
    )
    parser_install.add_argument("plist_id", help="The plist id install.")

    parser_uninstall = subparsers.add_parser(
        "uninstall", help="Uninstall a given plist file."
    )
    parser_uninstall.add_argument("plist_id", help="The plist to un-install.")

    parser_show = subparsers.add_parser("show", help="Show a given plist file.")
    parser_show.add_argument("plist_id", help="The plist to display.")

    parser_reset = subparsers.add_parser(
        "reset",
        help="Delete the current db and plist directory. NOTE: Currently does not "
        "unload or delete existing plist symlinks.",
    )

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
        USER_CONFIG,
    )
    logger.debug("Calling PlistCreator.driver()")
    plc.driver()


def list_plists(args):
    db_getters = PlistDbGetters(USER_CONFIG)
    if args.plist_id:
        db_plist_displayer = DbPlistDetailDisplayer()
        row = db_getters.get_a_single_plist_file_details(args.plist_id)
        db_plist_displayer.display_plist_detail(row)
    else:
        logger.debug("Calling 'display_all_tracked_plist_files().")
        all_rows = db_getters.get_all_tracked_plist_files()
        db_all_rows_displayer = DbAllRowsDisplayer()
        db_all_rows_displayer.display_all_rows_table(all_rows)


def install_plist(args):
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


def reset_user(args: argparse.Namespace):
    user_conf = UserConfig()
    logger.debug("Fetching the project directory")
    project_dir = user_conf.project_dir
    logger.debug(f"Project directory: {project_dir}")
    logger.debug(f"Deleting: {project_dir}")
    shutil.rmtree(project_dir)
    logger.debug("Project directory and contents deleted")


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
        "reset": reset_user,
    }
    command = args.command
    try:
        if command in command_dispatcher:
            command_dispatcher[command](args)
        else:
            print(f"Unknown command: {command}")
    except PlistFileIDNotFound as error:
        print(error)
