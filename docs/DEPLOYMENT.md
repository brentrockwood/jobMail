# JobMail Production Deployment Guide

This guide covers deploying JobMail for automated, unattended operation.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Scheduling with Cron](#scheduling-with-cron)
- [Scheduling with Systemd Timer (Linux)](#scheduling-with-systemd-timer-linux)
- [Monitoring and Logging](#monitoring-and-logging)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

## Prerequisites

1. **Python 3.12+** installed
2. **Gmail API credentials** configured (see main README.md)
3. **OAuth token generated** with browser access (can copy to headless server)
4. **AI Provider API key** (OpenAI, Anthropic, or Ollama server)
5. **Secrets configured** in `secrets.env`

## Initial Setup

### 1. Clone and Install

```bash
cd /opt  # or your preferred location
git clone https://github.com/yourusername/jobmail.git
cd jobmail

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Secrets

```bash
# Copy example files
cp .env.example .env
cp secrets.env.example secrets.env

# Edit secrets.env with your credentials
nano secrets.env
```

Required secrets:
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (depending on provider)
- Gmail OAuth credentials in `credentials.json`

### 3. Generate OAuth Token

If setting up on a headless server, generate the token on a machine with browser access:

```bash
# On machine with browser:
python main.py run --dry-run --limit 1

# This will open browser for OAuth authorization
# After successful auth, token.json is created

# Copy token.json to headless server:
scp token.json user@server:/opt/jobmail/
```

### 4. Test the Setup

```bash
# Run in dry-run mode to test without making changes
python main.py run --dry-run --limit 5

# If successful, try a real run with small batch
python main.py run --limit 5

# Check statistics
python main.py stats
```

## Scheduling with Cron

Cron is the simplest option for scheduled execution on Unix-like systems.

### Setup Cron Job

```bash
# Edit crontab
crontab -e

# Add entry (runs every 4 hours)
0 */4 * * * cd /opt/jobmail && .venv/bin/python main.py run >> /var/log/jobmail/cron.log 2>&1

# Or for more control:
0 */4 * * * /opt/jobmail/scripts/run_jobmail.sh
```

### Example Wrapper Script

Create `/opt/jobmail/scripts/run_jobmail.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Configuration
PROJECT_DIR="/opt/jobmail"
VENV_DIR="$PROJECT_DIR/.venv"
LOG_DIR="/var/log/jobmail"
LOG_FILE="$LOG_DIR/jobmail-$(date +%Y%m%d).log"

# Create log directory if needed
mkdir -p "$LOG_DIR"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Change to project directory
cd "$PROJECT_DIR"

# Run JobMail
echo "=== JobMail Run: $(date) ===" >> "$LOG_FILE"
python main.py run --limit 50 >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

# Log completion
if [ $EXIT_CODE -eq 0 ]; then
    echo "Completed successfully" >> "$LOG_FILE"
else
    echo "Failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"

exit $EXIT_CODE
```

Make it executable:
```bash
chmod +x /opt/jobmail/scripts/run_jobmail.sh
```

### Cron Schedule Examples

```bash
# Every 4 hours
0 */4 * * * /opt/jobmail/scripts/run_jobmail.sh

# Twice daily (8am and 6pm)
0 8,18 * * * /opt/jobmail/scripts/run_jobmail.sh

# Every hour during business hours (Mon-Fri, 9am-5pm)
0 9-17 * * 1-5 /opt/jobmail/scripts/run_jobmail.sh

# Once daily at midnight
0 0 * * * /opt/jobmail/scripts/run_jobmail.sh
```

## Scheduling with Systemd Timer (Linux)

Systemd timers provide more advanced scheduling and better logging integration.

### 1. Create Service File

Create `/etc/systemd/system/jobmail.service`:

```ini
[Unit]
Description=JobMail Email Classifier
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=jobmail
Group=jobmail
WorkingDirectory=/opt/jobmail
Environment="PATH=/opt/jobmail/.venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/opt/jobmail/.venv/bin/python /opt/jobmail/main.py run --limit 50

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=jobmail

# Security hardening
PrivateTmp=yes
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/jobmail/jobmail.db /opt/jobmail/token.json

[Install]
WantedBy=multi-user.target
```

### 2. Create Timer File

Create `/etc/systemd/system/jobmail.timer`:

```ini
[Unit]
Description=JobMail Email Classifier Timer
Requires=jobmail.service

[Timer]
# Run every 4 hours
OnCalendar=*-*-* 00,04,08,12,16,20:00:00

# Run 5 minutes after boot if missed
OnBootSec=5min

# Run 5 minutes after last completion if behind schedule
OnUnitActiveSec=4h

# Allow some time jitter to distribute load
RandomizedDelaySec=10min

[Install]
WantedBy=timers.target
```

### 3. Create Dedicated User

```bash
# Create jobmail user (no login shell)
sudo useradd -r -s /usr/sbin/nologin -d /opt/jobmail jobmail

# Set ownership
sudo chown -R jobmail:jobmail /opt/jobmail

# Ensure secrets are readable only by jobmail user
sudo chmod 600 /opt/jobmail/secrets.env
sudo chmod 600 /opt/jobmail/token.json
sudo chmod 600 /opt/jobmail/credentials.json
```

### 4. Enable and Start

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable timer to start on boot
sudo systemctl enable jobmail.timer

# Start timer now
sudo systemctl start jobmail.timer

# Check timer status
sudo systemctl status jobmail.timer
sudo systemctl list-timers jobmail.timer
```

### 5. Manual Execution

```bash
# Run service manually (useful for testing)
sudo systemctl start jobmail.service

# Check service status
sudo systemctl status jobmail.service

# View logs
sudo journalctl -u jobmail.service -f
```

### Systemd Timer Schedule Examples

```ini
# Every 4 hours
OnCalendar=*-*-* 00,04,08,12,16,20:00:00

# Twice daily (8am and 6pm)
OnCalendar=*-*-* 08,18:00:00

# Every hour during business hours (Mon-Fri, 9am-5pm)
OnCalendar=Mon-Fri *-*-* 09..17:00:00

# Once daily at midnight
OnCalendar=daily

# Every 30 minutes
OnCalendar=*-*-* *:00,30:00
```

## Monitoring and Logging

### Log Rotation (Cron)

Create `/etc/logrotate.d/jobmail`:

```
/var/log/jobmail/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 jobmail jobmail
}
```

### Viewing Logs

```bash
# Cron logs
tail -f /var/log/jobmail/cron.log

# Systemd logs
sudo journalctl -u jobmail.service -f

# Filter by date
sudo journalctl -u jobmail.service --since "2 hours ago"

# Show only errors
sudo journalctl -u jobmail.service -p err
```

### Statistics Monitoring

```bash
# View current statistics
python main.py stats

# View recent processed emails
python main.py stats --recent 20

# Export statistics (add to cron for daily reports)
python main.py stats > /var/log/jobmail/stats-$(date +%Y%m%d).txt
```

### Email Notifications on Failure

Add to cron or systemd service to send email on failure:

```bash
# Cron with email on failure
MAILTO=admin@example.com
0 */4 * * * /opt/jobmail/scripts/run_jobmail.sh || echo "JobMail failed at $(date)"

# Or use a wrapper script that sends email
```

## Security Best Practices

### File Permissions

```bash
# Restrict access to sensitive files
chmod 600 secrets.env credentials.json token.json
chmod 640 jobmail.db

# Ensure scripts are not world-writable
chmod 755 scripts/*.sh
chmod 644 src/*.py

# Verify .gitignore includes secrets
cat .gitignore | grep -E "(secrets\.env|credentials\.json|token\.json)"
```

### Environment Isolation

```bash
# Run security scan before deployment
./scripts/security_scan.sh

# Verify no secrets in git history
git log --all --full-history --pretty=format: --name-only | grep -E "(secrets|credentials|token)" || echo "Clean"
```

### API Key Rotation

1. Rotate AI provider API keys periodically (every 90 days recommended)
2. If OAuth token is compromised, revoke access in Google Cloud Console
3. Update `secrets.env` with new credentials
4. Restart service: `sudo systemctl restart jobmail.service`

### Network Security

```bash
# Restrict outbound connections (optional firewall rules)
# Only allow HTTPS to Gmail API and AI provider APIs:
- api.openai.com (OpenAI)
- api.anthropic.com (Anthropic)
- gmail.googleapis.com (Gmail API)
- Your Ollama server (if using local AI)
```

## Troubleshooting

### OAuth Token Expired

```bash
# Regenerate token (requires browser)
rm token.json
python main.py run --dry-run --limit 1

# Copy to production server
scp token.json user@server:/opt/jobmail/
sudo chown jobmail:jobmail /opt/jobmail/token.json
sudo chmod 600 /opt/jobmail/token.json
```

### Permission Errors

```bash
# Check file ownership
ls -la /opt/jobmail/ | grep -E "(secrets|credentials|token|db)"

# Fix ownership
sudo chown jobmail:jobmail /opt/jobmail/jobmail.db
sudo chown jobmail:jobmail /opt/jobmail/token.json

# Fix permissions
sudo chmod 600 /opt/jobmail/secrets.env
```

### Database Locked

```bash
# Stop the service
sudo systemctl stop jobmail.service

# Check for stale locks
lsof /opt/jobmail/jobmail.db

# Remove lock file if safe
rm /opt/jobmail/jobmail.db-journal

# Restart service
sudo systemctl start jobmail.service
```

### Rate Limiting

If you hit API rate limits:

1. **Gmail API**: Default quota is 250 quota units/user/second, 1 billion/day
   - Reduce `BATCH_SIZE` in configuration
   - Increase time between runs

2. **AI Provider Limits**:
   - OpenAI: Check your tier limits
   - Anthropic: Check your usage limits
   - Ollama: No external rate limits (local server)

3. **Retry Logic**: The app automatically retries failed requests with exponential backoff

### Testing Configuration

```bash
# Validate configuration
python -c "from src.config import Config; c = Config.from_env(); c.validate(); print('Config OK')"

# Test Gmail connectivity
python -c "from src.config import Config; from src.gmail_client import GmailClient; client = GmailClient(Config.from_env()); client.authenticate(); print('Gmail OK')"

# Test AI provider
python -c "from src.config import Config; from src.classifier import create_classifier; classifier = create_classifier(Config.from_env()); print('AI Provider OK')"
```

## Performance Tuning

### Batch Size

Adjust `BATCH_SIZE` in `.env`:

```bash
# Small batches (lower API usage, slower overall)
BATCH_SIZE=10

# Medium batches (balanced)
BATCH_SIZE=50

# Large batches (faster, higher API usage)
BATCH_SIZE=100
```

### Confidence Threshold

Adjust `CONFIDENCE_THRESHOLD` in `.env`:

```bash
# More conservative (fewer actions, more unknowns)
CONFIDENCE_THRESHOLD=0.9

# Balanced (default)
CONFIDENCE_THRESHOLD=0.8

# More aggressive (more actions, potential misclassifications)
CONFIDENCE_THRESHOLD=0.7
```

### AI Provider Selection

- **OpenAI (GPT-4)**: Most accurate, highest cost
- **Anthropic (Claude)**: Very accurate, moderate cost
- **Ollama (Local)**: Free, requires local GPU, variable accuracy

Choose based on your priorities: accuracy, cost, or privacy/local operation.

## Backup and Recovery

### Database Backup

```bash
# Manual backup
cp jobmail.db jobmail.db.backup-$(date +%Y%m%d)

# Automated backup (add to cron)
0 2 * * * cp /opt/jobmail/jobmail.db /opt/jobmail/backups/jobmail.db.$(date +\%Y\%m\%d) && find /opt/jobmail/backups -name "jobmail.db.*" -mtime +30 -delete
```

### Restore from Backup

```bash
# Stop service
sudo systemctl stop jobmail.service

# Restore database
cp jobmail.db.backup-YYYYMMDD jobmail.db

# Fix permissions
sudo chown jobmail:jobmail jobmail.db

# Start service
sudo systemctl start jobmail.service
```

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/yourusername/jobmail/issues
- Documentation: See README.md and this deployment guide
