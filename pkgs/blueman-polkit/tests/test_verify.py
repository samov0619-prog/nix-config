"""Synthetic install-check fixtures; no real helper, Polkit or Bluetooth access."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify import verify


# Representative upstream contract: privileged action with admin authentication;
# the stock rule grants this action to wheel. These are fixtures, not shipped policy.
POLICY = """<policyconfig>
<action id="org.blueman.network.setup"><defaults>
<allow_inactive>no</allow_inactive>
<allow_active>auth_admin_keep</allow_active>
</defaults></action></policyconfig>"""
RULE = """polkit.addRule(function(action, subject) {
    if (action.id == "org.blueman.network.setup" && subject.isInGroup("wheel"))
        return polkit.Result.YES;
});
"""


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="blueman-polkit-test-", dir="/tmp/opencode"
        )
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.package = root / "package"
        self.source = root / "source"
        self.constants = self.package / "lib/python3.13/site-packages/blueman/Constants.py"
        self.policy = self.package / "share/polkit-1/actions/org.blueman.policy"
        self.rules = self.package / "share/polkit-1/rules.d/blueman.rules"
        files = {
            self.constants: "POLKIT = True\nraise RuntimeError('Do not import me')\n",
            self.policy: POLICY,
            self.rules: RULE,
            self.source / "data/configs/org.blueman.policy.in": POLICY,
            self.source / "data/configs/blueman.rules": RULE,
        }
        for path, text in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def test_enabled_support_and_unchanged_policy(self):
        verify(self.package, self.source)

    def test_disabled_support_is_rejected(self):
        self.constants.write_text("POLKIT = False\n")
        with self.assertRaisesRegex(ValueError, "POLKIT=True"):
            verify(self.package, self.source)

    def test_missing_flag_is_rejected(self):
        self.constants.write_text("VERSION = 'fixture'\n")
        with self.assertRaisesRegex(ValueError, "POLKIT=True"):
            verify(self.package, self.source)

    def test_non_boolean_flag_is_rejected(self):
        self.constants.write_text("POLKIT = 1\n")
        with self.assertRaisesRegex(ValueError, "POLKIT=True"):
            verify(self.package, self.source)

    def test_missing_policy_is_rejected(self):
        self.policy.unlink()
        with self.assertRaises(FileNotFoundError):
            verify(self.package, self.source)

    def test_relaxed_action_is_rejected(self):
        self.policy.write_text(POLICY.replace("auth_admin_keep", "yes"))
        with self.assertRaisesRegex(ValueError, "action defaults"):
            verify(self.package, self.source)

    def test_missing_action_is_rejected(self):
        self.policy.write_text("<policyconfig/>")
        with self.assertRaisesRegex(ValueError, "No Polkit actions"):
            verify(self.package, self.source)

    def test_modified_rule_is_rejected(self):
        self.rules.write_text(RULE + "// local override\n")
        with self.assertRaisesRegex(ValueError, "rules differ"):
            verify(self.package, self.source)

    def test_missing_rule_is_rejected(self):
        self.rules.unlink()
        with self.assertRaises(FileNotFoundError):
            verify(self.package, self.source)


if __name__ == "__main__":
    unittest.main()
