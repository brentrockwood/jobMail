#!/usr/bin/env bash
#
# Security scan script for JobMail
# Checks for leaked secrets, API keys, tokens, and other sensitive information
#
# Exit codes:
#   0 - No issues found
#   1 - Security issues detected
#   2 - Script error

set -eo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "JobMail Security Scanner"
echo "========================"
echo ""
echo "Scanning directory: $PROJECT_ROOT"
echo ""

ISSUES_FOUND=0

# Pattern categories to scan for (category|pattern pairs)
PATTERNS=(
    "API_Keys|(api[_-]?key|apikey|api[_-]?secret)['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9_-]{20,}"
    "AWS_Keys|(aws[_-]?access[_-]?key[_-]?id|aws[_-]?secret[_-]?access[_-]?key)['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{20,}"
    "Private_Keys|-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----"
    "Tokens|(token|auth[_-]?token|access[_-]?token)['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9_.-]{20,}"
    "Passwords|(password|passwd|pwd)['\"]?\s*[:=]\s*['\"]?[^'\"\s]{8,}"
    "OpenAI_Keys|sk-[A-Za-z0-9]{48}"
    "Anthropic_Keys|sk-ant-[A-Za-z0-9-]{95}"
    "Database_URLs|(postgres|mysql|mongodb):\/\/[^\s'\"]*:[^\s'\"]*@"
    "Email_Addresses|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}"
    "IP_Addresses|([0-9]{1,3}\.){3}[0-9]{1,3}"
)

# Files and directories to exclude
EXCLUDE_PATTERNS=(
    ".git"
    "__pycache__"
    "*.pyc"
    "node_modules"
    ".venv"
    "venv"
    ".env.example"
    "secrets.env.example"
    "*_test.py"
    "test_*.py"
    "*.md"
    "security_scan.sh"
    "*.json"
)

# Build grep exclude arguments
GREP_EXCLUDES=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    GREP_EXCLUDES="$GREP_EXCLUDES --exclude=$pattern"
done
GREP_EXCLUDES="$GREP_EXCLUDES --exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=venv"

# Function to scan for a pattern
scan_pattern() {
    local category=$1
    local pattern=$2
    local results
    
    # Use grep to find matches
    results=$(cd "$PROJECT_ROOT" && grep -rn -E -i $GREP_EXCLUDES "$pattern" . 2>/dev/null || true)
    
    if [ -n "$results" ]; then
        # Replace underscores with spaces for display
        local display_category="${category//_/ }"
        echo -e "${RED}✗ Found potential $display_category:${NC}"
        echo "$results" | sed 's/^/  /'
        echo ""
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
}

# Check for files that should be gitignored
echo "Checking for sensitive files..."
SENSITIVE_FILES=(
    "secrets.env"
    "credentials.json"
    "token.json"
    "*.pem"
    "*.key"
    "*.p12"
    "*.pfx"
    "id_rsa"
    "id_dsa"
)

for file_pattern in "${SENSITIVE_FILES[@]}"; do
    found_files=$(cd "$PROJECT_ROOT" && find . -name "$file_pattern" -not -path "./.git/*" -not -path "./.venv/*" -not -path "./venv/*" 2>/dev/null || true)
    if [ -n "$found_files" ]; then
        echo -e "${YELLOW}⚠ Found sensitive file(s): $file_pattern${NC}"
        echo "$found_files" | sed 's/^/  /'
        
        # Check if files are in .gitignore
        for file in $found_files; do
            if git check-ignore "$PROJECT_ROOT/$file" >/dev/null 2>&1; then
                echo -e "  ${GREEN}✓ File is properly gitignored${NC}"
            else
                echo -e "  ${RED}✗ WARNING: File is NOT gitignored!${NC}"
                ISSUES_FOUND=$((ISSUES_FOUND + 1))
            fi
        done
        echo ""
    fi
done

# Scan for each pattern category
echo "Scanning for sensitive patterns..."
for pattern_entry in "${PATTERNS[@]}"; do
    category="${pattern_entry%%|*}"
    pattern="${pattern_entry#*|}"
    scan_pattern "$category" "$pattern"
done

# Check if secrets.env or credentials.json are committed to git
echo "Checking git history for leaked secrets..."
LEAKED_FILES=$(cd "$PROJECT_ROOT" && git log --all --full-history --pretty=format: --name-only | grep -E "(secrets\.env|credentials\.json|token\.json|\.pem|\.key)" | grep -v "\.example" || true)
if [ -n "$LEAKED_FILES" ]; then
    echo -e "${RED}✗ Found sensitive files in git history:${NC}"
    echo "$LEAKED_FILES" | sort -u | sed 's/^/  /'
    echo ""
    echo -e "${YELLOW}NOTE: These files may have been committed in the past.${NC}"
    echo -e "${YELLOW}Consider using 'git filter-branch' or 'BFG Repo-Cleaner' to remove them.${NC}"
    echo ""
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
fi

# Summary
echo "================================"
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓ Security scan passed! No issues found.${NC}"
    exit 0
else
    echo -e "${RED}✗ Security scan found $ISSUES_FOUND issue(s).${NC}"
    echo ""
    echo "Please review the findings above and:"
    echo "1. Remove any hardcoded secrets from code"
    echo "2. Move secrets to secrets.env (gitignored)"
    echo "3. Ensure sensitive files are in .gitignore"
    echo "4. If secrets were committed, rotate them immediately"
    echo ""
    exit 1
fi
