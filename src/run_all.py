# -*- coding: utf-8 -*-
# run_all.py — orchestrates the three stages

import sys
import subprocess
from pathlib import Path

# Ensure the project root is on sys.path so config.py can be imported
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import WORKDIR  # now import works

def run(mod):
    print(f"=== {mod} ===")
    subprocess.check_call([sys.executable, str((WORKDIR / 'src' / mod).resolve())])

if __name__ == "__main__":
    run("extract_to_csv.py")
    run("translate_csv.py")
    run("build_pack.py")
    print("All done.")

