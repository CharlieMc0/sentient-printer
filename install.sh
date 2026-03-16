#!/bin/bash
set -e

# Sentient Printer Installer for macOS
# Installs the CUPS virtual printer, Python dependencies, and config

INSTALL_DIR="/usr/local/lib/sentient-printer"
CONFIG_PATH="/usr/local/etc/sentient-printer.yaml"
FILTER_DIR="/usr/libexec/cups/filter"
PPD_DIR="/usr/share/ppd/sentient-printer"
PRINTER_NAME="SentientPrinter"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "🖨️  Sentient Printer Installer"
echo "   Your printer is about to get opinions."
echo ""

# --- Pre-flight checks ---

if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}Error: Sentient Printer requires macOS.${NC}"
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo -e "${YELLOW}This installer needs sudo access to install CUPS components.${NC}"
    echo "Re-running with sudo..."
    exec sudo "$0" "$@"
fi

# Check/install Python 3
if ! command -v python3 &>/dev/null; then
    echo -e "${YELLOW}Python 3 not found. Installing via Homebrew...${NC}"
    if command -v brew &>/dev/null; then
        sudo -u "${SUDO_USER:-$USER}" brew install python3
    else
        echo -e "${RED}Error: Homebrew not found. Install Python 3 manually.${NC}"
        exit 1
    fi
fi
PYTHON_VERSION=$(python3 --version 2>&1)
echo -e "${GREEN}✓${NC} Found $PYTHON_VERSION"

# Check/install pdftotext (poppler)
if ! command -v pdftotext &>/dev/null; then
    echo -e "${YELLOW}pdftotext not found. Installing poppler via Homebrew...${NC}"
    if command -v brew &>/dev/null; then
        sudo -u "${SUDO_USER:-$USER}" brew install poppler
    else
        echo -e "${RED}Error: Homebrew not found. Install poppler manually: https://poppler.freedesktop.org/${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓${NC} Found pdftotext (poppler)"

# Check CUPS
if ! command -v lpstat &>/dev/null; then
    echo -e "${RED}Error: CUPS not found. It should be built into macOS.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Found CUPS"

echo ""

# --- Interactive setup ---

# Select real printer
echo "Available printers:"
echo "---"
lpstat -p 2>/dev/null | sed 's/^printer /  /' | sed 's/ is.*$//' || true
echo "---"
echo ""
read -rp "Enter the name of your REAL printer to forward jobs to: " REAL_PRINTER

if [[ -z "$REAL_PRINTER" ]]; then
    echo -e "${RED}Error: You must specify a real printer.${NC}"
    exit 1
fi

# Verify printer exists
if ! lpstat -p "$REAL_PRINTER" &>/dev/null; then
    echo -e "${YELLOW}Warning: Printer '$REAL_PRINTER' not found in CUPS. Continuing anyway.${NC}"
fi

# Select personality
echo ""
echo "Choose a personality:"
echo "  1) passive-aggressive — Corporate snark"
echo "  2) existential — Questions the meaning of printing"
echo "  3) supportive — Wholesome encouragement"
echo "  4) eco-guilt — Environmental shame"
echo "  5) judgy — Pure judgment"
echo "  6) unhinged — Chaotic energy"
echo ""
read -rp "Enter number [1]: " PERSONALITY_NUM

case "${PERSONALITY_NUM:-1}" in
    1) PERSONALITY="passive-aggressive" ;;
    2) PERSONALITY="existential" ;;
    3) PERSONALITY="supportive" ;;
    4) PERSONALITY="eco-guilt" ;;
    5) PERSONALITY="judgy" ;;
    6) PERSONALITY="unhinged" ;;
    *) PERSONALITY="passive-aggressive" ;;
esac
echo -e "${GREEN}✓${NC} Personality: $PERSONALITY"

# Select LLM provider
echo ""
echo "LLM Provider:"
echo "  1) openai — OpenAI API (default, requires API key)"
echo "  2) anthropic — Anthropic API (requires API key)"
echo "  3) ollama — Local Ollama (no API key needed)"
echo ""
read -rp "Enter number [1]: " PROVIDER_NUM

case "${PROVIDER_NUM:-1}" in
    1) PROVIDER="openai" ;;
    2) PROVIDER="anthropic" ;;
    3) PROVIDER="ollama" ;;
    *) PROVIDER="openai" ;;
esac

API_KEY=""
if [[ "$PROVIDER" != "ollama" ]]; then
    echo ""
    read -rp "Enter your $PROVIDER API key: " API_KEY
    if [[ -z "$API_KEY" ]]; then
        echo -e "${YELLOW}Warning: No API key provided. You'll need to add it to $CONFIG_PATH later.${NC}"
    fi
fi
echo -e "${GREEN}✓${NC} Provider: $PROVIDER"

echo ""
echo "--- Installing ---"

# --- Install files ---

# Create install directory and venv
mkdir -p "$INSTALL_DIR"
echo "Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"
echo -e "${GREEN}✓${NC} Python dependencies installed"

# Copy source files
cp "$SCRIPT_DIR/src/"*.py "$INSTALL_DIR/"
echo -e "${GREEN}✓${NC} Source files copied to $INSTALL_DIR"

# Install CUPS filter
mkdir -p "$FILTER_DIR"
cat > "$FILTER_DIR/sentient-printer-filter" << 'FILTER_WRAPPER'
#!/bin/bash
# Sentient Printer CUPS filter wrapper
# Activates the venv and runs the Python filter
VENV="/usr/local/lib/sentient-printer/venv"
export PATH="$VENV/bin:$PATH"
exec "$VENV/bin/python3" /usr/local/lib/sentient-printer/filter.py "$@"
FILTER_WRAPPER
chmod 755 "$FILTER_DIR/sentient-printer-filter"
echo -e "${GREEN}✓${NC} CUPS filter installed"

# Install PPD
mkdir -p "$PPD_DIR"
cp "$SCRIPT_DIR/ppd/sentient-printer.ppd" "$PPD_DIR/"
echo -e "${GREEN}✓${NC} PPD file installed"

# Write config
cat > "$CONFIG_PATH" << CONFIGEOF
# Sentient Printer Configuration
real_printer: "$REAL_PRINTER"
personality: "$PERSONALITY"

llm:
  provider: "$PROVIDER"
  model: ""
  api_key: "$API_KEY"
  base_url: ""
CONFIGEOF
chmod 600 "$CONFIG_PATH"
echo -e "${GREEN}✓${NC} Config written to $CONFIG_PATH"

# --- Register CUPS printer ---

# Remove existing if present
lpadmin -x "$PRINTER_NAME" 2>/dev/null || true

# Register the virtual printer
lpadmin -p "$PRINTER_NAME" \
    -E \
    -v "file:///dev/null" \
    -P "$PPD_DIR/sentient-printer.ppd" \
    -D "Sentient Printer" \
    -L "Your printer, but with opinions"
echo -e "${GREEN}✓${NC} CUPS printer '$PRINTER_NAME' registered"

# Enable
cupsenable "$PRINTER_NAME" 2>/dev/null || true
cupsaccept "$PRINTER_NAME" 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ Sentient Printer installed!${NC}"
echo ""
echo "It should now appear in System Settings → Printers & Scanners."
echo "To test: lp -d $PRINTER_NAME /path/to/any.pdf"
echo ""
echo "Config file: $CONFIG_PATH"
echo "To change personality or API key, edit the config and reprint."
echo ""
echo "To uninstall: sudo ./uninstall.sh"
