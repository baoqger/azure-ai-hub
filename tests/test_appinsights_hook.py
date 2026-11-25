import os
import unittest
from unittest.mock import MagicMock, patch

from mkdocs_hooks import appinsights


class TestAppInsightsHook(unittest.TestCase):
    def test_production_hostname_from_site_url(self):
        self.assertEqual(
            appinsights._production_hostname(
                "https://polite-pond-0d22a6d0f.azurestaticapps.net/"
            ),
            "polite-pond-0d22a6d0f.azurestaticapps.net",
        )
        self.assertEqual(appinsights._production_hostname(""), "")

    def test_on_config_injects_connection_string_from_env(self):
        os.environ[appinsights.ENV_CONNECTION_STRING] = "InstrumentationKey=test;"
        try:
            config = MagicMock()
            config.extra = {"analytics": {"provider": "appinsights"}}
            config.site_url = "https://example.azurestaticapps.net/"

            appinsights.on_config(config)

            self.assertEqual(
                config.extra["analytics"]["connection_string"],
                "InstrumentationKey=test;",
            )
            self.assertEqual(
                config.extra["analytics"]["production_hostname"],
                "example.azurestaticapps.net",
            )
        finally:
            os.environ.pop(appinsights.ENV_CONNECTION_STRING, None)

    def test_on_config_skips_connection_string_when_env_unset(self):
        os.environ.pop(appinsights.ENV_CONNECTION_STRING, None)
        config = MagicMock()
        config.extra = {"analytics": {"provider": "appinsights"}}
        config.site_url = "https://example.azurestaticapps.net/"

        appinsights.on_config(config)

        self.assertNotIn("connection_string", config.extra["analytics"])
        self.assertEqual(
            config.extra["analytics"]["production_hostname"],
            "example.azurestaticapps.net",
        )


    @patch.object(appinsights, "_LOADER_OUT", appinsights._LOADER_OUT)
    def test_write_loader_includes_hostname_guard(self):
        os.environ[appinsights.ENV_CONNECTION_STRING] = "InstrumentationKey=test;"
        try:
            config = MagicMock()
            config.site_url = "https://example.azurestaticapps.net/"
            appinsights.on_pre_build(config)
            text = appinsights._LOADER_OUT.read_text(encoding="utf-8")
            self.assertIn('location.hostname === "example.azurestaticapps.net"', text)
            self.assertIn("InstrumentationKey=test;", text)
        finally:
            os.environ.pop(appinsights.ENV_CONNECTION_STRING, None)
            appinsights.on_pre_build(MagicMock(site_url="https://example.azurestaticapps.net/"))


if __name__ == "__main__":
    unittest.main()