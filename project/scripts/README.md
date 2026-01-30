# Context Management Scripts

Two bash scripts for managing structured context log files with automatic rotation.

## Scripts

### `add-context`
Adds properly formatted entries to a context file with auto-generated metadata.

**Usage:**
```bash
add-context --agent AGENT --model MODEL [OPTIONS] [BODY_TEXT]
```

**Required Parameters:**
- `--agent AGENT` - Agent name and version (e.g., "CLI/1.0")
- `--model MODEL` - Model name and version (e.g., "gpt-4")

**Optional Parameters:**
- `--session SESSION` - Session identifier
- `--output FILE` - Output context file (default: `context.md`)
- `--file FILE` - Read body from file

**Body Input (priority order):**
1. Remaining arguments as body text (quoted)
2. `--file` to read from file
3. stdin if no body provided

**Auto-generated Fields:**
- `date` - ISO 8601 local date and time with offset
- `hash` - Base64 encoded SHA-256 hash of body text
- `startCommit` - Git hash of most recent commit (if in git repo)

**Examples:**
```bash
# Body as argument
add-context --agent "CLI/1.0" --model "gpt-4" "This is my context"

# Body from file
add-context --agent "CLI/1.0" --model "gpt-4" --file body.txt

# Body from stdin
cat body.txt | add-context --agent "CLI/1.0" --model "gpt-4"

# With session and custom output
add-context --agent "CLI/1.0" --model "gpt-4" --session "abc123" \
  --output my-context.md "Context text"
```

### `rotate-context`
Rotates context files when they exceed a size limit, moving older entries to timestamped overflow files.

**Usage:**
```bash
rotate-context [OPTIONS]
```

**Options:**
- `--file FILE` - Context file to rotate (default: `context.md`)
- `--size BYTES` - Size limit in bytes (default: `1048576` = 1MB)
- `--keep N` - Number of recent entries to keep (default: `2`)

**Behavior:**
- Checks file size; if under limit, exits with code 1 (no rotation)
- If over limit and has more than `--keep` entries, creates overflow file
- Overflow filename: `<basename>-YYYY-MM-DDTHH_MM_SS±OFFSET.md`
- Original file is trimmed to keep only the last N entries
- Prints overflow filename to stdout on success (exit code 0)
- Returns exit code 2 on errors

**Examples:**
```bash
# Use defaults (context.md, 1MB, keep 2 entries)
rotate-context

# Custom file and limits
rotate-context --file mycontext.md --size 2097152 --keep 3

# Capture overflow filename
OVERFLOW=$(rotate-context --file context.md)
if [ $? -eq 0 ]; then
    echo "Created overflow: $OVERFLOW"
fi
```

## Entry Format

Each entry in the context file follows this structure:

```
---
date: 2026-01-25T13:44:33+0000
hash: KQjNYowLItHmgLl89cEJ4/5D+IMB3nkezcnIkaOTe2Q=
agent: CLI/1.0
model: gpt-4
session: abc123
startCommit: a1b2c3d4
---

Body text goes here.
Can contain multiple lines.
Any characters or whitespace.

EOF

```

**Notes:**
- Blank line required between entries
- `EOF` marker must be on its own line
- `session` and `startCommit` fields are optional
- Body text is hashed for integrity verification

## Installation

```bash
chmod +x add-context rotate-context
# Optionally move to PATH
sudo mv add-context rotate-context /usr/local/bin/
```

## Workflow Example

```bash
# Add entries throughout the day
add-context --agent "MyApp/1.0" --model "gpt-4" "Morning context"
add-context --agent "MyApp/1.0" --model "gpt-4" "Afternoon update"
add-context --agent "MyApp/1.0" --model "gpt-4" "Evening notes"

# Rotate when needed (manually or via cron)
rotate-context

# Or integrate rotation into your workflow
if rotate-context --size 500000 --keep 5; then
    echo "Rotated context to: $(rotate-context --size 500000 --keep 5)"
fi
```

## Integration Ideas

**Manual rotation:**
```bash
# Check and rotate when needed
rotate-context || echo "No rotation needed"
```

**Automated rotation (cron):**
```bash
# Add to crontab to check daily
0 0 * * * /path/to/rotate-context --file /path/to/context.md
```

**Post-add hook:**
```bash
# Create wrapper script
add-context "$@" && rotate-context
```

## Dependencies

- bash
- openssl (for SHA-256 hashing)
- git (optional, for startCommit field)
- Standard Unix tools: awk, sed, grep, stat

## Platform Notes

**macOS vs Linux:**
The scripts handle platform differences in `stat` command automatically:
- macOS: `stat -f%z`
- Linux: `stat -c%s`

## Exit Codes

**add-context:**
- `0` - Success
- `1` - Invalid arguments or missing required parameters
- `2` - File errors

**rotate-context:**
- `0` - Rotation performed (overflow filename printed to stdout)
- `1` - No rotation needed (file under size limit or insufficient entries)
- `2` - Error (file not found, etc.)
