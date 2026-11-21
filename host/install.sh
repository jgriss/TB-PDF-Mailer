#!/usr/bin/env bash
# Installs the com.example.pdftool native messaging host for the PDF Mailer
# Thunderbird extension on Linux and macOS. On Windows, register the host
# manually as described in README.md.
set -euo pipefail

HOST_NAME="com.example.pdftool"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_BIN="${PDF_TOOL_HOST_BIN:-$HOME/.local/bin/pdf_tool_host.py}"

case "$(uname -s)" in
  Linux)
    HOST_DIR="$HOME/.mozilla/native-messaging-hosts"
    ;;
  Darwin)
    HOST_DIR="$HOME/Library/Application Support/Mozilla/NativeMessagingHosts"
    ;;
  *)
    echo "Unsupported OS '$(uname -s)'. Register the host manually (see README.md)." >&2
    exit 1
    ;;
esac

mkdir -p "$(dirname "$INSTALL_BIN")" "$HOST_DIR"
cp "$SCRIPT_DIR/pdf_tool_host.py" "$INSTALL_BIN"
chmod +x "$INSTALL_BIN"
sed "s|/usr/local/bin/pdf_tool_host.py|$INSTALL_BIN|" \
  "$SCRIPT_DIR/$HOST_NAME.json" > "$HOST_DIR/$HOST_NAME.json"

echo "Installed native messaging host '$HOST_NAME'."
echo "Host script: $INSTALL_BIN"
echo "Host manifest: $HOST_DIR/$HOST_NAME.json"
