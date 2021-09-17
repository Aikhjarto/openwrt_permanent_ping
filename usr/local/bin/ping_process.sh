#!/bin/sh
# This script is starting ping_process2.py in a special manner
# so it can be used with procd to be run as a service.

# https://forum.openwrt.org/t/solved-procd-service-doesnt-kill-its-children-processes/29622
# https://aweirdimagination.net/2020/06/28/kill-child-jobs-on-script-exit/
# https://linux.die.net/man/1/ash section "grouping commands together"
set -e

#echo started
#trap 'echo EXIT $(jobs -p)' EXIT
#trap 'echo INT $(jobs -p)' INT
#trap 'echo HUP $(jobs -p)' HUP
#trap 'echo QUIT $(jobs -p)' QUIT
trap 'echo TERM $(jobs -p); kill $(jobs -p)' TERM

# important to start the pipe in background as the in the foreground
# traps will not trigger
# user curly brackets and ";" instead of round brackets to make
# the "jobs" command able to see the subprocesses
{ ping 8.8.8.8 | python3 -u /usr/local/bin/ping_process.py --heartbeat-interval 600 | tee /tmp/ping$(date +%Y-%m-%d_%H%M%S); } &

# while loop which returns to the shell once in a while to make the trap execute
while [ 1 ]; do 
    sleep 1
done

