"""Real interactive Pi smoke test; all servers, files and credentials are disposable."""
import fcntl
import json
import os
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = json.dumps({
            "rules_version": "pty-test",
            "rules": [f"Read-only rule {i}" for i in range(30)],
            "problems": [{
                "slug": "help_me_unpack", "title": "Help me unpack",
                "challenge_url": "https://hackattic.com/challenges/help_me_unpack",
                "instructions": ["Details test only"], "model": "any", "thinking_level": "any",
            }],
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args):
        pass


server = HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with tempfile.TemporaryDirectory(prefix="golf-view-pty-") as directory:
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))
        # This notification proves extension/session initialization reached its
        # ready boundary; header rendering alone happens earlier in Pi startup.
        ready = Path(directory) / "ready.ts"
        ready.write_text('export default function(pi) { pi.on("session_start", (_e, ctx) => ctx.ui.notify("PTY_BROWSER_READY", "info")); pi.registerCommand("pty-check", { description: "Test readiness", handler: (_args, ctx) => ctx.ui.notify("PTY_COMMAND_HANDLED", "info") }); }')
        env = {
            **os.environ, "HOME": directory, "PI_CODING_AGENT_DIR": directory + "/config",
            "PI_TELEMETRY": "0", "AGENT_GOLF_API_BASE_URL": f"http://127.0.0.1:{server.server_port}",
        }
        child = subprocess.Popen([
            "pi", "--offline", "--no-extensions", "--no-mcp", "--no-skills",
            "--no-prompt-templates", "--no-context-files",
            "--extension", str(Path(sys.argv[1]).resolve()), "--extension", str(ready),
        ], cwd=directory, env=env, stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
        os.close(slave)

        def stop(_signum=None, _frame=None):
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            if _signum is not None:
                raise SystemExit(1)

        signal.signal(signal.SIGTERM, stop)

        def wait_for(expected, stage, timeout=8):
            output = b""
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    raise AssertionError(f"Pi exited during {stage}")
                if not select.select([master], [], [], min(.1, max(0, deadline - time.monotonic())))[0]:
                    continue
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    raise AssertionError(f"PTY closed during {stage}") from None
                output += chunk
                if b"\x1b[6n" in chunk:
                    os.write(master, b"\x1b[1;1R")
                plain = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", output.decode(errors="replace"))
                if (expected is None and plain.strip()) or (expected is not None and expected in plain):
                    return plain
            # Never dump terminal output: a future fixture could contain private data.
            raise AssertionError(f"Timed out waiting for {stage}")

        def send(data):
            os.write(master, data)

        try:
            wait_for("PTY_BROWSER_READY", "extension initialization")
            send(b"/golf-problems\r")
            rules = wait_for("view problems", "rules navigation")
            assert "Agent Golf rules" in rules and "submit" not in rules
            send(b"\x1b")
            wait_for("Problem browsing closed", "rules cancellation")
            send(b"/golf-problems\r")
            wait_for("view problems", "second rules view")
            send(b"\r")
            wait_for("choose to view details", "problem selector")
            send(b"\r")
            details = wait_for("back to problems", "details navigation")
            assert "Problem details" in details and "submit" not in details
            send(b"\x1b")
            wait_for("choose to view details", "return to selector")
            send(b"\x1b")
            # The repeated closed notification may be deduplicated by Pi. Wait
            # for restoration rendering, then prove the main command input works.
            wait_for(None, "editor restoration")
            send(b"/pty-check\r")
            wait_for("PTY_COMMAND_HANDLED", "main editor after selector cancellation")
            print("REAL TUI PASS: custom rules/footer, Esc close, Enter selector, custom details/footer, Esc back")
        finally:
            stop()
            os.close(master)
finally:
    server.shutdown()
    server.server_close()
