"""Actual Blueman dialog class; mocked GTK/GLib, no display or Bluetooth access."""

import argparse
import ast
from pathlib import Path
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
import unittest


HERE = Path(__file__).resolve().parents[1]
SOURCE_FILE = "blueman/gui/Notification.py"
ORIGINAL = ""
TEST_SOURCE = ""


def read_source(path):
    if path.is_dir():
        return (path / SOURCE_FILE).read_text()
    if path.suffix == ".py":
        return path.read_text()
    with tarfile.open(path) as archive:
        members = [m for m in archive.getmembers() if m.isfile()
                   and "/".join(Path(m.name).parts[1:]) == SOURCE_FILE]
        if len(members) != 1:
            raise ValueError("Expected exactly one upstream Notification.py")
        return archive.extractfile(members[0]).read().decode()


class Scheduler:
    SOURCE_REMOVE = False

    def __init__(self):
        self.timers = {}
        self.next_id = 1

    def timeout_add(self, delay, callback):
        identifier = self.next_id
        self.next_id += 1
        self.timers[identifier] = (delay, callback)
        return identifier

    def source_remove(self, identifier):
        del self.timers[identifier]

    def fire(self):
        identifier = next(iter(self.timers))
        _, callback = self.timers.pop(identifier)
        return callback()


class Window:
    def __init__(self, **_kwargs):
        self.props = SimpleNamespace()
        self.signals = {}
        self.visible = False

    def set_name(self, _name):
        pass

    def resize(self, *_args):
        pass

    def add_button(self, *_args):
        pass

    def set_opacity(self, _opacity):
        pass

    def connect(self, signal, callback):
        self.signals[signal] = callback

    def present(self):
        self.visible = True

    def hide(self):
        self.visible = False
        if "hide" in self.signals:
            self.signals["hide"](self)

    def destroy(self):
        self.visible = False
        if "destroy" in self.signals:
            self.signals["destroy"](self)


def dialog_class(text, scheduler):
    tree = ast.parse(text)
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                and n.name == "_NotificationDialog")
    namespace = {
        "Gtk": SimpleNamespace(MessageDialog=Window,
                               MessageType=SimpleNamespace(QUESTION=1),
                               ButtonsType=SimpleNamespace(NONE=0),
                               ResponseType=SimpleNamespace(DELETE_EVENT=-4),
                               WindowPosition=SimpleNamespace(CENTER=1)),
        "GLib": scheduler, "Fade": lambda _window: None, "OPACITY_START": 0.7,
    }
    exec("from __future__ import annotations\n" + ast.unparse(node), namespace)
    return namespace["_NotificationDialog"]


class DialogContracts(unittest.TestCase):
    def setUp(self):
        if not TEST_SOURCE:
            self.skipTest("Run this harness with an explicit Blueman source path")
        self.scheduler = Scheduler()
        self.dialog = dialog_class(TEST_SOURCE, self.scheduler)

    def create(self, **kwargs):
        return self.dialog("Mouse", "Disconnected", **kwargs)

    def test_default_starts_at_show_and_expires_after_3_seconds(self):
        window = self.create()
        self.assertFalse(self.scheduler.timers)
        window.show()
        self.assertEqual([t[0] for t in self.scheduler.timers.values()], [3000])
        self.assertIs(self.scheduler.fire(), False)
        self.assertFalse(window.visible)
        self.assertFalse(self.scheduler.timers)

    def test_explicit_timeout_is_preserved(self):
        window = self.create(timeout=3200)
        window.show()
        self.assertEqual([t[0] for t in self.scheduler.timers.values()], [3200])

    def test_zero_timeout_is_persistent(self):
        window = self.create(timeout=0)
        window.show()
        self.assertTrue(window.visible)
        self.assertFalse(self.scheduler.timers)

    def test_action_requests_stay_pending_until_answer(self):
        responses = []
        for timeout in (-1, 100):
            window = self.create(timeout=timeout, actions=[("confirm", "Confirm"), ("deny", "Deny")],
                                 actions_cb=responses.append)
            window.show()
            self.assertFalse(self.scheduler.timers)
            self.assertTrue(window.visible)
            window.dialog_response(window, 100)
            self.assertFalse(window.visible)
        self.assertEqual(responses, ["confirm", "confirm"])

    def test_manual_close_hide_destroy_and_response_cancel_timer(self):
        for action in ("close", "hide", "destroy", "response"):
            with self.subTest(action=action):
                window = self.create()
                window.show()
                self.assertEqual(len(self.scheduler.timers), 1)
                if action == "response":
                    window.dialog_response(window, -4)
                else:
                    getattr(window, action)()
                self.assertFalse(self.scheduler.timers)
                self.assertFalse(window.visible)
                window.close()

    def test_repeated_show_renews_only_one_timer(self):
        window = self.create()
        window.show()
        first = next(iter(self.scheduler.timers))
        window.show()
        self.assertEqual(len(self.scheduler.timers), 1)
        self.assertNotIn(first, self.scheduler.timers)

    def test_message_update_does_not_resurrect_after_expiry(self):
        window = self.create()
        window.show()
        self.scheduler.fire()
        window.set_message("Connected 90%")
        self.assertFalse(window.visible)
        self.assertFalse(self.scheduler.timers)


class BaselineReproduction(unittest.TestCase):
    def test_unpatched_dialog_ignores_default_and_explicit_timeouts(self):
        if not ORIGINAL:
            self.skipTest("Run this harness with an explicit upstream source path")
        for timeout in (-1, 3200):
            scheduler = Scheduler()
            window = dialog_class(ORIGINAL, scheduler)("Mouse", "Disconnected", timeout)
            window.show()
            self.assertTrue(window.visible)
            self.assertFalse(scheduler.timers)


def main():
    global ORIGINAL, TEST_SOURCE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Upstream source directory, tarball or Notification.py")
    parser.add_argument("--check-upstream", action="store_true", help="Run contracts without applying the patch")
    args = parser.parse_args()
    ORIGINAL = read_source(args.source)
    TEST_SOURCE = ORIGINAL
    if not args.check_upstream:
        with tempfile.TemporaryDirectory(prefix="blueman-timeout-", dir="/tmp/opencode") as temporary:
            root = Path(temporary)
            target = root / SOURCE_FILE
            target.parent.mkdir(parents=True)
            target.write_text(ORIGINAL)
            result = subprocess.run(
                ["patch", "--batch", "--forward", "--fuzz=0", "-p1", "-i",
                 str(HERE / "notification-timeout.patch")], cwd=root,
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode or "offset" in result.stdout:
                raise RuntimeError(result.stdout + result.stderr)
            TEST_SOURCE = target.read_text()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DialogContracts)
    if not args.check_upstream:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(BaselineReproduction))
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
