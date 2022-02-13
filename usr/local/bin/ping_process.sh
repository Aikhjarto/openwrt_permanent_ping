#!/bin/sh
# This script is starting ping_process.py with parameters obtained by `uci`

# get values via uci
DST=$(uci -q get permanent_ping.permanent_ping.dst)
INTERVAL=$(uci -q get permanent_ping.permanent_ping.heartbeat_interval) 
LOG=$(uci -q get permanent_ping.permanent_ping.log_filename)
USE_TIMESUFFIX=$(uci -q get permanent_ping.permanent_ping.use_timesuffix)
MAX_TIME_MS=$(uci -q get permanent_ping.permanent_ping.max_time_ms)
RAW_LOG=$(uci -q get permanent_ping.permanent_ping.raw_log)
TIMEOUT=$(uci -q get permanent_ping.permanent_ping.timeout)

# "set -s" after all calls to uci, since they return non-zero for optional parameters
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

ARGS="--destination ${DST}"
if [[ ! -z ${INTERVAL} ]]; then
	ARGS="${ARGS} --heartbeat-interval ${INTERVAL}"
fi
if [[ ! -z "${RAW_LOG}" ]]; then
	ARGS="${ARGS} --raw-log-file ${RAW_LOG}"
fi
if [[ ! -z ${TIMEOUT} ]]; then
	ARGS="${ARGS} --timeout ${TIMEOUT}"
fi
if [[ ! -z "${LOG}" ]]; then
	ARGS="${ARGS} --log ${LOG}"
fi

python3 -u /usr/local/bin/ping_process.py ${ARGS}
exit $?

