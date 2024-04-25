from launchd_me.plist_creator import PlistCreator, ScheduleType

def main():
    plc = PlistCreator("hello.py", ScheduleType.interval, 300)
    my_list = [
        plc.script_name, 
        plc.schedule_type, 
        plc.schedule, 
        plc.template_path,
        plc.project_dir, 
        plc.plist_dir, 
        plc.plist_file_name, 
        ]
    for x in my_list:
        print(x)

if __name__ == "__main__":
    main()
