import launchd_me

def main():
    plc = launchd_me.PlistCreator("hello.py", launchd_me.ScheduleType.interval, 300)
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
    print("cli.py is __name__")
