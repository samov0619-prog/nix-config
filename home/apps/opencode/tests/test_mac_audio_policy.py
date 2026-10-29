"""Corporate Mac overlay must not inherit personal home audio/attention plugins."""
import json
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1]
MAC = SOURCE / "macos"


class MacAudioPolicyTests(unittest.TestCase):
    def test_mac_uses_builtin_sounds_without_home_overrides(self):
        attention = json.loads((MAC / "opencode/cli.json").read_text()).get("attention", {})
        self.assertFalse(attention.get("sounds"), "Personal home sound overrides must not reach the corporate Mac")
        self.assertIn(attention.get("sound_pack"), (None, "opencode.default"))
        audio = [path.relative_to(MAC) for path in MAC.rglob("*")
                 if path.suffix.lower() in {".mp3", ".wav", ".ogg", ".oga", ".flac", ".m4a"}]
        self.assertEqual(audio, [], "Do not vendor personal audio into either Mac config layer")

    def test_mac_keeps_native_notification_handler(self):
        cli = json.loads((MAC / "opencode/cli.json").read_text())
        self.assertFalse(cli.get("plugins"), "Do not restore home attention directives in the Mac CLI seed")
        plugins = MAC / "opencode/plugins"
        self.assertFalse((plugins / "session-notifications").exists())
        self.assertFalse((plugins / "quiet-urgency").exists())


if __name__ == "__main__":
    unittest.main()
