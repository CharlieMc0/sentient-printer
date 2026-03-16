#!/bin/bash
set -e

# Sentient Printer Uninstaller

INSTALL_DIR="/usr/local/lib/sentient-printer"
CONFIG_PATH="/usr/local/etc/sentient-printer.yaml"
FILTER_PATH="/usr/local/libexec/cups/filter/sentient-printer-filter"
PPD_DIR="/usr/local/share/ppd/sentient-printer"
PRINTER_NAME="SentientPrinter"
PDF_PRINTER_NAME="SentientPDF"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo ""
echo "🖨️  Sentient Printer Uninstaller"
echo ""

if [[ $EUID -ne 0 ]]; then
    echo "Re-running with sudo..."
    exec sudo "$0" "$@"
fi

# Remove CUPS printers
for P in "$PRINTER_NAME" "$PDF_PRINTER_NAME"; do
    if lpstat -p "$P" &>/dev/null; then
        lpadmin -x "$P"
        echo -e "${GREEN}✓${NC} Removed CUPS printer '$P'"
    else
        echo "  Printer '$P' not found in CUPS (already removed)"
    fi
done

# Remove filter
if [[ -f "$FILTER_PATH" ]]; then
    rm "$FILTER_PATH"
    echo -e "${GREEN}✓${NC} Removed CUPS filter"
fi

# Remove PPD
if [[ -d "$PPD_DIR" ]]; then
    rm -rf "$PPD_DIR"
    echo -e "${GREEN}✓${NC} Removed PPD files"
fi

# Remove installed files and venv
if [[ -d "$INSTALL_DIR" ]]; then
    rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}✓${NC} Removed $INSTALL_DIR"
fi

# Remove config
if [[ -f "$CONFIG_PATH" ]]; then
    rm "$CONFIG_PATH"
    echo -e "${GREEN}✓${NC} Removed config file"
fi

# Remove sudoers rule
SUDOERS_FILE="/etc/sudoers.d/sentient-printer"
if [[ -f "$SUDOERS_FILE" ]]; then
    rm "$SUDOERS_FILE"
    echo -e "${GREEN}✓${NC} Removed sudoers rule"
fi

echo ""
echo -e "${GREEN}✅ Sentient Printer uninstalled.${NC}"
echo "   Your printer no longer has opinions."
echo ""
