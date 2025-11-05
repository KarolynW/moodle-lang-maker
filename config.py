# -*- coding: utf-8 -*-
from pathlib import Path

# Point these at your Windows Moodle checkout
MOODLE_CODE_ROOT = Path(r"C:\moodle")           # eg C:\moodle
MOODLE_CORE_LANG_EN = MOODLE_CODE_ROOT / "lang" / "en"

# If you want to include plugins, set this to the Moodle root folder
INCLUDE_PLUGINS = True

# Where to write intermediate CSV and final packs
WORKDIR = Path(r"C:\moodle-lang-maker")
DATA_DIR = WORKDIR / "data"
OUTPUT_DIR = WORKDIR / "output"
LOG_DIR = WORKDIR / "logs"

# Output language variant code
VARIANT_CODE = "en_skyrim"
VARIANT_NAME = "Skyrim English"
PARENT_LANGUAGE = "en"

# Translation target description. You can change this to any language or style
TARGET_STYLE = "Skyrim English"

# Batch size for API calls
BATCH_SIZE = 150

# Model name for OpenAI Responses API
OPENAI_MODEL = "gpt-4o-mini"

# Optional: limit to these folders while testing
INCLUDE_ONLY_REL_PATHS = []  # e.g. ["mod/forum/lang/en/forum.php"]

# Files to skip outright
SKIP_BASENAMES = {"langconfig.php"}  # keep our own

