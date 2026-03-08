#!/usr/bin/env bash

set -euo pipefail

mkdir -p "$HOME/system_monitor/thermals/logs"

DATE=$(date '+%Y-%m-%d_%H-%M-%S')

LOG_FILE="$HOME/system_monitor/thermals/logs/log_thermals.log$DATE"
INTERVAL=2   # seconds between checks


echo "Cron run started for $PWD $0 at $DATE" 


echo " Deleting old Logs once at $DATE"
bash $HOME/system_monitor/thermals/AutoDeleteThermalsLogs.sh >> "$LOG_FILE" 2>&1


while true; do
    {
        echo "=============== $(date '+%Y-%m-%d %H:%M:%S') ==============="
        # CPU
        echo "$(date '+%Y-%m-%d %H:%M:%S') |CPU| $(sensors | head -4 | paste -sd '|' - | sed 's/|/ || /g')"
        # Battery
        echo "$(date '+%Y-%m-%d %H:%M:%S') |BAT| $(sensors | head -9 | tail -4 | paste -sd '|' - | sed 's/|/ || /g')"
        # ACPI
        echo "$(date '+%Y-%m-%d %H:%M:%S') |ACPI| $(sensors | tail -13 | paste -sd '|' - | sed 's/|/ || /g')"
        echo
    } >> "$LOG_FILE" 2>&1

    sleep "$INTERVAL"
done
