#!/usr/bin/env python3
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
args = [a for a in sys.argv[1:] if a == "--dry-run"]
os.execv(
    sys.executable,
    [sys.executable, str(HERE / "refresh_google_oauth.py"), "--service", "rclone"] + args,
)
