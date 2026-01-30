#!/usr/bin/env bash
#
# Run all code quality checks for JobMail
# This script runs tests, linting, type checking, and security scanning
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              JobMail Code Quality Checks                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

FAILED_CHECKS=()
PASSED_CHECKS=()

# Function to run a check
run_check() {
    local name=$1
    local command=$2
    
    echo -e "${BLUE}▶ Running: $name${NC}"
    echo "────────────────────────────────────────────────────────────"
    
    if eval "$command"; then
        echo -e "${GREEN}✓ $name passed${NC}"
        PASSED_CHECKS+=("$name")
        echo ""
        return 0
    else
        echo -e "${RED}✗ $name failed${NC}"
        FAILED_CHECKS+=("$name")
        echo ""
        return 1
    fi
}

# Check 1: Security Scan
run_check "Security Scan" "$SCRIPT_DIR/security_scan.sh" || true

# Check 2: Code Formatting (Black)
run_check "Black (Code Formatting)" "black --check --diff src/ tests/ main.py" || true

# Check 3: Linting (Ruff)
run_check "Ruff (Linting)" "ruff check src/ tests/ main.py" || true

# Check 4: Type Checking (MyPy)
run_check "MyPy (Type Checking)" "mypy src/ main.py" || true

# Check 5: Unit Tests
run_check "Pytest (Unit Tests)" "pytest -v --tb=short" || true

# Summary
echo ""
echo "════════════════════════════════════════════════════════════"
echo "                    SUMMARY"
echo "════════════════════════════════════════════════════════════"
echo ""

if [ ${#PASSED_CHECKS[@]} -gt 0 ]; then
    echo -e "${GREEN}Passed checks (${#PASSED_CHECKS[@]}):${NC}"
    for check in "${PASSED_CHECKS[@]}"; do
        echo -e "  ${GREEN}✓${NC} $check"
    done
    echo ""
fi

if [ ${#FAILED_CHECKS[@]} -gt 0 ]; then
    echo -e "${RED}Failed checks (${#FAILED_CHECKS[@]}):${NC}"
    for check in "${FAILED_CHECKS[@]}"; do
        echo -e "  ${RED}✗${NC} $check"
    done
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo -e "${RED}Some checks failed. Please fix the issues above.${NC}"
    echo "════════════════════════════════════════════════════════════"
    exit 1
else
    echo "════════════════════════════════════════════════════════════"
    echo -e "${GREEN}All checks passed! 🎉${NC}"
    echo "════════════════════════════════════════════════════════════"
    exit 0
fi
