"""Internationalization support for agit."""

import json
import os
from pathlib import Path
from typing import Any

_LOCALE_DIR = Path(__file__).parent / "locale"
_current_locale = "zh_CN"
_translations: dict[str, dict[str, str]] = {}


def _load_locale(locale: str) -> dict[str, str]:
    if locale in _translations:
        return _translations[locale]
    locale_file = _LOCALE_DIR / locale / "messages.json"
    if not locale_file.exists():
        locale_file = _LOCALE_DIR / "zh_CN" / "messages.json"
    with open(locale_file, encoding="utf-8") as f:
        _translations[locale] = json.load(f)
    return _translations[locale]


def set_locale(locale: str) -> None:
    global _current_locale
    _current_locale = locale


def get_locale() -> str:
    return _current_locale


def t(key: str, **kwargs: Any) -> str:
    """Translate a key to the current locale.

    Usage:
        t("config.saved", config_key="ai.model")
        t("risk.blocked", command="git push --force")
    """
    trans = _load_locale(_current_locale)
    template = trans.get(key, key)
    if kwargs:
        try:
            template = template.format(**kwargs)
        except KeyError:
            pass
    return template
