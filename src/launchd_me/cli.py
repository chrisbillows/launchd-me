import argparse

import launchd_me

def get_args():
    parser = argparse.ArgumentParser(
        prog="Launchd-me",
        description="Create and manage plist files."
        )
    parser.add_argument("Script")
    parser.add_argument("ScheduleType")
    parser.add_argument("Schedule")
    args = parser.parse_args()
    return args


def main():
    print("Main is running")
    
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
