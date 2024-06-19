Launchd is a macOS terminal utility that runs scripts on a schedule.

Launchd Me makes the process a simple CLI command.

`launchd-me your_script.py calendar {Hour: 1}`

## Installation

`pip install launchd-me`

Use the awesome [pipx](https://github.com/pypa/pipx) to make Launchd Me available
system wide. (More here.)

`pipx install launchd-me`

## What does Launchd Me do?

It generates

Launchd requires a `.plist` file



The main command is `launchd-me`

I have a script `clean_downloads.py`








## More on Launchd


Or, as [Apple](https://support.apple.com/en-gb/guide/terminal/apdc6c1077b-5d5d-4d35-9c19-60f2397b2369/mac)
puts it:

>  The launchd process is used by macOS to manage daemons and agents, and you can use it
to run your shell scripts.

You can easily use it to run Python, JavaScript

## More on Launchd


## Who am I?

I'm this guy. I currently an apprentice software developer at the Met Office in the UK. This is my first ever actually completed project.


## Why not use a cron job?

Launchd is the macOS recommended alternative for cron jobs. See [Apple - "The preferred way to add a timed job is to use launchd"]([text](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html#//apple_ref/doc/uid/10000172i-CH1-SW2))



## Pip X


Install pipx with Homebrew from yor terminal with [three commands](https://github.com/pypa/pipx#on-macos).


[text](https://pythonbytes.fm/episodes/transcript/377/a-dramatic-episode#play-at)

## Useful Links

* [Launchd man page (opens the terminal)](x-man-page://launchd.plist) - or just run
`man launchd` in your terminal.
* [Launchd.info](https://launchd.info/) - an extensive third-party resource
* [Reddit - cron or launchd](https://www.reddit.com/r/MacOS/comments/13r469w/cron_or_launchd/)
* [Apple - "The preferred way to add a timed job is to use launchd"]([text](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html#//apple_ref/doc/uid/10000172i-CH1-SW2))
