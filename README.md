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
- API key for at least one AI provider (OpenAI, Anthropic, Gemini, or local Ollama)

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
# - GEMINI_API_KEY (if using Gemini)
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
# Process inbox (default: 20 emails)
python main.py run

# Process with custom limit
python main.py run --limit 50

# Process with date filters
python main.py run --after 2024/01/01 --before 2024/12/31

# Process with custom query
python main.py run --query "from:noreply@linkedin.com"
```

### Dry Run Mode

Test without making changes:

```bash
# Dry run via CLI flag
python main.py run --dry-run --limit 10

# Or set in secrets.env
DRY_RUN=true
python main.py run
```

### View Statistics

```bash
# Show classification statistics
python main.py stats

# Show statistics with recent emails
python main.py stats --recent 10
```

### Reset Database

```bash
# Clear all processed email records (with confirmation)
python main.py reset

# Skip confirmation
python main.py reset --force
```

### Configuration Options

All configuration is via environment variables in `secrets.env`. See `secrets.env.example` for comprehensive documentation with all options.

#### AI Provider Selection

JobMail supports four AI providers. Choose the one that best fits your needs:

| Provider | Pros | Cons | Setup |
|----------|------|------|-------|
| **OpenAI** | High accuracy, fast responses | Costs per API call | Get API key from [OpenAI Platform](https://platform.openai.com/api-keys) |
| **Anthropic** | Excellent quality, privacy-focused | Costs per API call | Get API key from [Anthropic Console](https://console.anthropic.com/) |
| **Gemini** | Latest Google AI, competitive pricing | Newer, experimental models | Get API key from [Google AI Studio](https://aistudio.google.com/apikey) |
| **Ollama** | Free, runs locally, data stays private | Requires local installation, slower | Install from [Ollama.ai](https://ollama.ai) |

**OpenAI Configuration:**
```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4  # Options: gpt-4, gpt-4-turbo, gpt-3.5-turbo
```

**Anthropic Configuration:**
```bash
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929  # Latest Claude model
```

**Gemini Configuration:**
```bash
AI_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-2.0-flash-exp  # Options: gemini-2.0-flash-exp, gemini-1.5-pro, gemini-1.5-flash
```

**Ollama Configuration:**

Ollama runs AI models locally on your machine. Best for privacy and cost control.

```bash
# 1. Install Ollama from https://ollama.ai
# 2. Pull a model: ollama pull llama2
# 3. Configure JobMail:

AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1  # Note: /v1 path is required
OLLAMA_MODEL=llama2  # or qwen2.5:72b-instruct-q4_K_M, mistral, phi3, etc.
```

Popular Ollama models:
- `llama2` - General purpose, 7B parameters
- `qwen2.5:72b-instruct-q4_K_M` - High quality (requires 48GB+ RAM)
- `mistral` - Fast and efficient
- `phi3` - Small and fast (good for low-resource systems)

**Remote Ollama Setup:**

If running Ollama on a different machine:
```bash
OLLAMA_BASE_URL=http://your-server:11434/v1
```

#### Core Configuration

| Variable | Default | Range/Options | Description |
|----------|---------|---------------|-------------|
| `AI_PROVIDER` | `openai` | `openai`, `anthropic`, `gemini`, `ollama` | Which AI provider to use |
| `CONFIDENCE_THRESHOLD` | `0.8` | `0.75`-`0.85` recommended | Minimum confidence for classification. Lower = more emails labeled (may include false positives). Higher = fewer emails labeled (only high confidence). |
| `BATCH_SIZE` | `20` | `20`-`50` regular runs, `100`-`500` bulk processing | Number of emails to process per run. Larger batches may hit API rate limits. |
| `DRY_RUN` | `false` | `true`, `false` | If `true`, log actions without making changes to Gmail. Use for testing. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | Logging verbosity. Use `INFO` for production, `DEBUG` for troubleshooting. |

#### Gmail Labels

Customize label names applied to classified emails:

| Variable | Default | Description |
|----------|---------|-------------|
| `LABEL_ACKNOWLEDGED` | `Acknowledged` | Application acknowledgements (auto-archived) |
| `LABEL_REJECTED` | `Rejected` | Rejections (auto-archived) |
| `LABEL_FOLLOWUP` | `FollowUp` | Emails requiring action (NOT archived) |
| `LABEL_JOBBOARD` | `JobBoard` | Job board notifications (auto-archived) |

#### Advanced Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GMAIL_CREDENTIALS_FILE` | `credentials.json` | Path to OAuth2 credentials from Google Cloud |
| `GMAIL_TOKEN_FILE` | `token.json` | Path where OAuth2 token is stored (auto-generated) |
| `DATABASE_PATH` | `jobmail.db` | SQLite database path for tracking processed emails |

### Automated Runs

For unattended/production operation, see the **[Deployment Guide](docs/DEPLOYMENT.md)** for complete instructions on:

- Setting up cron jobs
- Configuring systemd timers
- Log rotation and monitoring
- Security best practices
- Troubleshooting

Quick cron example:

```bash
# Edit crontab
crontab -e

# Run every 4 hours
0 */4 * * * cd /path/to/jobmail && .venv/bin/python main.py run >> /var/log/jobmail.log 2>&1
```

## Development

### Run All Checks

```bash
# Run all checks (tests, linting, type checking, security)
./scripts/run_checks.sh
```

### Individual Checks

```bash
# Run tests
pytest

# Code formatting
black src/ tests/ main.py

# Linting
ruff check src/ tests/ main.py

# Type checking
mypy src/ main.py

# Security scan
./scripts/security_scan.sh
```

## Project Structure

```
jobmail/
├── src/
│   ├── __init__.py
│   ├── config.py            # Configuration management
│   ├── gmail_client.py      # Gmail API wrapper
│   ├── classifier.py        # AI classification logic
│   ├── processor.py         # Main processing loop
│   └── storage.py           # SQLite state tracking
├── tests/                   # Test files
├── scripts/
│   ├── run_checks.sh        # Run all quality checks
│   └── security_scan.sh     # Security scanning
├── docs/
│   └── DEPLOYMENT.md        # Production deployment guide
├── project/                 # Project planning & context
├── main.py                  # CLI entry point
├── .venv/                   # Virtual environment (not in git)
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

