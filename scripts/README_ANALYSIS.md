# Stock Universe Analysis - Setup Guide

## Overview

The S&P 500 analysis takes ~20 minutes to complete. To avoid users waiting, we:
1. **Pre-populate cache before launch** (run once manually)
2. **Schedule weekly updates** (automated via cron)

## Quick Start

### 1. Run Analysis Before Launch

```bash
# Make sure you're in the project root
cd /path/to/FinLearnAI

# Set your Polygon API key (if not in .env)
export POLYGON_API_KEY=your_key_here

# Run the analysis (takes ~20 minutes)
python3 scripts/run_universe_analysis.py
```

This will:
- Analyze all ~500 S&P 500 stocks
- Cache results to `backend/cache/sp500_analysis.json`
- Results valid for 24 hours (but we'll refresh weekly)

### 2. Set Up Weekly Automatic Updates

**Option A: Using the setup script (recommended)**

```bash
# Run the setup script
./scripts/setup_weekly_analysis.sh
```

This creates a cron job that runs every **Sunday at 2:00 AM**.

**Option B: Manual cron setup**

```bash
# Edit crontab
crontab -e

# Add this line (runs every Sunday at 2 AM):
0 2 * * 0 cd /path/to/FinLearnAI && python3 scripts/run_universe_analysis.py >> logs/universe_analysis.log 2>&1
```

### 3. Verify Setup

```bash
# Check if cron job is set up
crontab -l

# Check if cache file exists
ls -lh backend/cache/sp500_analysis.json

# View analysis logs (if weekly job has run)
tail -f logs/universe_analysis.log
```

## How It Works

1. **Cache File**: `backend/cache/sp500_analysis.json`
   - Contains all analyzed stocks with scores
   - Loaded automatically when backend starts
   - Valid for 24 hours (but refreshed weekly)

2. **Backend Loading**:
   - On startup, backend checks for cache file
   - If found and fresh, loads it immediately
   - Users see results instantly (no waiting)

3. **Weekly Refresh**:
   - Cron job runs analysis every Sunday at 2 AM
   - Updates cache file automatically
   - Users always have fresh data (max 7 days old)

## Manual Commands

```bash
# Run analysis now
python3 scripts/run_universe_analysis.py

# Check cache file
cat backend/cache/sp500_analysis.json | jq '.stats'

# View top 10 stocks
cat backend/cache/sp500_analysis.json | jq '.stocks[:10] | .[] | {ticker, composite_score, sector}'

# Check when cache was last updated
stat backend/cache/sp500_analysis.json
```

## Troubleshooting

**Cache not loading?**
- Check file exists: `ls backend/cache/sp500_analysis.json`
- Check file permissions: `chmod 644 backend/cache/sp500_analysis.json`
- Check backend logs for cache loading messages

**Cron job not running?**
- Check cron service: `systemctl status cron` (Linux) or check cron daemon
- Check logs: `tail -f logs/universe_analysis.log`
- Verify Python path in cron: `which python3`

**Analysis fails?**
- Check Polygon API key: `echo $POLYGON_API_KEY`
- Check API rate limits (Polygon free tier has limits)
- Check network connectivity

## Production Deployment

For production (EC2/server):

1. **Before first launch:**
   ```bash
   python3 scripts/run_universe_analysis.py
   ```

2. **Set up weekly cron:**
   ```bash
   ./scripts/setup_weekly_analysis.sh
   ```

3. **Ensure logs directory exists:**
   ```bash
   mkdir -p logs
   ```

4. **Monitor weekly runs:**
   ```bash
   # Add to monitoring/alerting system
   tail -f logs/universe_analysis.log
   ```

## Schedule Options

Edit `setup_weekly_analysis.sh` to change schedule:

- **Daily at 2 AM**: `0 2 * * *`
- **Every Monday at 3 AM**: `0 3 * * 1`
- **Twice weekly (Mon/Thu)**: `0 2 * * 1,4`
- **Every 3 days**: Use a different approach (systemd timer)

## Notes

- Analysis takes ~20 minutes, so schedule during off-peak hours
- Cache file is ~5-10 MB (JSON with all stock data)
- Backend loads cache on startup (fast, <1 second)
- Users never wait - they always get cached results instantly
