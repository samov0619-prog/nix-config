"""Run the real compress plugin with fake Yazi APIs, never personal files or UI."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


PLUGIN = None
LUA = None
SEVEN_ZIP = None

HARNESS = r'''
local plugin_path, scenario = arg[1], arg[2]
local function record(...)
    local fields = { ... }
    for i, value in ipairs(fields) do fields[i] = tostring(value) end
    io.write(table.concat(fields, "\0"), "\0\0")
end
local url_mt = { __tostring = function(self) return self.path end }
function Url(path)
    if type(path) == "table" then return path end
    return setmetatable({ path = path }, url_mt)
end
url_mt.__index = function(self, key)
    if key == "name" then return self.path:match("([^/]+)$") end
    if key == "parent" then return Url(self.path:match("^(.*)/[^/]+$")) end
    if key == "join" then
        return function(parent, child) return Url(parent.path .. "/" .. tostring(child)) end
    end
end
local inputs = {}
local function input(value, event) inputs[#inputs + 1] = { value, event } end
local password_mode = scenario ~= "plain" and scenario ~= "archive-cancel"
input(scenario == "unsupported" and "fixture.tar" or "fixture.zip",
      scenario == "archive-cancel" and 0 or 1)
if password_mode and scenario ~= "unsupported" then
    input(scenario == "password-empty" and "" or "fixture-only",
          scenario == "password-cancel" and 0 or 1)
end
if scenario == "repeat" then input("plain.zip", 1) end
local input_index = 0
ya = {
    target_family = function() return "unix" end,
    sync = function(callback) return callback end,
    emit = function() end,
    quote = function(value) return tostring(value) end,
    notify = function(value) record("notify", value.level, value.content) end,
    input = function()
        input_index = input_index + 1
        assert(inputs[input_index], "Unexpected input request")
        return table.unpack(inputs[input_index])
    end,
}
local file = { url = Url("/fixture/input space 'тест'.txt"), name = "input space 'тест'.txt" }
cx = { active = { selected = {}, current = { cwd = Url("/fixture"), hovered = file } } }
if scenario == "selected" then cx.active.selected = { file } end
os.execute = function(command)
    return command == "command -v 7zz >/dev/null 2>&1"
        or command == "command -v tar >/dev/null 2>&1"
end
fs = {
    unique = function(_, url) return url end,
    create = function(_, url) record("create", url); return true end,
    remove = function(_, url) record("remove", url); return true end,
    rename = function(from, to) record("rename", from, to); return true end,
}
function Command(name)
    local command = { name = name, args = {} }
    function command:arg(values)
        if type(values) ~= "table" then values = { values } end
        for _, value in ipairs(values) do self.args[#self.args + 1] = tostring(value) end
        return self
    end
    function command:cwd(value) self.directory = value; return self end
    function command:spawn() return self end
    function command:wait()
        record("command", self.name, self.directory or "", table.unpack(self.args))
        return { success = true }
    end
    return command
end
local plugin = assert(loadfile(plugin_path))()
plugin:entry({ args = password_mode and { "-p" } or {} })
if scenario == "repeat" then plugin:entry({ args = {} }) end
'''


class CompressTests(unittest.TestCase):
    def run_plugin(self, scenario):
        with tempfile.TemporaryDirectory(
            prefix="yazi-compress-api-", dir="/tmp/opencode"
        ) as temporary:
            root = Path(temporary)
            harness = root / "harness.lua"
            harness.write_text(HARNESS)
            environment = os.environ.copy()
            environment["HOME"] = str(root)
            result = subprocess.run(
                [str(LUA), str(harness), str(PLUGIN), scenario],
                cwd=root,
                env=environment,
                capture_output=True,
                timeout=5,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode())
        return [
            record.decode().split("\0")
            for record in result.stdout.split(b"\0\0")
            if record
        ]

    def assert_no_archive(self, scenario):
        records = self.run_plugin(scenario)
        self.assertFalse([r for r in records if r[0] in ("create", "command", "rename")])
        return records

    def test_archive_name_cancel_does_nothing(self):
        self.assert_no_archive("archive-cancel")

    def test_password_cancel_does_not_create_plaintext_archive(self):
        self.assert_no_archive("password-cancel")

    def test_empty_password_does_not_create_plaintext_archive(self):
        self.assert_no_archive("password-empty")

    def test_password_mode_rejects_unencrypted_format(self):
        records = self.assert_no_archive("unsupported")
        self.assertTrue([r for r in records if r[:2] == ["notify", "error"]])

    def test_plain_zip_preserves_hovered_filename(self):
        commands = [r for r in self.run_plugin("plain") if r[0] == "command"]
        self.assertEqual(
            commands,
            [["command", "7zz", "/fixture", "a", "-tzip",
              "/fixture/.tmp_compress/fixture.zip", "input space 'тест'.txt"]],
        )

    def test_selected_password_zip_uses_single_password_argument(self):
        commands = [r for r in self.run_plugin("selected") if r[0] == "command"]
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][1:3], ["7zz", "/fixture"])
        self.assertEqual(commands[0].count("-Pfixture-only"), 1)
        self.assertEqual(commands[0][-1], "input space 'тест'.txt")

    def test_next_plain_invocation_does_not_reuse_password_or_flags(self):
        commands = [r for r in self.run_plugin("repeat") if r[0] == "command"]
        self.assertEqual(len(commands), 2)
        self.assertIn("-Pfixture-only", commands[0])
        self.assertNotIn("-Pfixture-only", commands[1])
        self.assertIn("/fixture/.tmp_compress/plain.zip", commands[1])

    def test_real_7zz_round_trip_and_wrong_password(self):
        if SEVEN_ZIP is None:
            self.skipTest("Pass --seven-zip for the real tiny ZIP fixture")
        with tempfile.TemporaryDirectory(
            prefix="yazi-compress-zip-", dir="/tmp/opencode"
        ) as temporary:
            root = Path(temporary)
            filename = "input space 'тест'.txt"
            payload = b"Synthetic archive fixture\n"
            (root / filename).write_bytes(payload)
            archive = root / "fixture.zip"
            commands = [r for r in self.run_plugin("selected") if r[0] == "command"]
            self.assertEqual(len(commands), 1)
            arguments = commands[0][3:]
            arguments[-2] = str(archive)
            subprocess.run(
                [str(SEVEN_ZIP), *arguments, "-mmt=1"],
                cwd=root, stdin=subprocess.DEVNULL, capture_output=True,
                check=True, timeout=10,
            )
            for password, succeeds in (("incorrect", False), ("fixture-only", True)):
                result = subprocess.run(
                    [str(SEVEN_ZIP), "x", "-so", f"-p{password}", str(archive), filename],
                    cwd=root, stdin=subprocess.DEVNULL, capture_output=True, timeout=10,
                )
                self.assertEqual(result.returncode == 0, succeeds)
                if succeeds:
                    self.assertEqual(result.stdout, payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plugin", type=Path, help="Patched compress main.lua")
    parser.add_argument("--lua", required=True, type=Path)
    parser.add_argument("--seven-zip", type=Path)
    parser.add_argument("--patch", type=Path, help="Apply the local fix to a temporary copy")
    options, remaining = parser.parse_known_args()
    PLUGIN = options.plugin.resolve()
    LUA = options.lua.resolve()
    SEVEN_ZIP = options.seven_zip.resolve() if options.seven_zip else None
    with tempfile.TemporaryDirectory(
        prefix="yazi-compress-source-", dir="/tmp/opencode"
    ) as temporary:
        if options.patch:
            candidate = Path(temporary) / "main.lua"
            shutil.copyfile(PLUGIN, candidate)
            subprocess.run(
                ["patch", "--batch", "--forward", "--fuzz=0", "-p1", "-i", str(options.patch.resolve())],
                cwd=temporary, check=True, capture_output=True,
            )
            PLUGIN = candidate
        unittest.main(argv=[__file__, *remaining])
