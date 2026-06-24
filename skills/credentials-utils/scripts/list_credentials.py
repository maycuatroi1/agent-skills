#!/usr/bin/env python3
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.execv(sys.executable, [sys.executable, str(HERE / "doctor.py")] + sys.argv[1:])
