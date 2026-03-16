#!/bin/bash
set -e

# Quick dev setup — no sudo, no CUPS, just get running
# Usage: ./dev-setup.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo ""
echo "🖨️  Sentient Printer — Dev Setup"
echo ""

# Check deps
for cmd in python3 pdftotext; do
    if command -v "$cmd" &>/dev/null; then
        echo "✓ $cmd"
    else
        echo "✗ $cmd not found"
        [[ "$cmd" == "pdftotext" ]] && echo "  Install: brew install poppler"
        [[ "$cmd" == "python3" ]] && echo "  Install: brew install python3"
        exit 1
    fi
done

# Create venv
if [[ ! -d "$VENV_DIR" ]]; then
    echo ""
    echo "Creating venv..."
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"
"$VENV_DIR/bin/pip" install --quiet pytest
echo "✓ Dependencies installed"

# Write dev config if missing
CONFIG="$SCRIPT_DIR/config/sentient-printer.yaml"
if [[ ! -s "$CONFIG" ]] || grep -q 'api_key: ""' "$CONFIG" 2>/dev/null; then
    echo ""
    echo "Config: $CONFIG"
    echo "  Set your API key and personality there before testing."
fi

# Run tests
echo ""
echo "Running tests..."
"$VENV_DIR/bin/python3" -m pytest tests/ -v

echo ""
echo "✅ Ready! Test it:"
echo ""
echo "  .venv/bin/python3 sentient-printer test /path/to/any.pdf"
echo ""
echo "  Or run the full install (needs sudo + macOS):"
echo "  sudo ./install.sh"
echo ""
