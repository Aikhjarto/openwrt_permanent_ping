# OpenWrt service to log ping problems

This project provides a service for OpenWrt to check stability of a network
connection by monitoring the output of a long-lasting `ping` and logging only
interesting (long roundtrip-time, missed packages).

It writes to syslog and to a optionally to a file.

## Install

Copy files from folder `etc` and `usr` to the `/etc` and `/usr` (including subfolders) on the router, respectivley.

## Config

Adjust parameters in `/etc/config/permanent_ping`.
You may want to set the log destination not to RAM, but to a thumbdrive.
The lines for 'log_filename' and 'use_timesuffix' can be deleted to disable
creation of a dedicated logfile (log to syslog only) or creation of a timestamp
as suffix for the dedicated log file.


## Start

```
service permanent_ping enable
service permanent_ping start
```
