# -*- coding: utf-8 -*-
"""
Apply an existing Batch API output JSONL to strings.csv.

Assumes custom_id was built as: f"{row['hash']}__{row_index}"
where row_index is the zero-based index of the row at the time
the batch was created.
"""

import csv
import json

from src.common import CSV_PATH, tokens_for
from config import DATA_DIR

BATCH_OUTPUT = DATA_DIR / "batch_output.jsonl"


def extract_output_text(body: dict) -> str:
    """Pull assistant text out of a /v1/responses response body."""
    if isinstance(body.get("output_text"), str):
        return body["output_text"]

    for item in body.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    return c.get("text", "")
    return ""


def main():
    # ----- Load CSV -----
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} rows from {CSV_PATH}")

    if not BATCH_OUTPUT.exists():
        raise SystemExit(f"Batch output file not found at {BATCH_OUTPUT}")

    # ----- Build custom_id -> row mapping using hash__row_index -----
    cid_to_row = {}
    for idx, row in enumerate(rows):
        h = row.get("hash")
        if not h:
            continue
        cid = f"{h}__{idx}"
        cid_to_row[cid] = row

    print(f"Prepared {len(cid_to_row)} custom_id mappings from CSV")

    # ----- Load batch_output.jsonl -----
    output_lines = BATCH_OUTPUT.read_text(encoding="utf-8").splitlines()

    total_items = 0
    matched = 0
    changed = 0

    for line in output_lines:
        line = line.strip()
        if not line:
            continue

        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            print("Skipping invalid JSON line in batch_output")
            continue

        total_items += 1
        cid = obj.get("custom_id")
        if not cid:
            continue

        row = cid_to_row.get(cid)
        if row is None:
            # custom_id that does not exist in this CSV: maybe Moodle changed
            continue

        if obj.get("error"):
            print(f"Batch item error for {cid}: {obj['error']}")
            continue

        body = obj.get("response", {}).get("body", {})
        raw_text = extract_output_text(body).strip()
        if not raw_text:
            continue

        # We asked for JSON only: {"translated_text": "..."}
        try:
            decoded = json.loads(raw_text)
            if isinstance(decoded, dict) and "translated_text" in decoded:
                translated = decoded["translated_text"]
            else:
                translated = decoded if isinstance(decoded, str) else raw_text
        except json.JSONDecodeError:
            translated = raw_text

        src = row["source_text"]
        tgt = (translated or "").strip()
        if not tgt:
            continue

        matched += 1

        # Placeholder / tag safety
        safe_tgt = tgt if tokens_for(src) == tokens_for(tgt) else src

        if safe_tgt != row.get("translated_text"):
            changed += 1

        row["translated_text"] = safe_tgt
        row["status"] = "ok" if safe_tgt != src else "fallback"

    print(f"Processed {total_items} batch items.")
    print(f"Matched {matched} rows in CSV, changed {changed} rows.")

    # ----- Rewrite CSV keeping all columns -----
    fieldnames = sorted({k for r in rows for k in r.keys()})

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print("Updated strings.csv from batch_output.jsonl")


if __name__ == "__main__":
    main()


