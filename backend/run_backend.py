#!/usr/bin/env python3
"""Run the FastAPI backend server."""
import os
import subprocess
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.exit(subprocess.call([sys.executable, "-m", "uvicorn", "app.main:app", "--reload"]))
