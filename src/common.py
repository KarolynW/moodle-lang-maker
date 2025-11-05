# common module placeholder
# -*- coding: utf-8 -*-
import json, os, re, csv, hashlib, time
from pathlib import Path
from typing import Iterable, List, Dict, Tuple
from config import (MOODLE_CODE_ROOT, MOODLE_CORE_LANG_EN, INCLUDE_PLUGINS,
                    WORKDIR, DATA_DIR, OUTPUT_DIR, LOG_DIR, VARIANT_CODE,
                    VARIANT_NAME, PARENT_LANGUAGE, BATCH_SIZE, OPENAI_MODEL,
                    TARGET_STYLE, INCLUDE_ONLY_REL_PATHS, SKIP_BASENAMES)

# Ensure folders exist
for p in (DATA_DIR, OUTPUT_DIR, LOG_DIR):
    p.mkdir(parents=True, exist_ok=True)

CSV_PATH = DATA_DIR / "strings.csv"

# Regexes to extract $string['key'] = 'value';
RE_SQ = re.compile(r"\$string\[['\"](?P<k>[^'\"]+)['\"]\]\s*=\s*'(?P<t>(?:\\'|[^'])*?)';", re.S)
RE_DQ = re.compile(r'\$string\[\s*["\'](?P<k>[^"\']+)["\']\s*\]\s*=\s*"(?P<t>(?:\\"|[^"])*?)";', re.S)

def unescape_php(s: str, quote: str) -> str:
    return s.replace("\\'", "'") if quote == "'" else s.replace('\\"', '"')

def php_quote(s: str) -> str:
    # Minimal escaping for single-quoted PHP strings
    return s.replace("\\", "\\\\").replace("'", "\\'")

def sha_row(component: str, relfile: str, key: str, text: str) -> str:
    h = hashlib.sha256()
    for v in (component, relfile, key, text):
        h.update(b"|")
        h.update(v.encode("utf-8"))
    return h.hexdigest()

def discover_lang_files() -> List[Path]:
    files: List[Path] = []
    # Core
    if MOODLE_CORE_LANG_EN.is_dir():
        files += list(MOODLE_CORE_LANG_EN.glob("*.php"))
    # Plugins
    if INCLUDE_PLUGINS:
        for p in MOODLE_CODE_ROOT.rglob("lang/en/*.php"):
            # exclude core we already added
            if "lang\\en\\" in str(p).lower() or "lang/en/" in str(p).lower():
                if p.parent == MOODLE_CORE_LANG_EN:
                    continue
                files.append(p)
    # Optional include-only filter
    if INCLUDE_ONLY_REL_PATHS:
        keep = set(INCLUDE_ONLY_REL_PATHS)
        files = [f for f in files if str(f.relative_to(MOODLE_CODE_ROOT)).replace("\\", "/") in keep]
    return sorted(files)

def rel_from_root(p: Path) -> str:
    return str(p.relative_to(MOODLE_CODE_ROOT)).replace("\\", "/")

def is_core_lang_file(p: Path) -> bool:
    # Core lang files are under moodle/lang/en/*.php
    try:
        return p.parent.resolve() == MOODLE_CORE_LANG_EN.resolve()
    except Exception:
        return False

def component_from_path(p: Path) -> str:
    """Compute frankenstyle component for plugins and sensible core component.
       We keep this pragmatic rather than perfect. It is enough for pack output."""
    parts = p.parts
    # …/admin/tool/analytics/lang/en/tool_analytics.php or …/mod/forum/lang/en/forum.php
    if is_core_lang_file(p):
        # Use file stem for core, eg admin.php -> admin, moodle.php -> moodle
        stem = p.stem
        return stem  # Moodle core components usually match filenames
    # Plugins
    # Find the index of "lang"
    try:
        idx = parts.index("lang")
    except ValueError:
        try:
            idx = parts.index("lang".capitalize())  # Windows oddities
        except ValueError:
            idx = None
    if idx is None or idx < 2:
        return p.stem

    # Look back to determine plugin type and name
    # e.g. .../<plugintype>/<pluginname>/lang/en/<file>.php
    plugintype = parts[idx - 2]
    pluginname = parts[idx - 1]

    # Map to frankenstyle
    mapping = {
        "mod": f"mod_{pluginname}",
        "block": f"block_{pluginname}",
        "blocks": f"block_{pluginname}",
        "auth": f"auth_{pluginname}",
        "enrol": f"enrol_{pluginname}",
        "filter": f"filter_{pluginname}",
        "format": f"format_{pluginname}",
        "report": f"report_{pluginname}",
        "grade": f"grade_{pluginname}",
        "editor": f"editor_{pluginname}",
        "qtype": f"qtype_{pluginname}",
        "question": f"qtype_{pluginname}" if pluginname != "behaviour" else f"qbehaviour_{pluginname}",
        "qbehaviour": f"qbehaviour_{pluginname}",
        "tool": f"tool_{pluginname}",
        "availability": f"availability_{pluginname}",
        "message": f"message_{pluginname}",
        "portfolio": f"portfolio_{pluginname}",
        "repository": f"repository_{pluginname}",
        "theme": f"theme_{pluginname}",
        "local": f"local_{pluginname}",
        "profilefield": f"profilefield_{pluginname}",
        "assignsubmission": f"assignsubmission_{pluginname}",
        "assignfeedback": f"assignfeedback_{pluginname}",
        "booktool": f"booktool_{pluginname}",
        "scormreport": f"scormreport_{pluginname}",
        "admin": f"admin_{pluginname}",
        # add others as needed
    }
    comp = mapping.get(plugintype, f"{plugintype}_{pluginname}")
    return comp

# Placeholder and tag validator
PLACEHOLDER_PATTERNS = [
    r"\{\$a(?:->[A-Za-z0-9_]+)?\}",   # {$a} or {$a->name}
    r"%\d+\$[sdfox]",                 # %1$s, %2$d etc
    r"%[sdfox]",                      # %s, %d, %f, %o, %x
    r"%%",                            # literal percent
]
TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")

def tokens_for(s: str) -> List[str]:
    toks: List[str] = []
    for p in PLACEHOLDER_PATTERNS:
        toks += re.findall(p, s)
    toks += TAG_RE.findall(s)
    return sorted(toks)

def chunk(it: Iterable, n: int):
    buf = []
    for x in it:
        buf.append(x)
        if len(buf) == n:
            yield buf
            buf = []
    if buf:
        yield buf
