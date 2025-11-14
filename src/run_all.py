# -*- coding: utf-8 -*-
# Orchestrates the three stages using -m so imports resolve at project root.

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(modname: str):
    print(f"=== {modname} ===")
    # Run as module from the project root so `from config import ...` works
    subprocess.run([sys.executable, "-m", modname], cwd=str(ROOT), check=True)

if __name__ == "__main__":
    run("src.extract_to_csv")
    run("src.translate_csv")
    run("src.build_pack")
    print("All done.")


