# Scheduling a script


```
launchd-me <script_to_automate> <schedule_type> <schedule>
```
### Script to automate

This is the script you want to automate.



## Examples

To run a c to run `your_script.py` once every hour you'd run:

```
launchd-me your_script.py calendar {Hour: 1}
```

#



This command does the following:

1. A `plist` file for your script.
1. The `plist` file is customised for `your_script.py` and your schedule.
1. The `plist` file is verified w   ith `plutil -lint`
1. `your_script.py` was made an executable (if it wasn't already)
1. A symlink to `plist` file was created in `User/Library/LaunchAgents`
    - This means the `plist` will automatically load on restart
1. The script was loaded for operation now with the `launchctl load`

Incidentally, this is a workflow for creating these scripts yourself. You can just copy
the template
