#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <project-dir>" >&2
  exit 1
fi

PROJECT_DIR="$1"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
RUNNER="$PROJECT_DIR/run_pipeline.py"
ENV_FILE="$PROJECT_DIR/.env"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/daily_run.log"

mkdir -p "$LOG_DIR"

if [[ -f "$ENV_FILE" ]]; then
  CRON_LINE="0 2 * * * cd $PROJECT_DIR && set -a && . $ENV_FILE && set +a && $PYTHON_BIN $RUNNER >> $LOG_FILE 2>&1"
else
  CRON_LINE="0 2 * * * cd $PROJECT_DIR && $PYTHON_BIN $RUNNER >> $LOG_FILE 2>&1"
fi

(crontab -l 2>/dev/null | grep -Fv "$RUNNER" || true; echo "$CRON_LINE") | crontab -
echo "Installed cron job:"
echo "$CRON_LINE"
