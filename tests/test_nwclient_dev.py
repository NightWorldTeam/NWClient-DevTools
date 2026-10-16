"""Tests for NWClient game installation selection, no Minecraft required."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_FILE = Path(__file__).resolve().parents[1] / "nwclient_dev.py"
spec = importlib.util.spec_from_file_location("nwclient_dev", MODULE_FILE)
dev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dev)


class InstallationDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "workspace"
        self.workspace.mkdir()
        self.appdata = Path(self.temp.name) / "appdata"
        self.appdata.mkdir()
        self.custom = Path(self.temp.name) / "custom"
        self.explicit = Path(self.temp.name) / "explicit"

    def install(self, root):
        (root / "libraries").mkdir(parents=True)
        (root / "assets").mkdir(parents=True)
        jar = root / "instances" / "nwclient dev" / "version" / "client.jar"
        jar.parent.mkdir(parents=True)
        jar.touch()

    def config(self, path):
        (self.workspace / "deploy.toml").write_text(
            '[launch]\nroot = "' + path.as_posix() + '"\n',
            encoding="utf-8"
        )

    def discover(self, **env):
        variables = {"APPDATA": str(self.appdata), **env}
        with mock.patch.object(dev, "WORKSPACE", self.workspace), mock.patch.dict(
            os.environ, variables, clear=True
        ):
            return dev.locate_installation()

    def test_explicit_config_wins_over_both_other_valid_options(self):
        self.install(self.explicit)
        self.install(self.custom)
        self.install(self.appdata / ".lexplosion")
        self.config(self.explicit)
        root, source = self.discover(NWCLIENT_HOME=str(self.custom))
        self.assertEqual(root, self.explicit)
        self.assertEqual(source, "deploy.toml")

    def test_invalid_explicit_config_does_not_silently_fall_back(self):
        self.install(self.custom)
        self.install(self.appdata / ".lexplosion")
        self.config(self.explicit)
        with self.assertRaisesRegex(ValueError, "deploy.toml takes priority"):
            self.discover(NWCLIENT_HOME=str(self.custom))

    def test_environment_wins_without_explicit_config(self):
        self.install(self.custom)
        self.install(self.appdata / ".lexplosion")
        root, source = self.discover(NWCLIENT_HOME=str(self.custom))
        self.assertEqual(root, self.custom)
        self.assertEqual(source, "NWCLIENT_HOME")

    def test_appdata_used_when_environment_path_is_incomplete(self):
        self.install(self.appdata / ".lexplosion")
        root, source = self.discover(NWCLIENT_HOME=str(self.custom))
        self.assertEqual(root, self.appdata / ".lexplosion")
        self.assertEqual(source, "%APPDATA%/.lexplosion")

    def test_missing_all_requires_config_file(self):
        with self.assertRaisesRegex(ValueError, "Create deploy.toml"):
            self.discover()

    def test_empty_explicit_config_is_error_even_if_appdata_valid(self):
        self.install(self.appdata / ".lexplosion")
        (self.workspace / "deploy.toml").write_text("[launch]\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "no installation path"):
            self.discover()


if __name__ == "__main__":
    unittest.main()
