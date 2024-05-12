import argparse

import launchd_me

def get_args():
    """Get command line args.
    
    Maybe something like:
        
    `launchd-me create hello.py interval 300`
    `launchd-me list`
    `launchd-me install`
    `launchd-me uninstall`
    `launchd-me show`
    """
    parser = argparse.ArgumentParser(
        prog="ldm",
        description="Create and manage plist files."
        )
    subparsers = parser.add_subparsers(required=True)
    
    parser_create = subparsers.add_parser("create", help="Create a plist file from a given script.")
    parser_create.add_argument("script_path", help="path to the script to automate.")
    parser_create.add_argument("schedule_type", choices=["interval", "calendar"], help="schedule_type. 'interval' schedules are defined seconds. 'calendar' schedules are defined usings times, days, weeks etc. See Documentation for more details.")
    parser_create.add_argument("schedule_details", help="How often the script is run. E.g. `300` for 'interval'. ")
    parser_create.add_argument("-a", "--auto-install", default=True, help="Automatically load the plist file once created. Defaults to True.")
    parser_create.add_argument("-m", "--make-executable", default=True, help="Check if the specified script is already an executable and, if it is not, make it exectuable. Defaults to True.")

    parser_list = subparsers.add_parser("list", help="List all tracked plist files.")
    parser_list.add_argument("plist_id", help="Display details of given plist file.")      
        
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    # plc = launchd_me.PlistCreator("hello.py", launchd_me.ScheduleType.interval, 300)
    # my_list = [
    #     plc.script_name, 
    #     plc.schedule_type, 
    #     plc.schedule, 
    #     plc.template_path,
    #     # plc.project_dir, 
    #     # plc.plist_dir, 
    #     plc.plist_file_name, 
    #     ]
    # for x in my_list:
    #     print(x)
