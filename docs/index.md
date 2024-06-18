# Introduction

Easily create and manage automation scripts on macOS using Apple's launchd utility.


## What is Launchd?

Launchd runs scripts on a schedule. Launchd is Apple's alternative to cron jobs.

Launchd Me makes the process a simple CLI command.

`launchd-me my_hourly_script.py {Hour: 1}`

LaunchdMe



## Installation

`pip install launchd-me`

Consider using the awesome [pipx]([text](https://github.com/pypa/pipx)) to make any
Python CLI package available system wide.

Install pipx with Homebrew from yor terminal with [three commands](https://github.com/pypa/pipx#on-macos).

`



[text](https://pythonbytes.fm/episodes/transcript/377/a-dramatic-episode#play-at)

## Basic Usage

Once a week I want to run `delete_rick_astley_videos.py`.



#


Or, as [Apple](https://support.apple.com/en-gb/guide/terminal/apdc6c1077b-5d5d-4d35-9c19-60f2397b2369/mac)
puts it:

>  The launchd process is used by macOS to manage daemons and agents, and you can use it
to run your shell scripts.

You can easily use it to run Python, JavaScript

## What is Launchd Me




## Why not use a cron job?

Launchd is the macOS recommended alternative for cron jobs. See [Apple - "The preferred way to add a timed job is to use launchd"]([text](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html#//apple_ref/doc/uid/10000172i-CH1-SW2))




## Useful Links

* [Launchd man page (opens the terminal)](x-man-page://launchd.plist) - or just run
`man launchd` in your terminal.
* [Launchd.info](https://launchd.info/) - an extensive third-party resource
* [Reddit - cron or launchd](https://www.reddit.com/r/MacOS/comments/13r469w/cron_or_launchd/)
* [Apple - "The preferred way to add a timed job is to use launchd"]([text](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html#//apple_ref/doc/uid/10000172i-CH1-SW2))



## Basic Usage
