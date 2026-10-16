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



    def test_windows_process_rights_allow_wait_for_single_object(self):
        source = (ROOT / "nwclient_debug_start.py").read_text(encoding="utf-8")
        self.assertIn("SYNCHRONIZE = 0x00100000", source)
        self.assertIn("PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE", source)

    def test_reuse_jdwp_when_our_own_process_is_already_listening(self):
        from unittest import mock
        import nwclient_debug_start as helper
        with mock.patch.object(helper, "same_workspace_java_is_running", return_value=True), \
             mock.patch.object(helper, "port_is_available", return_value=False):
            self.assertTrue(helper.reuse_existing_debug_jvm(Path("C:/nwclient")))

    def test_foreign_process_occupying_port_is_rejected(self):
        from unittest import mock
        import nwclient_debug_start as helper
        with mock.patch.object(helper, "same_workspace_java_is_running", return_value=False), \
             mock.patch.object(helper, "port_is_available", return_value=False):
            with self.assertRaisesRegex(ValueError, "occupied by another process"):
                helper.reuse_existing_debug_jvm(Path("C:/nwclient"))

    def test_previous_game_without_jdwp_prevents_duplicate_launch(self):
        from unittest import mock
        import nwclient_debug_start as helper
        with mock.patch.object(helper, "same_workspace_java_is_running", return_value=True), \
             mock.patch.object(helper, "port_is_available", return_value=True):
            with self.assertRaisesRegex(ValueError, "still running"):
                helper.reuse_existing_debug_jvm(Path("C:/nwclient"))

    def test_new_game_can_start_on_free_port(self):
        from unittest import mock
        import nwclient_debug_start as helper
        with mock.patch.object(helper, "same_workspace_java_is_running", return_value=False), \
             mock.patch.object(helper, "port_is_available", return_value=True):
            self.assertFalse(helper.reuse_existing_debug_jvm(Path("C:/nwclient"))


if __name__ == "__main__":
    unittest.main()
