# Sentient Printer — CLAUDE.md

## What Is This?
A virtual printer driver for macOS powered by an LLM. It installs as a regular printer on the system. When you print to it, the LLM reads the document, generates personality-driven commentary, appends a commentary page, and either forwards to your real printer or saves a PDF to your Desktop.

The fun IS the product. This is a humor/personality project with viral potential, not enterprise software.

## Examples
- Print a long work report → footer: "Is this the life 10-year-old you wanted?"
- Print something embarrassing → extra page: "Shred this immediately"
- Print a resume → "You've got this. But fix the typo on page 2."
- Print directions → "Your phone exists."
- 47th slide deck revision → "I'm sure THIS one is the winner."
- Print an email chain → "This could have been resolved in one message."

## Architecture

### Platform: macOS only (for now)
macOS uses CUPS natively. This makes the install clean.

### How It Works
```
User App → Print → "Sentient Printer" (CUPS virtual printer) → LLM → Modified PDF → Real Printer / Desktop PDF
```

1. **CUPS filter** — A custom CUPS filter (Python script) registered as a virtual printer
2. **Text extraction** — `pypdf` extracts readable text from the print job (pure Python, no external deps)
3. **LLM call** — Send extracted text to an LLM API with a personality system prompt. Support:
   - Cloud: OpenAI (default), Anthropic — configurable API key
   - Local: Ollama — for privacy/offline use
4. **PDF modification** — Using `fpdf2` to generate a commentary page + `pypdf` to merge it into the original document
5. **Desktop notification** — macOS notification with commentary snippet via `osascript`
6. **Output** — Either forward to real printer (SentientPrinter) or save PDF to Desktop (SentientPDF)

### Two Printer Modes
- **SentientPrinter** — Enhances and forwards to a real physical printer
- **SentientPDF** — Enhances and saves to `~/Desktop/<title>_sentient.pdf` (no forwarding)
- Install supports PDF-only mode (skip real printer selection)

### CUPS Filter Pipeline
Our filter at `/usr/local/libexec/cups/filter/sentient-printer-filter`:
- Receives the print job from CUPS
- Extracts text via pypdf
- Calls LLM with personality prompt
- Appends commentary page
- Sends notification to user's desktop
- Writes enhanced PDF to stdout (CUPS pipeline) and/or saves to Desktop
- **Fail-open**: any error passes the original PDF through unmodified

PPD uses absolute path: `/usr/local/libexec/cups/filter/sentient-printer-filter`
(SIP blocks `/usr/libexec/`, so we use `/usr/local/libexec/`)

### CUPS Execution Context
CUPS filters run as the `_lp` user on macOS, NOT as your user. This matters:
- Filter scripts must be executable by `_lp` (permissions: `755`, owner: `root`)
- Python venv at `/usr/local/lib/sentient-printer/venv/` owned by root
- Config file at `/usr/local/etc/sentient-printer.yaml` (chmod 600 — protects API key)
- Sudoers rule at `/etc/sudoers.d/sentient-printer` grants `_lp` permission to run `cp`, `test`, `osascript` as the printing user (needed for PDF saving and notifications)
- Logs go to CUPS error log (`/var/log/cups/error_log`) via stderr

### Fail-Open Requirement
**Never lose a print job.** If anything fails — LLM timeout, API error, PDF modification crash — the filter MUST forward the original unmodified document. Wrap the entire enhance pipeline in a try/except that falls back to passthrough.

### Project Structure
```
sentient-printer/
├── CLAUDE.md                 # This file
├── install.sh                # Installer script (auto-installs deps via Homebrew)
├── uninstall.sh              # Clean removal
├── sentient-printer           # CLI tool (configure, test, status)
├── requirements.txt          # Python deps: pypdf, fpdf2, requests, pyyaml
├── Formula/
│   └── sentient-printer.rb   # Homebrew formula
├── src/
│   ├── filter.py             # Main CUPS filter — receives job, calls LLM, modifies PDF
│   ├── llm.py                # LLM client (OpenAI / Anthropic / Ollama via requests)
│   ├── pdf_tools.py          # PDF text extraction (pypdf) + modification (fpdf2)
│   ├── personalities.py      # System prompts for each personality (6 built-in + custom)
│   └── config.py             # Config management (YAML, sane defaults)
├── ppd/
│   └── sentient-printer.ppd  # Printer description file for CUPS
├── config/
│   └── sentient-printer.yaml # Default/example config
└── tests/
    ├── conftest.py           # Shared fixtures
    ├── test_filter.py        # PDF tools + filter tests
    └── test_llm.py           # LLM client + personality tests
```

### Config File (sentient-printer.yaml)
```yaml
real_printer: ""                  # CUPS name of real printer (blank for PDF-only)
personality: "passive-aggressive"  # Which personality to use

llm:
  provider: "openai"              # openai | anthropic | ollama
  model: ""                       # Leave empty for provider default
  api_key: ""                     # Required for openai/anthropic
  base_url: ""                    # Only needed for custom endpoints / ollama
```

### Personalities
6 built-in + custom:
- **passive-aggressive** — Corporate snark
- **existential** — Questions the meaning of printing
- **supportive** — Wholesome encouragement
- **eco-guilt** — Environmental shame
- **judgy** — Pure judgment
- **unhinged** — Chaotic energy
- **custom** — User provides their own system prompt in config

### Install Flow
```bash
sudo ./install.sh
# 1. Auto-installs Python 3 and poppler via Homebrew if missing
# 2. Creates venv + installs Python deps
# 3. Copies filter to /usr/local/libexec/cups/filter/
# 4. Installs PPD and config
# 5. Adds sudoers rule for _lp user
# 6. Prompts: real printer (or blank for PDF-only), personality, LLM provider + API key
# 7. Registers CUPS printers (SentientPrinter and/or SentientPDF)
```

### Key Commands
```bash
# Install / Uninstall
sudo ./install.sh
sudo ./uninstall.sh

# CLI tool
sentient-printer configure     # Interactive setup
sentient-printer test file.pdf # Test pipeline without printing
sentient-printer status        # Show config

# Print
lp -d SentientPrinter file.pdf  # Print with commentary
lp -d SentientPDF file.pdf      # Save roasted PDF to Desktop

# Debug
tail -f /var/log/cups/error_log | grep SENTIENT

# Homebrew (once tap is published)
brew tap CharlieMc0/tap
brew install sentient-printer
```

## Tech Stack
- **Language:** Python 3
- **PDF generation:** fpdf2 (generates commentary page)
- **PDF merging + text extraction:** pypdf (pure Python, no external deps)
- **LLM:** OpenAI (default), Anthropic, Ollama — all via `requests` (no SDK deps)
- **Notifications:** osascript (built into macOS)
- **Config:** YAML (pyyaml)
- **Print system:** CUPS (native macOS)
- **Distribution:** Homebrew tap at CharlieMc0/homebrew-tap

## Repo
- GitHub: CharlieMc0/sentient-printer
- Homebrew tap: CharlieMc0/homebrew-tap
- License: MIT
- Parent: Lugh Labs LLC

## macOS SIP Gotchas
- `/usr/libexec/cups/filter/` is SIP-protected — use `/usr/local/libexec/cups/filter/`
- `/usr/share/ppd/` is SIP-protected — use `/usr/local/share/ppd/`
- `/usr/local/etc/` may not exist — create with `mkdir -p` before writing config
- PPD must use **absolute path** to filter (CUPS won't find it by name in /usr/local/)
- `sudo -H` flag needed when running pip to avoid cache ownership warnings

## Post-MVP Roadmap
1. **Network/AirPrint mode** — Share printer over local network via CUPS + Bonjour
2. **Config UI** — Menu bar app for personality/API key management
3. **.pkg installer** — For non-technical users

## Vibe
This is a fun weekend project that should make people laugh. Keep the code simple, the personalities sharp, and the README entertaining. The demo video of someone printing a doc and getting roasted is the marketing.
