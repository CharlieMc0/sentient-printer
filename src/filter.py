#!/usr/bin/env python3
"""Sentient Printer CUPS filter.

CUPS filter interface:
    filter job-id user title copies options [filename]

If filename is provided, read from it. Otherwise read from stdin.
Output the (possibly modified) PDF to stdout.
Log to stderr (CUPS routes this to error_log).
"""

import os
import subprocess
import sys
import shutil
import tempfile

# Activate venv if running from installed location
VENV_PATH = "/usr/local/lib/sentient-printer/venv"
if os.path.exists(VENV_PATH):
    site_packages = os.path.join(
        VENV_PATH, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"
    )
    if os.path.exists(site_packages):
        sys.path.insert(0, site_packages)

# Add src directory to path for imports
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


def log(msg: str) -> None:
    """Log to stderr (CUPS error_log)."""
    print(f"SENTIENT-PRINTER: {msg}", file=sys.stderr)


def notify(user: str, commentary: str, title: str = "document") -> None:
    """Send a macOS desktop notification with the commentary."""
    # Truncate for notification display
    short = commentary[:150] + ("..." if len(commentary) > 150 else "")
    # Escape quotes for AppleScript
    short = short.replace("\\", "\\\\").replace('"', '\\"')
    title_safe = title.replace("\\", "\\\\").replace('"', '\\"')

    script = (
        f'display notification "{short}" '
        f'with title "🖨️ Your Printer Has Thoughts" '
        f'subtitle "{title_safe}"'
    )

    try:
        # Run as the printing user so it hits their notification center
        cmd = ["sudo", "-u", user, "osascript", "-e", script] if user else ["osascript", "-e", script]
        subprocess.run(cmd, timeout=5, capture_output=True)
        log("Notification sent")
    except Exception as e:
        log(f"Notification failed (non-fatal): {e}")


def passthrough(input_path: str) -> None:
    """Pass the original PDF through to stdout unmodified."""
    with open(input_path, "rb") as f:
        shutil.copyfileobj(f, sys.stdout.buffer)


def enhance(input_path: str, pdf_mode: bool = False, title: str = "document", user: str = "") -> None:
    """Run the enhancement pipeline: extract text, get commentary, append page."""
    from config import load_config
    from llm import get_commentary
    from pdf_tools import extract_text, append_commentary

    config = load_config()
    personality = config.get("personality", "passive-aggressive")

    log(f"Processing print job with personality: {personality}")

    # Extract text
    text = extract_text(input_path)
    if not text.strip():
        log("No text extracted from document, passing through")
        passthrough(input_path)
        return

    log(f"Extracted {len(text)} chars from document")

    # Get LLM commentary
    commentary = get_commentary(text, personality, config)
    log(f"Got commentary: {commentary[:100]}...")

    # Desktop notification
    notify(user, commentary, title)

    # Create modified PDF
    output_path = input_path + ".enhanced.pdf"
    try:
        append_commentary(input_path, commentary, output_path)

        if pdf_mode:
            # Save to user's Desktop instead of forwarding to printer
            safe_title = "".join(c if c.isalnum() or c in " -_." else "_" for c in title).strip() or "print"
            # Resolve the printing user's home (filter runs as _lp, not the user)
            import pwd
            try:
                user_home = pwd.getpwnam(user).pw_dir if user else os.path.expanduser("~")
            except KeyError:
                user_home = os.path.expanduser("~")
            pdf_dir = config.get("pdf_output_dir", os.path.join(user_home, "Desktop"))
            os.makedirs(pdf_dir, exist_ok=True)
            dest = os.path.join(pdf_dir, f"{safe_title}_sentient.pdf")
            # Avoid overwriting existing files
            counter = 1
            while os.path.exists(dest):
                dest = os.path.join(pdf_dir, f"{safe_title}_sentient_{counter}.pdf")
                counter += 1
            shutil.copy2(output_path, dest)
            log(f"PDF saved to {dest}")

        # Always write to stdout for CUPS pipeline
        with open(output_path, "rb") as f:
            shutil.copyfileobj(f, sys.stdout.buffer)
        log("Enhanced PDF written to stdout")
    finally:
        try:
            os.unlink(output_path)
        except OSError:
            pass


def main() -> None:
    # Parse CUPS filter arguments
    # filter job-id user title copies options [filename]
    if len(sys.argv) < 6:
        log(f"Usage: {sys.argv[0]} job-id user title copies options [filename]")
        sys.exit(1)

    job_id = sys.argv[1]
    user = sys.argv[2]
    title = sys.argv[3]

    # Detect PDF-only mode — CUPS sets PRINTER env var for the destination printer
    printer_name = os.environ.get("PRINTER", "")
    pdf_mode = "pdf" in printer_name.lower()

    log(f"Job {job_id} from {user}: {title} (printer={printer_name}, pdf_mode={pdf_mode})")

    # Get input PDF — from filename arg or stdin
    tmp_input = None
    if len(sys.argv) >= 7:
        input_path = sys.argv[6]
    else:
        # Read from stdin to a temp file
        tmp_input = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        shutil.copyfileobj(sys.stdin.buffer, tmp_input)
        tmp_input.close()
        input_path = tmp_input.name

    try:
        # Fail-open: if anything goes wrong, pass the original through
        try:
            enhance(input_path, pdf_mode=pdf_mode, title=title, user=user)
        except Exception as e:
            log(f"Enhancement failed ({type(e).__name__}: {e}), passing through original")
            passthrough(input_path)
    finally:
        if tmp_input:
            try:
                os.unlink(tmp_input.name)
            except OSError:
                pass


if __name__ == "__main__":
    main()
