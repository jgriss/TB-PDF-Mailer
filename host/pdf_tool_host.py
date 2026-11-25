#!/usr/bin/env python3
"""Native messaging host for the PDF Mailer Thunderbird extension.

Reads one JSON message from stdin (native messaging framing: 4-byte
little-endian length + UTF-8 JSON) of the form:

    {"command": "pdf-stamp {pdf} -o {out}", "pdf": "/abs/in.pdf", "out": "/abs/out.pdf"}

Replaces the {pdf} placeholder with the shell-quoted input PDF path and the
{out} placeholder with the shell-quoted output PDF path, runs the command,
then reads the output PDF ({out}) back and answers with:

    {"ok": true, "data": "<base64 of the adapted PDF>", "stdout": "...", "stderr": "..."}

If the command did not write to {out} (e.g. it only uses {pdf} and modifies
the input in place), the input file is read back instead. On failure:

    {"ok": false, "error": "..."}
"""

import base64
import json
import os
import shlex
import subprocess
import sys


def read_message(stream):
    raw_length = stream.read(4)
    if len(raw_length) < 4:
        return None
    length = int.from_bytes(raw_length, "little")
    return json.loads(stream.read(length).decode("utf-8"))


def write_message(stream, payload):
    data = json.dumps(payload).encode("utf-8")
    stream.write(len(data).to_bytes(4, "little"))
    stream.write(data)
    stream.flush()


def build_command(template, pdf_path, out_path):
    """Substitute placeholders if still present (legacy add-on versions send
    the raw template). Modern add-ons expand the placeholders themselves, so
    a command without placeholders is executed verbatim - never append paths
    to it. Returns (command, uses_out)."""
    uses_out = "{out}" in template or "%OUT%" in template
    quoted_in = shlex.quote(pdf_path)
    quoted_out = shlex.quote(out_path)
    command = (template
               .replace("{out}", quoted_out).replace("%OUT%", quoted_out)
               .replace("{pdf}", quoted_in).replace("%PDF%", quoted_in))
    return command, uses_out


def main():
    try:
        message = read_message(sys.stdin.buffer)
        if not message:
            write_message(sys.stdout.buffer, {"ok": False, "error": "no input message"})
            return
        template = str(message.get("command", ""))
        pdf_path = str(message.get("pdf", ""))
        out_path = str(message.get("out", ""))
        command, uses_out = build_command(template, pdf_path, out_path)
        if out_path and os.path.exists(out_path):
            os.remove(out_path)  # never attach a stale output from a previous run
        proc = subprocess.run(command, shell=True, capture_output=True, text=True)
        if proc.returncode != 0:
            write_message(sys.stdout.buffer, {
                "ok": False,
                "error": "command exited with code %d: %s" % (proc.returncode, proc.stderr.strip()),
            })
            return
        if uses_out and out_path and not os.path.exists(out_path):
            write_message(sys.stdout.buffer, {
                "ok": False,
                "error": "command did not create the output file: " + out_path,
            })
            return
        result_path = out_path if (out_path and os.path.exists(out_path)) else pdf_path
        with open(result_path, "rb") as handle:
            data = base64.b64encode(handle.read()).decode("ascii")
        write_message(sys.stdout.buffer, {
            "ok": True,
            "data": data,
            "used": result_path,
            "command": command,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        })
    except Exception as exc:  # noqa: BLE001 - report any failure back to the extension
        write_message(sys.stdout.buffer, {"ok": False, "error": str(exc)})


if __name__ == "__main__":
    main()
