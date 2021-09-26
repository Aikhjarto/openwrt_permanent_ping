"""
Python 3 module to help processing long running pings and report anomalies.
"""

import argparse
import contextlib
from datetime import datetime
import fileinput
import re
import os
import signal
import sys
from threading import Timer
import time
import warnings


class Watchdog:
    """
    Idea from [1] but with daemo status of timer to not block exit of python interpreter
    and fixed handler with parameters taken from __init__().

    References
    ---------
    .. [1] https://stackoverflow.com/questions/16148735/how-to-implement-a-watchdog-timer-in-python
    """
    def __init__(self, timeout, datetime_fmt_string):
        self.datetime_fmt_string=datetime_fmt_string
        self.timeout=timeout

        self.timeout = timeout
        self.timer = Timer(self.timeout, self.handler)
        self.timer.daemon=True
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.timer = Timer(self.timeout, self.handler)
        self.timer.daemon=True
        self.timer.start()

    def stop(self):
        self.timer.cancel()

    def handler(self):
        time_string=datetime.now().strftime(self.datetime_fmt_string)
        print(f'{time_string} No result line from ping received for {self.timeout} seconds')
        self.reset()


class PingProcessor:
    """
    Class to check consecutive lines of the ouput of `ping x.x.x.x` for 
    anomalies. Anomal lines (too long roundtrip time or missing sequence 
    number, filtered messages, ...) are printed to stdout prefixed with a 
    human readable timestamp.

    Parameters
    ----------
    max_time_ms : float
        Round-trip time exceeding this value in ms will be logged to stdout.

    datetime_fmt_string : str, optional
        If given, it overrides the default format string "%Y-%m-%d %H:%M:%S".

    heartbeat_interval : float, optional
        If given and greater than zero, a heartbeat message is sent to stdout
        when no anomalies were found within the last 'heartbeat_interval'
        seconds.

    heartbeat_pipe : object
        To not gobble out output, heartbeat can be redirected.
        `heartbeat_pipe` is used as 'file=' argument to print().

    allowed_seq_diff : int
        If icmp_seq differs more more than `allowed_seq_diff` from one line to
        the next, the incident is logged. Default: 1, i.e. every missed ping
        is logged.

    raw_log_buffer : object
        Buffer object, like opened file, which has a '.write()' function 
        accepting strings.

    timeout_seconds : float
        When no response from the ping process was received for 
        `timeout_seconds` seconds, an message is written to stdout.
    """

    def __init__(self,
                 max_time_ms=1000,
                 datetime_fmt_string=None,
                 heartbeat_interval=0,
                 heartbeat_pipe=None,
                 allowed_seq_diff=1,
                 raw_log_buffer=None
                 ):

        self.max_time_ms = max_time_ms

        self.datetime_fmt_string = (
            "%Y-%m-%d %H:%M:%S" if datetime_fmt_string is None else datetime_fmt_string
        )

        # heartbeat
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_pipe = heartbeat_pipe
        self.last_timestamp = time.time()

        # raw log
        self.raw_log_buffer=raw_log_buffer

        # last line for status output
        self.last_line = ""
        self.time_string = ""

        self.last_seq = -1
        self.allowed_seq_diff = allowed_seq_diff

        # precompile regexp
        # search for seq=
        self.r_seq=re.compile(r'seq=[0-9]*')
        # search for number in square brackets
        self.r_timestamp=re.compile(r'\[[0-9]+([,.][0-9]*)?\]')
        # search from 'time={float} ms'
        self.r_roundtrip=re.compile(r'time=[0-9]+([,.][0-9]*)? ms')
        # check if something is suffiex to 'time={float} ms'
        self.r_checksuffix=re.compile(r'time=[0-9]+([,.][0-9]*)? ms.+')

    def process(self, line):
        """
        Process a line of the output of `ping x.x.x.x` or `ping -D x.x.x.x`.

        Parameters
        ----------
        line : str
            String denoting one line of the output of ping.

        Returns
        -------
        ret : int
            -1 for unparseable line, i.e. not `seq=` marker in the line
            1 if anomalies occured
            0 else

        Notes
        -----
        Typical output of `ping -D` looks like (without -D, the timestamp and the square 
        brackets are not included).
        ```
        PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
        [1597166438.798339] 64 bytes from 8.8.8.8: icmp_seq=1 ttl=118 time=14.2 ms
        [1597166439.798003] 64 bytes from 8.8.8.8: icmp_seq=2 ttl=118 time=13.8 ms
        [1597245144.447473] 64 bytes from 8.8.8.8: icmp_seq=877 ttl=118 time=244 ms (DUP!)
        [1597411489.934841] From x.x.x.x icmp_seq=14 Packet filtered
        [1597500391.382726] From x.x.x.x icmp_seq=13317 Destination Host Unreachable

        ```
        """

        ret_val=0

        # store line without newline
        self.last_line = line.rstrip()

        if line.startswith('PING '):
            # ignore startup line
            return 0

        timestamp=self._set_timestamp()
        if self.raw_log_buffer:
            if line.startswith('['):
                self.raw_log_buffer.write(line)
            else:
                self.raw_log_buffer.write(f'[{timestamp}] {line}')
                
        seq=self._get_seq_no()
        if seq < 0:
            # abort since there is something wrong with this line
            return -1
        
        # check roundtrip time
        rt_time=self._get_roundtrip()
        if (rt_time is None or # no roundtrip time in line
            rt_time > self.max_time_ms or  # too large roundtrip time
            self.r_checksuffix.match(self.last_line)): # some suffix after roundtrip time
            self._print(f"{self.time_string} {self.last_line}", timestamp=timestamp)

            ret_val=1
        
        # check sequence number increment (wraps to 0 after 65535)
        if self.last_seq != -1 and seq > (self.last_seq + self.allowed_seq_diff) % 65536:
            # missed one or more packets
            N_missed=seq-(self.last_seq+1)
            if N_missed==1:
                self._print(f"{self.time_string} Missed icmp_seq {self.last_seq+1}",
                            timestamp=timestamp)
            else:
                self._print(f"{self.time_string} Missed icmp_seq {self.last_seq+1} to {seq-1} ({N_missed} packets)",
                            timestamp=timestamp)

            ret_val=1

        # heartbeat message if nothing else happend
        if (
            self.last_timestamp
            and self.heartbeat_interval > 0
            and timestamp - self.last_timestamp > self.heartbeat_interval
        ):
            self._print(
                f"No anomalies found in the last {self.heartbeat_interval} s. "
                f"Last input was at {self.time_string}",
                file=self.heartbeat_pipe,
            )

        self.last_seq=seq

        return ret_val

    def _print(self, *args, timestamp=None, **kwargs):
        print(*args, **kwargs)

        # store time when stdout was written for next heartbeat
        if timestamp is None:
            timestamp=time.time()
        self.last_timestamp = timestamp

    def _get_seq_no(self, line=None):
        """
        Search for sequence number and return it as int. 
        Print and report an error if not found.
        """
        if line is None:
            line=self.last_line
        m=self.r_seq.search(line)
        if m is None:
            self._error(f'No sequence number time found in line "{line}" with pattern {self.r_seq.pattern}')
            return -1
        return int(line[m.start()+4:m.end()])
        
    def _get_roundtrip(self, line=None):
        """
        Parse for roundtrip time. Return as float if found or None otherise
        """
        if line is None:
            line=self.last_line
        m=self.r_roundtrip.search(line)
        if m is None:
            return None
        return float(line[m.start()+5:m.end()-3])
        
    def _set_timestamp(self, line=None):
        """
        Parse for timestamp in square brackets. 
        If not found, create one by time.time()
        """
        if line is None:
            line=self.last_line
        m=self.r_timestamp.search(line)
        if m is None:
            timestamp=time.time()
        else:
            timestamp=float(line[m.start()+1:m.end()-1])
        self.time_string = datetime.fromtimestamp(timestamp).strftime(
                         self.datetime_fmt_string
                    )
        return timestamp

    def _error(self, msg):
        print(msg)
        print(msg, file=sys.stderr)

    def print_status(self):
        """
        Callback for USR1 signal to print status to stderr.
        """
        print(f'Last line at {self.time_string}: "{self.last_line}"', file=sys.stderr)


USAGE="""Example usage: 

ping -D 8.8.8.8 | python3 -u ping_process.py

To store to file next to stdout:
ping -D 8.8.8.8 | python3 -u ping_process.py | tee -a ping.log

The '-D' argument to ping is optional, as some versions of ping do not have it.
When USR1 signal is received, status is printed to stderr.
"""


def parse_args():
    """
    Setup an run an argument parser
    """

    parser = argparse.ArgumentParser(description="Reads data from ping via stdin "
                                     "and forwards only interesting lines to stdout.",
                                     epilog=USAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("--max-time-ms", "-t", type=float, default=500, metavar="T",
                        help="Roundtrip times exceeding T will be logged. Default %(default)s")

    parser.add_argument("--fmt", type=str, default="%Y-%m-%d %H:%M:%S",
                        help=r"Format for the human readable timestamp passed to the 'datetime' module. "
                        "Default: '%(default)s'")
    parser.add_argument("--heartbeat-interval", type=float, default=0, metavar="H",
                        help="If H is greater than 0 and no output was produced within H seconds, "
                        "a status message indicating that this script is still alive will be printed." )

    parser.add_argument("--allowed-seq-diff", type=int, default=1, metavar="N",
                        help="If N or more sequence numbers are missing, a corresponding "
                        "line will be printed. Default: %(default)s")

    parser.add_argument("--raw-log-file", type=str, default=None, metavar='f',
                        help="If given, received output of ping is logged to given file. "
                        "If -D was not used for the ping process, the missing timestamp is prepended "
                        "as time when the line is processed.")
    
    parser.add_argument("--timeout", type=float, default=60.0,
                        help="A notification is printed if the ping process did not output anything "
                        "for `timeout` seconds.")

    args = parser.parse_args()

    return args


if __name__ == "__main__":

    args = parse_args()

    if sys.stdin.isatty():
        raise RuntimeError("This script is supposed to read from a pipe and not from user input. "
                           "Call it with '-h', to see options.")

    LANG=os.getenv('LANG')
    if LANG and not LANG.startswith('en'):
        warnings.warn(f'The environment variable LANG={LANG} points language other than English. '
                      'This might result in non-parseable output, e.g. "Zeit=12.3 ms" instead of '
                      'time=12.3 ms" in German. '
                      'Consider setting `LC_ALL=C` to avoid problems with localization.', 
                      category=RuntimeWarning)

    # Hint about nullcontext() to open a file conditionally:
    # https://stackoverflow.com/questions/12168208/is-it-possible-to-have-an-optional-with-as-statement-in-python
    if args.raw_log_file:
        # Create folder for raw log if not exist and handle the case when 
        # dirname was an empty string denoting CWD. 
        # (makedirs produce FileNotFoundError in case of an empty string)
        dirname=os.path.dirname(args.raw_log_file)
        if dirname: 
            os.makedirs(dirname, exist_ok=True)

    with (open(args.raw_log_file,'a+', buffering=1) if args.raw_log_file else contextlib.nullcontext()) as f:
        p = PingProcessor(max_time_ms=args.max_time_ms,
                          datetime_fmt_string=args.fmt,
                          heartbeat_interval=args.heartbeat_interval,
                          allowed_seq_diff=args.allowed_seq_diff,
                          raw_log_buffer=f
                          )

        # callback for USR1
        signal.signal(signal.SIGUSR1, lambda sig, frame: p.print_status())

        # watchdog in case ping does not send anything for a given time
        watchdog = Watchdog(args.timeout, args.fmt)

        # read from stdin and pass to PingProcessor
        for line in fileinput.input("-"):
            p.process(line)
            watchdog.reset()

