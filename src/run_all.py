# -*- coding: utf-8 -*-
"""
Run the full pipeline in process:
 1) extract_to_csv
 2) translate_csv
 3) build_pack
"""

import sys
from pathlib import Path

# Ensure project root (the folder that contains config.py and src/) is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import extract_to_csv, translate_csv, build_pack


def main():
    print("=== extract_to_csv ===")
    extract_to_csv.main()

    print("=== translate_csv ===")
    translate_csv.main()

    print("=== build_pack ===")
    build_pack.main()

    print("All done.")


if __name__ == "__main__":
    main()


