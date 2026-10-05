#!/bin/bash
# Double-click this file on a Mac to start Shorts Maker.
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is not installed. Get it from https://www.python.org/downloads/ then double-click this file again."
  read -n 1 -s -r -p "Press any key to close..."; exit 1
fi
if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
python updater.py
pip install -q -r requirements.txt
python app.py
read -n 1 -s -r -p "Press any key to close..."
