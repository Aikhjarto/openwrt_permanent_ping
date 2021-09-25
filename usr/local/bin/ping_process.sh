#!/bin/sh
# This script is starting ping_process2.py in a special manner
# so it can be used with procd to be run as a service.

# https://forum.openwrt.org/t/solved-procd-service-doesnt-kill-its-children-processes/29622
# https://aweirdimagination.net/2020/06/28/kill-child-jobs-on-script-exit/
# https://linux.die.net/man/1/ash section "grouping commands together"

#trap 'echo EXIT $(jobs -p)' EXIT
#trap 'echo INT $(jobs -p)' INT
#trap 'echo HUP $(jobs -p)' HUP
#trap 'echo QUIT $(jobs -p)' QUIT
trap 'echo TERM $(jobs -p); kill $(jobs -p)' TERM

DST=$(uci -q get permanent_ping.permanent_ping.dst)
INTERVAL=$(uci -q get permanent_ping.permanent_ping.heartbeat_interval) 
LOG=$(uci -q get permanent_ping.permanent_ping.log_filename)
USE_TIMESUFFIX=$(uci -q get permanent_ping.permanent_ping.use_timesuffix)
MAX_TIME_MS=$(uci -q get permanent_ping.permanent_ping.max_time_ms)
RAW_LOG=$(uci -q get permanent_ping.permanent_ping.raw_log)
TIMEOUT=$(uci -q get permanent_ping.permanent_ping.timeout)

# "set -s" after calls to uci since they return non-zero for optional parameters
set -e

if [[ -z "${DST}" ]]; then
	DST="8.8.8.8"
fi

if [[ ! -z "${USE_TIMESUFFIX}" ]]; then
	SUFFIX=$(date +%Y-%m-%d_%H%M%S)
	if [[ ! -z "${LOG}" ]]; then
		LOG="${LOG}"_"${SUFFIX}"
	fi

	if [[ ! -z "${RAW_LOG}" ]]; then
		RAW_LOG="${RAW_LOG}_${SUFFIX}"
	fi
fi

ARGS=""
if [[ ! -z ${INTERVAL} ]]; then
	ARGS="${ARGS} --heartbeat-interval ${INTERVAL}"
fi
if [[ ! -z "${RAW_LOG}" ]]; then
	ARGS="${ARGS} --raw-log-file ${RAW_LOG}"
fi
if [[ ! -z ${TIMEOUT} ]]; then
	ARGS="${ARGS} --timeout ${TIMEOUT}"
fi

# important to start the pipe in background as the in the foreground
# traps will not trigger
# user curly brackets and ";" instead of round brackets to make
# the "jobs" command able to see the subprocesses
if [[ ! -z "${LOG}" ]]; then
    { ping ${DST} | \
      python3 -u /usr/local/bin/ping_process.py ${ARGS} | \
      tee -a "${LOG}"; } &
else
    { ping ${DST} | \
      python3 -u /usr/local/bin/ping_process.py ${ARGS}; }
fi

# while loop which returns to the shell once in a while to make the trap execute
while [ 1 ]; do 
    sleep 1
done

