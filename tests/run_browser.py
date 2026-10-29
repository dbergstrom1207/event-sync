"""Start an isolated server and run the optional Node/Playwright smoke test."""

from pathlib import Path
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    server = subprocess.Popen(
        [sys.executable, "app.py", "--port", "0"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        line = server.stdout.readline().strip()
        match = re.search(r"http://127\.0\.0\.1:\d+", line)
        if not match:
            raise RuntimeError("Test server failed to start")
        print(line, flush=True)
        result = subprocess.run(
            ["node", "tests/browser-smoke.cjs"],
            cwd=ROOT,
            env={**os.environ, "BASE_URL": match.group(0)},
            timeout=120,
        )
        return result.returncode
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
