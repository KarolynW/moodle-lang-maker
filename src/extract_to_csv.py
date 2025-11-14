# -*- coding: utf-8 -*-
import csv
from config import SKIP_BASENAMES
from src.common import (
    discover_lang_files, rel_from_root, component_from_path,
    RE_SQ, RE_DQ, unescape_php, sha_row, CSV_PATH
)

def main():
    files = discover_lang_files()
    rows = []
    for php in files:
        if php.name in SKIP_BASENAMES:
            continue
        data = php.read_text(encoding="utf-8", errors="ignore")
        relfile = rel_from_root(php)
        component = component_from_path(php)

        # single quoted
        for m in RE_SQ.finditer(data):
            key = m.group("k")
            text = unescape_php(m.group("t"), "'")
            rows.append([component, relfile, php.name, key, text, "", "pending",
                         sha_row(component, relfile, key, text)])

        # double quoted
        for m in RE_DQ.finditer(data):
            key = m.group("k")
            text = unescape_php(m.group("t"), '"')
            rows.append([component, relfile, php.name, key, text, "", "pending",
                         sha_row(component, relfile, key, text)])

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["component","relpath","sourcefile","key","source_text","translated_text","status","hash"])
        w.writerows(rows)

    print(f"Extracted {len(rows)} strings into {CSV_PATH}")

if __name__ == "__main__":
    main()
