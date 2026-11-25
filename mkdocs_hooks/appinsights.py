"""MkDocs hook: inject Application Insights settings at build time from environment."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

ENV_CONNECTION_STRING = "APPLICATIONINSIGHTS_CONNECTION_STRING"

_LOADER_INC = Path(__file__).resolve().parent.parent / "overrides" / "assets" / "javascripts" / "appinsights-loader.inc.js"
_LOADER_OUT = Path(__file__).resolve().parent.parent / "overrides" / "assets" / "javascripts" / "appinsights-loader.generated.js"


def _production_hostname(site_url: str) -> str:
    if not site_url:
        return ""
    return urlparse(site_url).hostname or ""


def _escape_js_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _write_loader_script(hostname: str, connection_string: str) -> None:
    if not connection_string or not hostname:
        _LOADER_OUT.write_text(
            "// Application Insights disabled: set APPLICATIONINSIGHTS_CONNECTION_STRING and site_url at build time.\n",
            encoding="utf-8",
        )
        return

    template = _LOADER_INC.read_text(encoding="utf-8")
    body = template.replace("__AIHUB_CS__", _escape_js_string(connection_string))
    guarded = (
        f'if (location.hostname === "{_escape_js_string(hostname)}") {{\n'
        f"{body}\n"
        "}\n"
    )
    _LOADER_OUT.write_text(guarded, encoding="utf-8")


def on_config(config, **kwargs):
    extra = dict(config.extra or {})
    analytics = dict(extra.get("analytics") or {})

    connection_string = os.environ.get(ENV_CONNECTION_STRING, "").strip()
    if connection_string:
        analytics["connection_string"] = connection_string

    site_url = getattr(config, "site_url", None) or ""
    hostname = _production_hostname(site_url)
    if hostname:
        analytics["production_hostname"] = hostname

    if analytics:
        extra["analytics"] = analytics
        config.extra = extra

    return config


def on_pre_build(config, **kwargs):
    hostname = _production_hostname(getattr(config, "site_url", None) or "")
    connection_string = os.environ.get(ENV_CONNECTION_STRING, "").strip()
    _write_loader_script(hostname, connection_string)
    return config