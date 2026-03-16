class SentientPrinter < Formula
  desc "A virtual printer that roasts your documents with AI commentary"
  homepage "https://github.com/CharlieMc0/sentient-printer"
  url "https://github.com/CharlieMc0/sentient-printer/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "0019dfc4b32d63c1392aa264aed2253c1e0c2fb09216f8e2cc269bbfb8bb49b5"
  license "MIT"

  depends_on "poppler"   # for pdftotext
  depends_on "python@3"

  def install
    # Install Python deps into a self-contained venv
    venv = libexec/"venv"
    system "python3", "-m", "venv", venv.to_s
    system venv/"bin/pip", "install", "--quiet", "-r", "requirements.txt"

    # Copy source files
    (lib/"sentient-printer").install Dir["src/*.py"]

    # Install CUPS filter wrapper
    cups_filter = lib/"sentient-printer/sentient-printer-filter"
    cups_filter.write <<~SH
      #!/bin/bash
      export PATH="#{venv}/bin:$PATH"
      exec "#{venv}/bin/python3" "#{lib}/sentient-printer/filter.py" "$@"
    SH
    cups_filter.chmod 0755

    # Install PPD
    (share/"ppd/sentient-printer").install "ppd/sentient-printer.ppd"

    # Install CLI
    bin.install "sentient-printer"
  end

  def post_install
    # Register CUPS virtual printer
    system "lpadmin", "-x", "SentientPrinter" rescue nil
    system "sudo", "cp", "#{lib}/sentient-printer/sentient-printer-filter",
           "/usr/libexec/cups/filter/sentient-printer-filter"
    system "lpadmin", "-p", "SentientPrinter", "-E",
           "-v", "file:///dev/null",
           "-P", "#{share}/ppd/sentient-printer/sentient-printer.ppd",
           "-D", "Sentient Printer",
           "-L", "Your printer, but with opinions"
  end

  def caveats
    <<~EOS
      Run first-time setup:
        sentient-printer configure

      Test it:
        sentient-printer test /path/to/any.pdf

      Print for real:
        lp -d SentientPrinter /path/to/any.pdf
    EOS
  end

  test do
    system bin/"sentient-printer", "status"
  end
end
