# -*- coding: utf-8 -*-
"""User-editable configuration for the Moodle Language Pack Maker.

All paths default to neutral placeholders so you can run the tool on any
platform. Update the values below to match your own Moodle checkout and desired
working directories before executing the scripts.
"""

from pathlib import Path


# --- Moodle source locations -------------------------------------------------

# Absolute path to the root of your Moodle installation. Update this to point to
# the checkout you want to mine. Windows users can keep the raw-string syntax,
# while Unix users can replace it with Path("/var/www/moodle").
MOODLE_CODE_ROOT = Path(r"/path/to/moodle")

# Path to the core English language pack within the Moodle checkout.
MOODLE_CORE_LANG_EN = MOODLE_CODE_ROOT / "lang" / "en"

# Include language files shipped with plugins under the Moodle root.
INCLUDE_PLUGINS = True


# --- Output & scratch directories -------------------------------------------

# Where to write intermediate CSV files, logs, and generated packs. The default
# uses a folder in your home directory to avoid permission issues inside the
# Moodle checkout.
WORKDIR = Path.home() / "moodle-lang-maker"
DATA_DIR = WORKDIR / "data"
OUTPUT_DIR = WORKDIR / "output"
LOG_DIR = WORKDIR / "logs"


# --- Variant metadata --------------------------------------------------------

# Identify the language variant you are building. Update the code and name to
# match your target audience.
VARIANT_CODE = "en_custom"
VARIANT_NAME = "Custom English"
PARENT_LANGUAGE = "en"

# Free-form description that is fed to the translation model to steer output.
TARGET_STYLE = "Custom English"


# --- OpenAI Batch API configuration -----------------------------------------

# Tune the batch size to control how many strings are submitted in one job. The
# default works well for moderate workloads, but feel free to adjust.
BATCH_SIZE = 150

# Model name used for the OpenAI Responses API.
OPENAI_MODEL = "gpt-4o-mini"

# Batch API timing controls.
BATCH_COMPLETION_WINDOW = "24h"   # Maximum processing window granted to OpenAI.
BATCH_POLL_SECONDS = 600           # Polling interval (seconds) when waiting.


# --- Extraction filters ------------------------------------------------------

# Limit extraction to specific language files while testing, expressed as
# relative paths from the Moodle root.
INCLUDE_ONLY_REL_PATHS = []  # e.g. ["mod/forum/lang/en/forum.php"]

# Filenames to skip outright during extraction.
SKIP_BASENAMES = {"langconfig.php"}

