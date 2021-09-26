# OpenWrt service to log ping problems

This project provides a service for OpenWrt to check stability of a network
connection by monitoring the output of a long-lasting `ping` and logging only
interesting events (long roundtrip-time, missed packages).

It writes to syslog and optionally to a file.

## Install
Python is required, thus install via opkg.
```
opkg update
opkg install python-light
```

Then, copy files from folder `etc` and `usr` to the `/etc` and `/usr` (including subfolders) on the router, respectivley.

Ensure that `/etc/init.d/permanent_ping` retains its executable flag during copy.

## Start/stop
The service can be started, stopped, enabled and disabled using
```
service permanent_ping {start, stop, enable, disable}
```
or via LUCI webinterface like any other service.

## Configuration
Parameters are stored in `/etc/config/permanent_ping` and can be edited via text editor or `uci`, e.g.
```
uci set permanent_ping.permanent_ping.dst=1.2.3.4
uci commit
```

Supperted parameters are:
* `dst`: The host to ping (IP or hostname).
* `heartbeat_interval`: Interval in seconds to write an "everything is fine"-message to the log to verify that the service is running.
* `log_filename`: If given, the supplied filename is used to create the file an write log messages additionally to syslog.
* `raw_log`: If givven, the supplied filename is used to create a file an write all lines from the ping process with a timestamp.
* `max_time_ms`: Maximum roundtrip time in milliseconds which is considered an not-an-issue.
* `use_timesuffix`: If not empty, a date-time suffix is append to `log_filename` and `raw_log` is appended to generate a new file each startup.
* `timeout`: When ping command does not send any line for `timeout` seconds, a message is printed.

Praxis tip: You may want to set the `log_filename` not to RAM, but to a thumbdrive.

# Other platforms
`usr/local/bin/ping_process.py` can be used standalone (without the startup and config files for OpenWrt) on any other platform which supports python>3.6.

Usage guide can be printed using `python3 usr/local/bin/ping_process.py -h`
```
Reads data from ping via stdin and forwards only interesting lines to stdout.

optional arguments:
  -h, --help            show this help message and exit
  --max-time-ms T, -t T
                        Roundtrip times exceeding T will be logged. Default 500
  --fmt FMT             Format for the human readable timestamp passed to the 'datetime' module. Default: '%Y-%m-%d %H:%M:%S'
  --heartbeat-interval H
                        If H is greater than 0 and no output was produced within H seconds, a status message indicating that this script is still alive will be printed.
  --allowed-seq-diff N  If N or more sequence numbers are missing, a corresponding line will be printed. Default: 1
  --raw-log-file f      If given, received output of ping is logged to given file. If -D was not used for the ping process, the missing timestamp is prepended as time when the line is
                        processed.
  --timeout TIMEOUT     A notification is printed if the ping process did not output anything for `timeout` seconds.

Example usage: 

ping -D 8.8.8.8 | python3 -u ping_process.py

To store to file next to stdout:
ping -D 8.8.8.8 | python3 -u ping_process.py | tee -a ping.log

The '-D' argument to ping is optional, as some versions of ping do not have it.
When USR1 signal is received, status is printed to stderr.
```

