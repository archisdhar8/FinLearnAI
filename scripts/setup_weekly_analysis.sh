#!/bin/bash
# Setup Weekly S&P 500 Analysis Cron Job
# This runs the analysis every week automatically

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_PATH="$(which python3)"

# Create cron job that runs every Sunday at 2 AM
CRON_SCHEDULE="0 2 * * 0"  # Every Sunday at 2 AM

CRON_JOB="$CRON_SCHEDULE cd $PROJECT_DIR && $PYTHON_PATH scripts/run_universe_analysis.py >> logs/universe_analysis.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "run_universe_analysis.py"; then
    echo "Cron job already exists. Removing old one..."
    crontab -l 2>/dev/null | grep -v "run_universe_analysis.py" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Weekly analysis cron job set up!"
echo ""
echo "Schedule: Every Sunday at 2:00 AM"
echo "Script: $PROJECT_DIR/scripts/run_universe_analysis.py"
echo "Logs: $PROJECT_DIR/logs/universe_analysis.log"
echo ""
echo "To view current cron jobs: crontab -l"
echo "To remove this cron job: crontab -e (then delete the line)"
echo ""
echo "To run manually right now:"
echo "  cd $PROJECT_DIR && python3 scripts/run_universe_analysis.py"
