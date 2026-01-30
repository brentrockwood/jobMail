# JobMail

An AI-powered classifier for a Gmail inbox that contains job application related email.

It should be able to classify:

- Acknowledgement of application receipt (label, archive)
- Rejection (label, archive)
- Follow up required (label)

Future versions may include features such as:

- Scheduling of interviews.
- Ranking of jobs based on given skillset and other provided factors.
- File based configuration (TOML?)
- Recognize and learn from manual recategorization
- Tag with employer/client ID/Name. Recognize person name.

---

# Implementation Plan

## Stack & Framework Decisions

### Language & Runtime
- **Python 3.12**

### AI Provider
- **OpenAI, Anthropic, and local Ollama** (OpenAI compatible API)
- All three providers supported, configurable

### Architecture
- **Script-based processor**
  - Runs on schedule (cron/systemd timer)
  - Fetches unprocessed emails, classifies, applies labels
  - Stores processed message IDs to avoid reprocessing
  - Minimal dependencies, easy to deploy
  - Unattended operation (headless/command line)

### Testing Framework
- **pytest** with pytest-mock and responses for HTTP mocking

### Code Style & Quality
- **PEP 8** compliance
- **black** - Code formatter
- **ruff or pylint** - Linter
- **mypy** - Type checking

### Security Scanning
- **Trufflehog**
- Manual grep for common patterns (scripted)

### Dependency Management
- **venv** for virtual environment
- **Pin to major versions** (may tighten as needed)

## Technical Components

### 1. Gmail API Integration
- OAuth2 authentication flow (headless/unattended operation)
- Scopes needed: `gmail.modify` (read, label, archive)
- Filter for relevant inbox messages
- Apply labels and archive operations

### 2. AI Classification
- Design classification prompt
- Parse structured output (JSON with label + confidence + provider/model tracking)
- Handle classification categories:
  - **acknowledgement**: label "Acknowledged", archive
  - **rejection**: label "Rejected", archive
  - **followup_required**: label "FollowUp", no archive
  - **jobboard**: label "JobBoard", archive (automated job board notifications)
  - **unknown/unclear**: no label, no archive, log for review
- Input: Both email subject and body for accuracy
- Confidence threshold: **0.8** (configurable, will evaluate with real data)
- Track AI provider and model used for each classification (for learning over time)

### 3. State Management
- Track processed message IDs in **SQLite**
- Avoid reprocessing same messages
- Store classification results for audit trail with:
  - Message ID
  - Classification category
  - Confidence score
  - AI provider and model used
  - Timestamp
- Efficient lookup for large volumes (rare after initial run)
- Future: Recognize manual recategorization

### 4. Configuration
- **Environment variables** via secrets.env
  - AI provider credentials (OpenAI, Anthropic, Ollama)
  - Gmail OAuth credentials
  - Label names (configurable, flat hierarchy)
  - Processing batch size (configurable, small for testing, larger for production)
  - Dry-run mode flag
  - Confidence threshold (default: 0.8)
- Future: Option to move to config file (TOML)

### 5. Error Handling
- Retry logic for API failures (exponential backoff)
- Logging with context (message ID, classification, errors)
- Graceful handling of ambiguous classifications (log for review)
- Rate limit handling (Gmail API, AI provider)
- No logging of email content (privacy)

### 6. Testing Strategy
- Unit tests for classification logic
- Mock Gmail API responses for testing
- Mock AI responses for testing
- Integration tests with test Gmail account
- Sample emails corpus for classification accuracy testing

## Implementation Phases

### Phase 1: Foundation
- [ ] Project structure setup
- [ ] Virtual environment (venv) setup
- [ ] Gmail API authentication & basic read (OAuth2, headless)
- [ ] Environment configuration (secrets.env pattern)
- [ ] Logging setup

### Phase 2: Core Classification
- [ ] AI integration for all three providers (OpenAI, Anthropic, Ollama)
- [ ] Classification prompt design
- [ ] Classification logic with confidence threshold
- [ ] Output parsing & validation (structured JSON)
- [ ] Unit tests for classification

### Phase 3: Gmail Actions
- [ ] Label creation/management (flat hierarchy)
- [ ] Apply labels to messages
- [ ] Archive operations
- [ ] State tracking (processed messages in SQLite)
- [ ] Efficient historical processing

### Phase 4: Production Readiness
- [x] Error handling & retry logic (exponential backoff)
- [x] Rate limiting
- [x] Dry-run mode
- [x] Configurable batch size
- [x] Integration tests
- [x] Security scanning (Trufflehog + scripted grep)
- [x] Documentation (setup, usage, troubleshooting)
- [x] Deployment guide (cron setup for unattended operation)

### Phase 5: Documentation Enhancement
- [ ] Expand Configuration Options section in README.md
- [ ] Document all AI providers (OpenAI, Anthropic, Ollama) with setup details
- [ ] Add Ollama-specific configuration (base URL, model examples)
- [ ] Enhance secrets.env.example with comprehensive inline comments
- [ ] Add recommended ranges for configuration values (confidence threshold, batch size)

### Phase 6: Gemini Support
- [ ] Add Google Gemini as fourth AI provider option
- [ ] Use OpenAI-compatible API endpoint for consistency
- [ ] Add GEMINI_API_KEY and GEMINI_MODEL configuration
- [ ] Update classifier factory to support gemini provider
- [ ] Add Gemini setup instructions to README
- [ ] Test with real Gemini API key
- [ ] Update tests to cover Gemini classifier

## Decisions & Rationale

### Gmail Account Setup
- **Decision**: User OAuth2 for headless/command line operation
- **Question**: Service account vs user OAuth - need to verify best approach for unattended use

### Label Hierarchy
- **Decision**: Flat labels (Acknowledged, Rejected, FollowUp)
- No nesting for simplicity

### Confidence Threshold
- **Decision**: Start with 0.8, evaluate with real data
- Easy to adjust via configuration

### Processing Batch Size
- **Decision**: Configurable
- Small batches for testing
- Initial production run: Several hundred to thousand emails
- Ongoing: ~12-20 emails/day with hourly runs

### Email Content Analysis
- **Decision**: Use both subject and body
- Better classification accuracy

### Historical Processing
- **Decision**: Process all emails not in SQLite processed log
- Efficient lookup required for rare large-volume scenarios

### Secrets Management
- **Decision**: secrets.env pattern per DOA
- .env.example and secrets.env.example provided
- OAuth credentials and API keys in secrets.env (gitignored)

## Dependencies

### Core
- google-api-python-client (Gmail API)
- google-auth-oauthlib (OAuth2)
- openai (OpenAI API)
- anthropic (Anthropic API)
- python-dotenv (environment config)

### Storage
- sqlite3 (built-in)

### Testing
- pytest
- pytest-mock
- responses (HTTP mocking)

### Code Quality
- black (formatter)
- ruff or pylint (linter)
- mypy (type checking)

### Security
- trufflehog

## Project Structure

```
jobmail/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── gmail_client.py      # Gmail API wrapper
│   ├── classifier.py        # AI classification logic
│   ├── processor.py         # Main processing loop
│   └── storage.py           # State tracking (SQLite)
├── tests/
│   ├── test_classifier.py
│   ├── test_gmail_client.py
│   └── fixtures/            # Sample emails
├── config/
│   └── labels.json          # Label configuration
├── scripts/
│   └── security_scan.sh     # Security scanning script
├── .env.example
├── secrets.env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Security Considerations

- OAuth credentials in secrets.env (gitignored)
- API keys in environment variables
- No logging of email content (privacy)
- Secure token storage (Gmail OAuth refresh tokens)
- Read-only access where possible (requires gmail.modify for labels)
- Security scanning after every file change
