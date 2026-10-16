"""Static checks for shared IntelliJ IDEA 2025.2 debugger configurations."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class IntelliJF5Tests(unittest.TestCase):
    def test_remote_debug_runs_gradle_start_first(self):
        remote = ET.parse(ROOT / ".run" / "NWClient - Minecraft Debug.run.xml").getroot()
        config = remote.find("configuration")
        self.assertEqual(config.get("type"), "Remote")
        opts = {x.get("name"): x.get("value") for x in config.findall("option")}
        self.assertEqual(opts["PORT"], "5005")
        self.assertEqual(opts["HOST"], "127.0.0.1")
        self.assertEqual(opts["SERVER_MODE"], "false")
        before = config.find("./method/option")
        self.assertEqual(before.get("name"), "RunConfigurationTask")
        self.assertEqual(before.get("enabled"), "true")
        self.assertEqual(before.get("run_configuration_name"), "NWClient - Start Debug JVM")

    def test_gradle_start_configuration_runs_task(self):
        gradle = ET.parse(ROOT / ".run" / "NWClient - Start Debug JVM.run.xml").getroot()
        opts = gradle.findall("./configuration/ExternalSystemSettings/option")
        tasks = next(x for x in opts if x.get("name") == "taskNames")
        self.assertEqual(tasks.find("./list/option").get("value"), "devDebugStart")

    def test_suspended_process_start_has_expected_arguments(self):
        source = (ROOT / "nwclient_debug_start.py").read_text(encoding="utf-8")
        self.assertIn('replace("suspend=n", "suspend=y")', source)
        self.assertIn("await_ready(process)", source)
        self.assertIn("CREATE_NEW_PROCESS_GROUP", source)
        build = (ROOT / "build.gradle").read_text(encoding="utf-8")
        self.assertIn("tasks.register('devDebugStart', Exec)", build)


if __name__ == "__main__":
    unittest.main()
