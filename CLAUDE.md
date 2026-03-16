# Sentient Printer — CLAUDE.md

## What Is This?
A virtual printer driver for macOS powered by an LLM. It installs as a regular printer on the system. When you print to it, the LLM reads the document, generates personality-driven commentary, modifies the output (appends a page, adds a footer, etc.), and forwards the job to your real physical printer.

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
User App → Print → "Sentient Printer" (CUPS virtual printer) → LLM → Modified PDF → Real Printer
```

1. **CUPS backend/filter** — A custom CUPS filter (Python script) registered as a virtual printer
2. **Text extraction** — `pdftotext` (poppler-utils) extracts readable text from the print job (arrives as PDF/PostScript). This is a hard dependency — pypdf text extraction is unreliable on real-world PDFs.
3. **LLM call** — Send extracted text to an LLM API with a personality system prompt. Support:
   - Cloud: OpenAI (default), Anthropic — configurable API key
   - Local: Ollama — for privacy/offline use
4. **PDF modification** — Using `fpdf2` to generate a commentary page + `pypdf` to merge it into the original document:
   - Append an extra page with the commentary (only mode for MVP)
5. **Forward to real printer** — Send the modified PDF to the user's actual printer via CUPS (the real printer is configured during setup)

### CUPS Filter Pipeline
CUPS filters are scripts that process print jobs in a pipeline. Our filter:
- Receives the print job from CUPS
- Converts to PDF if needed (PostScript → PDF via `ps2pdf`)
- Extracts text
- Calls LLM
- Modifies PDF
- Passes to the next filter / backend for the real printer

Filter location: `/usr/libexec/cups/filter/` or `/usr/local/lib/cups/filter/`
Backend location: `/usr/libexec/cups/backend/` or `/usr/local/lib/cups/backend/`

PPD file defines the virtual printer's capabilities.

### CUPS Execution Context
CUPS filters run as the `_lp` user on macOS, NOT as your user. This matters:
- Filter scripts must be executable by `_lp` (permissions: `755`, owner: `root`)
- Python dependencies must be installed system-wide or in a venv accessible to `_lp`
- The install script handles this by creating a venv at `/usr/local/lib/sentient-printer/venv/` owned by root, and the filter script activates it
- Config file at `/usr/local/etc/sentient-printer.yaml` must be readable by `_lp`
- Logs go to CUPS error log (`/var/log/cups/error_log`) via stderr — the filter should log there

### Fail-Open Requirement
**Never lose a print job.** If anything fails — LLM timeout, API error, PDF modification crash — the filter MUST forward the original unmodified document to the real printer. The user chose to print something; we don't get to eat it. Wrap the entire enhance pipeline in a try/except that falls back to passthrough.

### Project Structure
```
sentient-printer/
├── CLAUDE.md              # This file
├── README.md              # User-facing docs
├── install.sh             # Installer script
├── uninstall.sh           # Clean removal
├── src/
│   ├── filter.py          # Main CUPS filter — receives job, calls LLM, modifies PDF
│   ├── llm.py             # LLM client (OpenAI / Anthropic / Ollama)
│   ├── pdf_tools.py       # PDF text extraction + modification
│   ├── personalities.py   # System prompts for each personality
│   └── config.py          # Config management (real printer, personality, API settings)
├── ppd/
│   └── sentient-printer.ppd  # Printer description file for CUPS
├── config/
│   └── sentient-printer.yaml # User config (real printer name, personality, API key, etc.)
└── tests/
    ├── test_filter.py
    ├── test_llm.py
    └── sample_docs/       # Sample PDFs for testing
```

### Config File (sentient-printer.yaml)
MVP config is intentionally minimal — 3 things the user must decide, everything else has sane defaults.
```yaml
real_printer: "HP_LaserJet_Pro"   # CUPS name of the real printer to forward to
personality: "passive-aggressive"  # Which personality to use

llm:
  provider: "openai"              # openai | anthropic | ollama
  model: "gpt-4o"                # Model name (default per provider)
  api_key: ""                     # Required for openai/anthropic, ignored for ollama
  base_url: ""                    # Only needed for ollama (default: http://localhost:11434)
```

### Personalities (System Prompts)
Each personality is a system prompt that instructs the LLM how to comment on printed documents. Ship with several built-in:

- **passive-aggressive** — Corporate snark. "Per my previous print job..."
- **existential** — Questions the meaning of printing. "Another document enters the void."
- **supportive** — Wholesome encouragement. "Great work on this!"
- **eco-guilt** — Environmental shame. "This killed 0.3 trees."
- **judgy** — Pure judgment. "Really? You're printing THIS?"
- **unhinged** — Chaotic energy. No filter.
- **custom** — User provides their own system prompt

### Install Flow
```bash
# User runs:
./install.sh

# Script does:
# 1. Check dependencies (Python 3, cups, pdftotext)
# 2. Install Python deps (pypdf, fpdf2, requests, pyyaml)
# 3. Copy filter script to CUPS filter directory
# 4. Copy PPD file
# 5. Register virtual printer with lpadmin
# 6. Prompt: "Select your real printer:" (list from lpstat)
# 7. Prompt: "Choose a personality:" (list options)
# 8. Prompt: "LLM provider:" (openai/anthropic/ollama)
# 9. Write config file
# 10. Enable printer
# "Sentient Printer" now appears in System Settings → Printers
```

### Key Commands Reference
```bash
# List existing printers
lpstat -p -d

# Add a CUPS printer with custom backend
lpadmin -p SentientPrinter -E -v "sentient://localhost" -P /path/to/sentient-printer.ppd

# Remove
lpadmin -x SentientPrinter

# Restart CUPS
sudo launchctl stop org.cups.cupsd && sudo launchctl start org.cups.cupsd

# Test print
lp -d SentientPrinter /path/to/test.pdf
```

## MVP Scope
Build the simplest working version first:

1. ✅ CUPS filter that intercepts print jobs
2. ✅ Extract text from PDF via pdftotext (poppler)
3. ✅ Call OpenAI with one personality (Ollama/Anthropic as secondary)
4. ✅ Append a commentary page to the PDF (fpdf2 + pypdf)
5. ✅ Forward to real printer — fail open on any error
6. ✅ Install script that sets it all up (venv, permissions, CUPS registration)
7. ✅ At least 3 personalities
8. ✅ Log to CUPS error log via stderr

### Out of Scope for MVP
- Network/AirPrint mode (Phase 2 — see below)
- Windows/Linux support
- GUI settings app
- App Store distribution
- Homebrew formula

### Post-MVP: Network Printer Mode (Phase 2 — Top Priority)

**The killer feature.** One Mac runs Sentient Printer. Every device on the network sees it as a regular printer — iPhones, iPads, other Macs, Windows laptops. Zero install on client devices.

This turns it from a solo novelty into a shared experience. Set it up in an office, don't tell anyone, and wait. The comedy writes itself. This is the viral mechanic — the install funnel collapses from "every person installs" to "one person installs and an entire office gets pranked."

#### How it works
- CUPS already speaks IPP (Internet Printing Protocol)
- macOS has Bonjour/mDNS built in
- Sharing a CUPS printer over the network is mostly `cupsctl --share-printers` + Bonjour TXT records for AirPrint discovery
- iPhones/iPads discover AirPrint printers automatically — zero config on the client side
- The Sentient Printer just needs to advertise itself as an AirPrint-compatible shared printer

#### Implementation
1. Enable CUPS printer sharing (`cupsctl --share-printers`)
2. Register Bonjour service with the right AirPrint TXT records (`_ipp._tcp`, `_universal._sub._ipp._tcp`)
3. Ensure the virtual printer's PPD advertises PDF/image MIME types AirPrint expects
4. The install script gets a `--network` flag (or the config UI has a toggle)
5. Optional: mDNS advertisement via `dns-sd` or `avahi` for broader compatibility

#### What this enables
- **Office prank mode:** Install on one Mac, every printer in the building gets sentient
- **Home mode:** Family prints from phones/tablets, gets roasted
- **Demo mode:** Show it off at a meetup — anyone can print to it from their phone
- No app install, no accounts, no setup on client devices. It just appears.

### Post-MVP: Distribution & Config UI

#### Homebrew Formula (Phase 2)
The goal is `brew install sentient-printer` and you're done. Homebrew handles:
- Installing Python deps into a sandboxed prefix
- Installing poppler (for pdftotext) as a dependency
- Copying the CUPS filter + PPD to the right locations
- Running `lpadmin` to register the virtual printer via a post-install script
- A `sentient-printer configure` CLI command for first-time setup (pick real printer, enter API key, choose personality)

Homebrew is the right first distribution channel — this is a macOS CLI tool for a technical audience.

#### Config UI (Phase 2-3)
A lightweight macOS menu bar app (Python + rumps, or Swift) that:
- Lives in the menu bar with a printer icon
- Lets you pick personality from a dropdown
- Enter/change API key
- Select real printer (populated from `lpstat`)
- Toggle the printer on/off
- Shows recent print job commentary (fun to re-read)

This is what makes it feel like an "app" instead of a hacker tool. The menu bar app just reads/writes the same YAML config file — no new backend needed.

#### Possible: .pkg Installer (Phase 3)
A macOS `.pkg` installer for non-technical users. Double-click, grant permissions, done. This is the path to broader distribution but adds signing/notarization complexity. Only worth it if the project gets traction.

## Tech Stack
- **Language:** Python 3
- **PDF generation:** fpdf2 (lightweight, generates the commentary page)
- **PDF merging:** pypdf (merge commentary page into original doc)
- **Text extraction:** pdftotext (poppler-utils) — hard dependency, no fallback
- **LLM:** OpenAI (default), Anthropic, Ollama (local/offline)
- **Config:** YAML (minimal — 3 required fields for MVP)
- **Print system:** CUPS (native macOS)

## Repo
- GitHub: CharlieMc0 (to be created)
- License: MIT
- Parent: Lugh Labs LLC

## Vibe
This is a fun weekend project that should make people laugh. Keep the code simple, the personalities sharp, and the README entertaining. The demo video of someone printing a doc and getting roasted is the marketing.
