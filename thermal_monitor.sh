#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.json"

LOG_DIR=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['log_dir'])")
LOG_PREFIX=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['log_prefix'])")

mkdir -p "$LOG_DIR"

DATE=$(date '+%Y-%m-%d_%H-%M-%S')

LOG_FILE="$LOG_DIR/${LOG_PREFIX}$DATE"
INTERVAL=2   # seconds between checks


echo "Cron run started for $PWD $0 at $DATE" 


echo " Deleting old Logs once at $DATE"
bash "$SCRIPT_DIR/AutoDeleteThermalsLogs.sh" >> "$LOG_FILE" 2>&1


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
