# OpenWrt service to log ping problems

This project provides a service for OpenWrt to check stability of a network
connection by monitoring the output of a long-lasting `ping` and logging only
interesting (long roundtrip-time, missed packages).

It writes to syslog and to a optionally to a file.

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

Praxis tip: You may want to set the log destination not to RAM, but to a thumbdrive.

* `dst`: The host to ping (IP or hostname).
* `heartbeat_interval`: Interval in seconds to write an "everything is fine"-message to the log to verify that the service is running.
* `log_filename`: If given, the supplied filename is used to create the file an write log messages additionally to syslog.
* `raw_log`: If givven, the supplied filename is used to create a file an write all lines from the ping process with a timestamp.
* `max_time_ms`: Maximum roundtrip time in milliseconds which is considered an not-an-issue.
* `use_timesuffix`: If not empty, a date-time suffix is append to `log_filename` and `raw_log` is appended to generate a new file each startup.

Example `/etc/config/permanent_ping`:
```
config permanent_ping 'permanent_ping'
#        option heartbeat_interval 600
#        option log_filename /mnt/sda1/persistent/ping_log/ping
#        option use_timesuffix '1'
#        option dst '8.8.8.8'
#        option max_time_ms 500
#        option raw_log /mnt/sda1/persisten/ping_log/raw
```

