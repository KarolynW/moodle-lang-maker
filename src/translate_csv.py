# -*- coding: utf-8 -*-
import os, csv, json, time
from src.common import CSV_PATH, tokens_for, chunk   # package import
from config import BATCH_SIZE, TARGET_STYLE, OPENAI_MODEL

# Choose OpenAI or Azure OpenAI from environment
USE_AZURE = bool(os.getenv("AZURE_OPENAI_ENDPOINT"))
if USE_AZURE:
    from openai import OpenAI
    client = OpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        base_url=f"{os.environ['AZURE_OPENAI_ENDPOINT'].rstrip('/')}/openai/deployments/{os.environ['AZURE_OPENAI_DEPLOYMENT']}"
    )
    MODEL = "ignored-by-azure-deployments"  # deployment is selected by base_url path
else:
    from openai import OpenAI
    client = OpenAI()  # uses OPENAI_API_KEY
    MODEL = OPENAI_MODEL

SYSTEM = f"""You translate Moodle UI strings into {TARGET_STYLE}.
Rules:
1 Preserve placeholders exactly, for example {{$a}}, {{$a->name}}, %s, %d, %1$s
2 Preserve HTML tags and entities exactly
3 One line per item, no commentary
Return JSON only: [{{"key":"...","translated_text":"..."}}]"""

def translate_batch(items):
    prompt = "Translate these Moodle strings. JSON only.\n" + json.dumps(items, ensure_ascii=False)
    resp = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt}
        ]
    )
    return json.loads(resp.output_text)

def main():
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    pending = [r for r in rows if r.get("status") == "pending"]

    for batch in chunk(pending, BATCH_SIZE):
        items = [{"key": x["key"], "text": x["source_text"], "component": x["component"]} for x in batch]
        out = translate_batch(items) if items else []
        by_key = {o["key"]: o["translated_text"] for o in out if "key" in o and "translated_text" in o}

        for r in batch:
            src = r["source_text"]
            tgt = by_key.get(r["key"], "").strip()
            if not tgt:
                continue
            r["translated_text"] = tgt if tokens_for(src) == tokens_for(tgt) else src
            r["status"] = "ok" if r["translated_text"] != src else "fallback"

        # Persist after each batch for safety
        with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "component","relpath","sourcefile","key",
                    "source_text","translated_text","status","hash"
                ]
            )
            w.writeheader()
            w.writerows(rows)

        time.sleep(0.4)  # polite pacing

    print("Translation complete. CSV updated.")

if __name__ == "__main__":
    main()

