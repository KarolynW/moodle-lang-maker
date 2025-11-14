# Moodle Language Pack Maker

> Written by Codex and provided strictly “as is.” This is a what-you-see-is-what-you-get project with no promises of support, maintenance, or follow-up assistance.

Moodle Language Pack Maker automates the creation of bespoke Moodle language
variants (for example, “Klingon English”). It extracts English source strings
from your Moodle checkout, translates them in bulk with the OpenAI Batch API,
and rebuilds Moodle-compatible `lang/` packs that you can drop straight into
`moodledata/lang/<variant>`.

The project is designed for power users who want a reproducible pipeline:

1. Discover every English language file in your Moodle installation.
2. Extract each `$string['key'] = 'value';` entry into a CSV workbook.
3. Translate pending rows through OpenAI while preserving placeholders and HTML
   tags.
4. Merge the translated text back into the CSV.
5. Assemble Moodle language packs grouped by component and by source file.

---

## Repository layout

```
├── config.py            # User-editable configuration for paths and behaviour
├── requirements.txt     # Python dependencies (currently only openai)
├── src/
│   ├── common.py            # Shared helpers: file discovery, token safety, etc.
│   ├── extract_to_csv.py    # Step 1 – mine Moodle PHP strings into CSV
│   ├── translate_csv.py     # Step 2 – build & submit OpenAI batch translations
│   ├── apply_batch_output.py# Optional – reapply downloaded batch output
│   ├── build_pack.py        # Step 3 – rebuild Moodle-ready lang packs
│   └── run_all.py           # Convenience wrapper that runs the full pipeline
└── README.md
```

Intermediate artefacts and final packs live under the work directory defined in
`config.py` (see below).

---

## Requirements

* Python 3.11+ (the scripts are tested against CPython 3.11 on Windows; they
  also run on Linux when you adjust paths accordingly).
* Access to a Moodle code checkout (core and optional plugins) on the same
  machine.
* An OpenAI account with Batch API access and the `OPENAI_API_KEY` environment
  variable configured.
* Optional: you can adapt the scripts to call alternative OpenAI-compatible
  providers, but they ship configured for the public OpenAI client.

Install Python dependencies inside a virtual environment:

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On Linux/macOS use the equivalent `python3 -m venv venv && source venv/bin/activate`.

---

## Configuration (`config.py`)

Edit `config.py` before running anything. The most important settings are:

| Setting | Description |
| --- | --- |
| `MOODLE_CODE_ROOT` | Path to your Moodle checkout (Windows paths are fine, raw strings avoid escaping). |
| `MOODLE_CORE_LANG_EN` | Usually `<MOODLE_CODE_ROOT>/lang/en`. Only adjust if your tree is unusual. |
| `INCLUDE_PLUGINS` | `True` to include plugin language files discovered under `lang/en/` anywhere in the checkout. |
| `INCLUDE_ONLY_REL_PATHS` | Optional allow-list of relative paths (e.g. `"mod/forum/lang/en/forum.php"`) to speed up testing. Leave empty for “all files”. |
| `SKIP_BASENAMES` | Filenames to ignore during extraction (defaults to `langconfig.php`). |
| `WORKDIR`, `DATA_DIR`, `OUTPUT_DIR`, `LOG_DIR` | Where CSVs, batch files, outputs, and logs are written. Ensure the user has write access. |
| `VARIANT_CODE`, `VARIANT_NAME`, `PARENT_LANGUAGE` | Metadata for the generated language pack. `VARIANT_CODE` becomes the target directory name under `moodledata/lang/`. |
| `TARGET_STYLE` | Free-form description fed to the translator (e.g. “Pirate English”, “German (Sie)”). |
| `OPENAI_MODEL` | Model name for the `/v1/responses` endpoint. Defaults to `gpt-4o-mini`. |
| `BATCH_SIZE` | Legacy knob (the current batch implementation builds one request per row; tune if you adapt the workflow). |
| `BATCH_COMPLETION_WINDOW`, `BATCH_POLL_SECONDS` | Control how long OpenAI may process the batch and how often the script polls for completion. |

> **Tip:** Paths in `config.py` default to Windows. When running on Linux change
> `MOODLE_CODE_ROOT` and the work directories to Unix-style paths.

---

## End-to-end workflow

You can execute each stage manually or run everything via `src/run_all.py`.
The pipeline requires three stages in order:

1. `extract_to_csv` – scan Moodle for English strings and write `data/strings.csv`.
2. `translate_csv` – build a Batch API job for rows with `status == "pending"`.
3. `build_pack` – produce Moodle PHP files from translated rows.

### 1. Extract Moodle strings to CSV

```powershell
py src\extract_to_csv.py
```

The script:

* Discovers every `.php` file under `lang/en/` (core + optional plugins).
* Uses regular expressions to capture `$string['key'] = 'value';` and
  `$string["key"] = "value";` entries.
* Records component, relative path, source file name, string key, original
  English text, and a SHA-256 hash uniquely identifying the row.
* Writes `data/strings.csv` with columns: `component`, `relpath`, `sourcefile`,
  `key`, `source_text`, `translated_text`, `status`, `hash`.

Rows start with `translated_text` empty and `status` set to `pending`.

### 2. Translate pending rows through OpenAI Batch

```powershell
py src\translate_csv.py
```

Key behaviour:

* Loads `strings.csv`, keeps the `_row_index` in memory to generate stable
  `custom_id` values (`{hash}__{row_index}`) for the batch job.
* Creates `data/batch_input.jsonl`, where each line is a `POST /v1/responses`
  request containing the source string and metadata.
* Submits the JSONL file via the official OpenAI Python client, creating a batch
  job with the configured completion window.
* Spawns a background thread that polls `client.batches.retrieve(...)` every
  `BATCH_POLL_SECONDS` until the job reaches a terminal state.
* Once the batch completes, downloads the output JSONL, merges translations into
  memory, and rewrites `strings.csv` (keeping extra columns such as `_row_index`).
* Normalises translations to ensure placeholders (e.g. `{$a}`, `%1$s`) and HTML
  tags match the original tokens. If validation fails, the original English text
  is reused and the row status becomes `fallback`.

When there are no pending strings the script exits early.

#### Reapplying saved batch results

If you download batch output manually (e.g. from the OpenAI dashboard) place it
at `data/batch_output.jsonl` and run:

```powershell
py src\apply_batch_output.py
```

The helper will parse the JSONL, match rows by `custom_id`, apply the same
placeholder safety checks, and update `strings.csv` accordingly.

### 3. Build Moodle language packs

```powershell
py src\build_pack.py
```

The builder reads the updated CSV and considers only rows where
`translated_text` differs from `source_text`. It outputs two directory
structures under `output/`:

1. `en_variant_by_component` – files grouped by Moodle component name
   (`component.php`).
2. `en_variant_by_sourcefile` – files grouped by the original source PHP file.

Each folder includes a generated `langconfig.php` containing the variant name
and parent language. Copy one of these folders into your Moodle
`moodledata/lang/<variant_code>` directory (e.g. `moodledata/lang/en_Klingon`),
then purge Moodle caches via *Site administration → Development → Purge caches*.

### One-click run

To execute the full pipeline in sequence:

```powershell
py src\run_all.py
```

This runs extraction, translation, and pack building in a single process. The
translation step still waits for the batch to complete before proceeding.

---

## CSV anatomy

`data/strings.csv` is the source of truth for the workflow. You can edit it
manually to tweak translations:

* Update `translated_text` for any row and set `status` to `ok` to prevent
  retranslation.
* Leave `translated_text` blank and `status` as `pending` to include the string
  in the next batch submission.
* The `hash` column is a deterministic digest of `component`, `relpath`, `key`,
  and `source_text`; it prevents duplicate submissions when source text changes.

The scripts preserve additional columns you add manually, as writers gather the
union of all keys when saving the CSV.

---

## Logging and troubleshooting

* Standard output prints progress information, including batch IDs and polling
  timestamps.
* If the batch finishes in a non-success state the translator stops and leaves
  `strings.csv` untouched (except for `_row_index` which is recomputed on load).
* Placeholder mismatches are silently handled by reverting to the English
  source text. If you expect translations to differ, inspect the offending row
  and adjust the translation manually.
* To limit the workload during testing, populate `INCLUDE_ONLY_REL_PATHS` with a
  handful of relative paths. You can also manually clear `translated_text`
  values to requeue specific strings.

---

## Deployment notes

* Ensure the output directory is writable; on Windows, use a path outside the
  Moodle checkout to avoid permission issues.
* When copying packs into `moodledata/lang/`, the folder name must exactly match
  `VARIANT_CODE`.
* After purging caches, switch the site language (or individual user language)
  to your variant to verify the translated UI.

---

## Contributing

Pull requests are welcome! Useful contributions include:

* Extending component detection in `component_from_path` for additional Moodle
  plugin types.
* Enhancing placeholder validation to cover more edge cases.
* Adding optional support for alternative translation providers.
* Writing automated tests for the CSV lifecycle.

Before submitting, run the scripts you touched and ensure the README remains up
to date.

---

## Disclaimer

This toolkit is intentionally minimal. Use it at your own risk, adapt it to your
own infrastructure, and don’t expect help if something breaks. You are the
support team.

