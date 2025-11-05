# build_pack placeholder
# -*- coding: utf-8 -*-
import csv
from pathlib import Path
from collections import defaultdict
from common import CSV_PATH, php_quote
from config import OUTPUT_DIR, VARIANT_CODE, VARIANT_NAME, PARENT_LANGUAGE

def write_langconfig(outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "langconfig.php").write_text(
        "<?php\n"
        "defined('MOODLE_INTERNAL') || die();\n"
        f"$string['thislanguage'] = '{php_quote(VARIANT_NAME)}';\n"
        f"$string['thislanguageint'] = '{php_quote(VARIANT_NAME)}';\n"
        f"$string['parentlanguage'] = '{php_quote(PARENT_LANGUAGE)}';\n",
        encoding="utf-8"
    )

def main():
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Only keep rows where translation differs
    changed = [r for r in rows if r["translated_text"] and r["translated_text"] != r["source_text"]]

    # Two output modes to keep things safe and testable
    # 1 by component filename: tool_analytics.php, mod_forum.php, etc
    out_component = OUTPUT_DIR / "en_variant_by_component"
    out_component.mkdir(parents=True, exist_ok=True)
    write_langconfig(out_component)

    by_component = defaultdict(list)
    for r in changed:
        comp = r["component"]
        by_component[f"{comp}.php"].append((r["key"], r["translated_text"]))

    for phpfile, items in by_component.items():
        with (out_component / phpfile).open("w", encoding="utf-8") as fh:
            fh.write("<?php\ndefined('MOODLE_INTERNAL') || die();\n")
            for k, v in items:
                fh.write(f"$string['{k}'] = '{php_quote(v)}';\n")

    # 2 by source filename: admin.php, moodle.php, forum.php
    out_source = OUTPUT_DIR / "en_variant_by_sourcefile"
    out_source.mkdir(parents=True, exist_ok=True)
    write_langconfig(out_source)

    by_srcfile = defaultdict(list)
    for r in changed:
        by_srcfile[r["sourcefile"]].append((r["key"], r["translated_text"]))

    for phpfile, items in by_srcfile.items():
        with (out_source / phpfile).open("w", encoding="utf-8") as fh:
            fh.write("<?php\ndefined('MOODLE_INTERNAL') || die();\n")
            for k, v in items:
                fh.write(f"$string['{k}'] = '{php_quote(v)}';\n")

    print(f"Wrote {len(by_component)} files into {out_component}")
    print(f"Wrote {len(by_srcfile)} files into {out_source}")
    print("Next step: copy one of these folders to moodledata/lang/en_skyrim on Linux and purge caches.")

if __name__ == "__main__":
    main()
