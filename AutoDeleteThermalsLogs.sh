#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.json"

TARGET_DIR=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['log_dir'])")
FILE_PREFIX=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['log_prefix'])")
FILE_SUFFIX="*"

MIN_FILE_COUNT=2      # Only delete if more than this number of files exist
OLDER_THAN_DAYS=5     # Files older than this many days will be deleted
KEEP_NEWEST=5          # Always keep at least this many newest files
DRY_RUN=false           # true = no deletion, false = actually delete

LOCK_FILE="/tmp/log_thermals.log.lock"
# =========================

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "#######################################"
log "###############  START  ###############"
log "#######################################"

# ----- Locking -----
if [[ -e "$LOCK_FILE" ]]; then
  log "Another instance is running. Exiting."
  exit 1
fi
trap 'rm -f "$LOCK_FILE"' EXIT
touch "$LOCK_FILE"

cd "$TARGET_DIR"

# ----- Collect matching files (sorted oldest → newest) -----
mapfile -t MATCHING_FILES < <(
  find "$TARGET_DIR" -type f \
    -name "${FILE_PREFIX}*${FILE_SUFFIX}*" \
    -printf '%T@ %p\n' | sort -n | awk '{print $2}'
)

TOTAL_FILES=${#MATCHING_FILES[@]}
log "Found $TOTAL_FILES matching files."

# ----- File count guard -----
if (( TOTAL_FILES <= MIN_FILE_COUNT )); then
  log "Not deleting anything: file count TOTAL_FILES: ($TOTAL_FILES) ≤ MIN_FILE_COUNT: $MIN_FILE_COUNT."
  exit 0
fi

# ----- Determine deletion candidates -----
mapfile -t OLD_FILES < <(
  find "$TARGET_DIR" -type f \
    -name "${FILE_PREFIX}*${FILE_SUFFIX}*" \
    -mtime +"$OLDER_THAN_DAYS" \
    -printf '%T@ %p\n' | sort -n | awk '{print $2}'
)

OLD_COUNT=${#OLD_FILES[@]}

if (( OLD_COUNT == 0 )); then
  log "No files older than $OLDER_THAN_DAYS days found."
  exit 0
fi

# ----- Enforce KEEP_NEWEST -----
MAX_DELETIONS=$(( TOTAL_FILES - KEEP_NEWEST ))
if (( MAX_DELETIONS <= 0 )); then
  log "KEEP_NEWEST constraint prevents deletion."
  exit 0
fi

FILES_TO_DELETE=( "${OLD_FILES[@]:0:$MAX_DELETIONS}" )

log "Preparing to delete ${#FILES_TO_DELETE[@]} file(s)."

# ----- Delete (or dry-run) -----
for file in "${FILES_TO_DELETE[@]}"; do
  if [[ "$DRY_RUN" == true ]]; then
    log "[DRY-RUN] Would delete: $file"
  else
    log "Deleting: $file"
    rm -f -- "$file"
  fi
done

log "Cleanup completed successfully."


log "####################################"
log "##############  END  ###############"
log "####################################"


