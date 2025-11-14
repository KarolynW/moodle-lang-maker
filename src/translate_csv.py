# -*- coding: utf-8 -*-
"""
Batch translation of Moodle strings using the OpenAI Batch API.

Workflow:
 1. Read strings.csv and collect rows with status == "pending".
 2. Build a JSONL batch input file, one /v1/responses request per row.
    Each line uses "{hash}__{row_index}" as custom_id.
 3. Upload the JSONL as a batch input file and create a batch job.
 4. A background thread polls the batch until it finishes, then:
       - downloads the batch output
       - merges translations back into strings.csv
       - writes the updated CSV
       - signals an Event so main() can exit cleanly.
"""

import csv
import json
import time
import threading
from pathlib import Path

from openai import OpenAI

from src.common import CSV_PATH, tokens_for
from config import (
    TARGET_STYLE,
    OPENAI_MODEL,
    DATA_DIR,
    BATCH_COMPLETION_WINDOW,
    BATCH_POLL_SECONDS,
)

# OpenAI client (no Azure)
client = OpenAI()  # uses OPENAI_API_KEY from environment
MODEL = OPENAI_MODEL

SYSTEM = f"""You translate Moodle UI strings into {TARGET_STYLE}.
Rules:
1 Preserve placeholders exactly, for example {{$a}}, {{$a->name}}, %s, %d, %1$s
2 Preserve HTML tags and entities exactly
3 One line per item, no commentary
Return JSON only: {{"translated_text":"..."}}"""

# Where to put the batch input JSONL
BATCH_INPUT_PATH = DATA_DIR / "batch_input.jsonl"


# ---------------------------------------------------------------------------
# Build batch input file
# ---------------------------------------------------------------------------

def build_batch_input_file(pending_rows):
    """
    Create a JSONL file where each line is a POST /v1/responses request.

    custom_id is "{hash}__{row_index}" so it is unique per row.
    """
    BATCH_INPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with BATCH_INPUT_PATH.open("w", encoding="utf-8") as f:
        for row in pending_rows:
            custom_id = f"{row['hash']}__{row['_row_index']}"

            payload = {
                "key": row["key"],
                "text": row["source_text"],
                "component": row["component"],
            }

            user_prompt = (
                "Translate this Moodle UI string. JSON only.\n"
                + json.dumps(payload, ensure_ascii=False)
            )

            body = {
                "model": MODEL,
                "input": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                "max_output_tokens": 512,
            }

            line = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/responses",
                "body": body,
            }

            f.write(json.dumps(line, ensure_ascii=False))
            f.write("\n")

    return BATCH_INPUT_PATH


# ---------------------------------------------------------------------------
# Submit batch
# ---------------------------------------------------------------------------

def submit_batch(input_path: Path) -> str:
    """Upload JSONL and create a batch job, returns batch id."""
    # Using an explicit file handle is safest across client versions
    with input_path.open("rb") as fh:
        batch_input_file = client.files.create(
            file=fh,
            purpose="batch",
        )

    batch = client.batches.create(
        input_file_id=batch_input_file.id,
        endpoint="/v1/responses",
        completion_window=BATCH_COMPLETION_WINDOW,
        metadata={"job": "moodle_lang_translation"},
    )

    print(f"Submitted batch {batch.id}")
    return batch.id


# ---------------------------------------------------------------------------
# Extract text from /v1/responses body
# ---------------------------------------------------------------------------

def extract_output_text(body: dict) -> str:
    """
    Given a /v1/responses response body, pull out the assistant text.

    We try:
      - body["output_text"] if present
      - else any output_text in body["output"] entries.
    """
    if isinstance(body.get("output_text"), str):
        return body["output_text"]

    for item in body.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    return c.get("text", "")
    return ""


# ---------------------------------------------------------------------------
# Apply batch results to CSV rows
# ---------------------------------------------------------------------------

def apply_batch_results(rows, output_jsonl_text: str):
    """
    Parse batch output JSONL and update rows in place.

    Each line format:
      {"id": "...", "custom_id": "...",
       "response": {"body": {...}},
       "error": ...}

    custom_id format is "{hash}__{row_index}".
    """
    rows_by_custom_id = {}
    for r in rows:
        if "_row_index" in r:
            cid = f"{r['hash']}__{r['_row_index']}"
            rows_by_custom_id[cid] = r

    total_items = 0
    matched = 0
    changed = 0

    for line in output_jsonl_text.splitlines():
        line = line.strip()
        if not line:
            continue

        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            print("Skipping invalid JSON line in batch output")
            continue

        total_items += 1
        custom_id = obj.get("custom_id")
        if not custom_id or custom_id not in rows_by_custom_id:
            continue

        if obj.get("error"):
            print(f"Batch item error for {custom_id}: {obj['error']}")
            continue

        body = obj.get("response", {}).get("body", {})
        raw_text = extract_output_text(body).strip()
        if not raw_text:
            continue

        # We asked for JSON only: {"translated_text":"..."}
        try:
            decoded = json.loads(raw_text)
            if isinstance(decoded, dict) and "translated_text" in decoded:
                translated = decoded["translated_text"]
            else:
                translated = decoded if isinstance(decoded, str) else raw_text
        except json.JSONDecodeError:
            translated = raw_text

        row = rows_by_custom_id[custom_id]
        src = row["source_text"]
        tgt = (translated or "").strip()
        if not tgt:
            continue

        matched += 1

        # Placeholder and tag safety
        safe_tgt = tgt if tokens_for(src) == tokens_for(tgt) else src

        if safe_tgt != row.get("translated_text"):
            changed += 1

        row["translated_text"] = safe_tgt
        row["status"] = "ok" if safe_tgt != src else "fallback"

    print(f"Processed {total_items} batch items inside apply_batch_results.")
    print(f"Matched {matched} rows in CSV, changed {changed} rows.")


# ---------------------------------------------------------------------------
# Background polling thread
# ---------------------------------------------------------------------------

def poll_batch_and_update(batch_id: str, rows, done_event: threading.Event):
    """
    Background worker.

    Polls the batch every BATCH_POLL_SECONDS until it ends.
    When completed, downloads output, merges into rows, writes CSV,
    then signals done_event.
    """
    terminal_states = {"completed", "failed", "cancelled", "expired"}

    try:
        while True:
            batch = client.batches.retrieve(batch_id)
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] Batch {batch_id} status: {batch.status}")

            if batch.status in terminal_states:
                break

            time.sleep(BATCH_POLL_SECONDS)

        if batch.status != "completed":
            print(f"Batch finished in non success state: {batch.status}")
            if getattr(batch, "error_file_id", None):
                print(f"Batch error file id: {batch.error_file_id}")
            done_event.set()
            return

        if not batch.output_file_id:
            print("Batch completed but has no output_file_id")
            done_event.set()
            return

        # Download output JSONL
        file_resp = client.files.content(batch.output_file_id)
        output_text = file_resp.text

        # Merge results into rows
        apply_batch_results(rows, output_text)

        # Work out fieldnames from the actual data so extra columns like _row_index are kept
        fieldnames = sorted({k for r in rows for k in r.keys()})

        with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

        print("Translation complete. CSV updated from batch output.")

    finally:
        # Always signal main thread to avoid deadlock
        done_event.set()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Load CSV
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Add in memory row index so each custom_id is unique
    for idx, row in enumerate(rows):
        row["_row_index"] = idx

    pending = [r for r in rows if r.get("status") == "pending"]

    if not pending:
        print("No pending strings to translate.")
        return

    print(f"{len(pending)} strings pending translation")

    # Build JSONL input
    input_path = build_batch_input_file(pending)

    # Submit batch
    batch_id = submit_batch(input_path)

    # Set up background polling thread
    done_event = threading.Event()
    t = threading.Thread(
        target=poll_batch_and_update,
        args=(batch_id, rows, done_event),
        daemon=True,
    )
    t.start()

    print(
        "Batch submitted. Background thread will poll periodically "
        "until processing completes."
    )

    # Wait until the background worker has finished updating the CSV
    done_event.wait()
    print("Batch processing finished. Exiting translate_csv.")


if __name__ == "__main__":
    main()

