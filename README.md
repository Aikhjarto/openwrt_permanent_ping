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

