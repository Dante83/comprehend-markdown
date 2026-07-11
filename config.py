"""Shared configuration for the translation server + orchestrator.

Both entry points (server.py, launched standalone by an MCP host, and main.py,
the pipeline) read the same layered config so they never disagree about which
language is the source and which are the targets. config.json holds the
committed defaults; config.local.json (gitignored) overrides key-by-key.

The two knobs that make the whole pipeline direction-agnostic live here:

    source_language   the language the canonical README is written in, and the
                      name of its docs/<source_language>/ folder. Default
                      "English", but set it to "中文" / "Bahasa Indonesia" /
                      anything to translate *out of* that language instead.
    target_languages  the list the pipeline translates *into*. Any entry equal
                      to source_language is skipped (no self-translation).
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# The default fan-out list, used when config supplies no target_languages.
DEFAULT_TARGET_LANGUAGES = [
    "Deutsch", "Español", "Français", "Italiano", "Polski", "Português",
    "Русский", "Tiếng Việt", "ไทย", "中文", "日本語", "한국어",
    "العربية", "हिन्दी", "বাংলা", "Bahasa Indonesia", "اردو", "Naijá",
]

DEFAULT_SOURCE_LANGUAGE = "English"


def load_config():
    """Merge config.json then config.local.json, later files winning per key."""
    config = {}
    for filename in ("config.json", "config.local.json"):
        path = SCRIPT_DIR / filename
        if path.is_file():
            config.update(json.loads(path.read_text(encoding="utf-8")))
    return config


def get_source_language(config=None):
    """The language the source README is written in (also its folder name)."""
    config = config if config is not None else load_config()
    lang = str(config.get("source_language", DEFAULT_SOURCE_LANGUAGE)).strip()
    return lang or DEFAULT_SOURCE_LANGUAGE


def get_target_languages(config=None):
    """The languages to translate into, minus any that equal the source."""
    config = config if config is not None else load_config()
    langs = config.get("target_languages") or DEFAULT_TARGET_LANGUAGES
    source = get_source_language(config)
    # Skip self-translation so putting the source in the list is harmless.
    return [lang for lang in langs if lang.strip().lower() != source.lower()]
