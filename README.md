# JobMail

An AI-powered classifier for Gmail job application emails. Automatically categorizes job-related emails and applies labels for better organization.

## Features

JobMail can classify and process:

- **Acknowledgements**: Application receipt confirmations (label + archive)
- **Rejections**: Application rejections (label + archive)
- **Follow-ups**: Emails requiring your action (label only, no archive)
- **Job Board**: Automated job board notifications (label + archive)

## Future Enhancements

- Interview scheduling integration
- Job ranking based on skillset and preferences
- File-based configuration (TOML)
- Learning from manual recategorization
- Employer/client identification and tagging

## Requirements

- Python 3.12 or higher
- Gmail account with API access enabled
- API key for at least one AI provider (OpenAI, Anthropic, or local Ollama)

## Setup

### 1. Clone and Create Virtual Environment

```bash
cd jobmail
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Gmail API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API" and enable it
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client ID"
   - Choose "Desktop app" as application type
   - Download the credentials JSON file
5. Save the downloaded file as `credentials.json` in the project root

### 4. Configure Secrets

```bash
# Copy example files
cp .env.example secrets.env

# Edit secrets.env and add your API keys
# At minimum, set one of these:
# - OPENAI_API_KEY (if using OpenAI)
# - ANTHROPIC_API_KEY (if using Anthropic)
# - OLLAMA_BASE_URL (if using local Ollama)
```

Example `secrets.env`:

```bash
# Choose your AI provider
AI_PROVIDER=openai

# OpenAI configuration
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4

# Or use Anthropic
# AI_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-your-key-here

# Or use local Ollama
# AI_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
```

### 5. First Run - Authentication

On the first run, JobMail will open your browser to authorize Gmail access:

```bash
python -m src.main
```

- Follow the OAuth flow in your browser
- Grant the requested permissions
- The token will be saved to `token.json` for future unattended runs

**Note**: For unattended/headless operation after initial setup, the `token.json` file must exist. Generate it once on a machine with browser access, then copy it to your production environment.

### 6. Optional: Install Development Tools

```bash
pip install -e ".[dev]"
```

This installs testing and code quality tools:
- pytest (testing)
- black (code formatter)
- ruff (linter)
- mypy (type checker)

## Usage

### Basic Usage

Process unread job emails in your inbox:

```bash
python -m src.main
```

### Dry Run Mode

Test without making changes:

```bash
# Set in secrets.env
DRY_RUN=true

# Or export temporarily
export DRY_RUN=true
python -m src.main
```

### Configuration Options

All configuration is via environment variables in `secrets.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_PROVIDER` | `openai` | AI provider: `openai`, `anthropic`, or `ollama` |
| `CONFIDENCE_THRESHOLD` | `0.8` | Minimum confidence for classification (0.0-1.0) |
| `BATCH_SIZE` | `20` | Number of emails to process per run |
| `DRY_RUN` | `false` | If `true`, log actions without making changes |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LABEL_ACKNOWLEDGED` | `Acknowledged` | Label name for acknowledgements |
| `LABEL_REJECTED` | `Rejected` | Label name for rejections |
| `LABEL_FOLLOWUP` | `FollowUp` | Label name for follow-ups |
| `LABEL_JOBBOARD` | `JobBoard` | Label name for job board notifications |

### Automated Runs

For unattended operation, set up a cron job:

```bash
# Edit crontab
crontab -e

# Run every hour
0 * * * * cd /path/to/jobmail && /path/to/jobmail/venv/bin/python -m src.main >> /var/log/jobmail.log 2>&1
```

Or use systemd timer (see deployment documentation).

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src/ tests/
```

### Linting

```bash
ruff check src/ tests/
```

### Type Checking

```bash
mypy src/
```

### Security Scanning

```bash
# Install trufflehog (one-time)
# See: https://github.com/trufflesecurity/trufflehog

# Run security scan
trufflehog filesystem . --no-update
```

## Project Structure

```
jobmail/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration management
│   ├── gmail_client.py      # Gmail API wrapper
│   ├── classifier.py        # AI classification logic
│   ├── processor.py         # Main processing loop
│   └── storage.py           # SQLite state tracking
├── tests/                   # Test files
├── project/                 # Project documentation
├── venv/                    # Virtual environment (not in git)
├── credentials.json         # Gmail OAuth credentials (not in git)
├── token.json              # Gmail OAuth token (not in git)
├── secrets.env             # Your secrets (not in git)
├── jobmail.db              # SQLite database (not in git)
└── requirements.txt        # Python dependencies
```

## Troubleshooting

### "Credentials file not found"

Download OAuth credentials from Google Cloud Console as described in Setup step 3.

### "OPENAI_API_KEY is required"

Ensure `secrets.env` exists and contains your API key for the selected provider.

### "Token has been expired or revoked"

Delete `token.json` and re-authenticate:

```bash
rm token.json
python -m src.main
```

### Gmail API quota exceeded

Gmail API has rate limits. If you hit them:
- Reduce `BATCH_SIZE` in configuration
- Increase time between cron runs
- Monitor usage in Google Cloud Console

## Security

- **Never commit** `secrets.env`, `credentials.json`, `token.json`, or `jobmail.db`
- All secrets are gitignored by default
- Email content is not logged (privacy by design)
- OAuth tokens are encrypted at rest by Google's library
- Use `gmail.modify` scope (not full `gmail` access) for least privilege

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
