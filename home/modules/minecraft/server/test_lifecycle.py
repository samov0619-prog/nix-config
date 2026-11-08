#!/usr/bin/env python3
"""Check evaluated unit declarations and readiness without starting Minecraft."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
import unittest


class LifecycleTests(unittest.TestCase):
    def test_systemd_unit_graph_validates_without_starting_services(self):
        base = "/tmp/opencode" if Path("/tmp/opencode").is_dir() else None
        with tempfile.TemporaryDirectory(prefix="minecraft-unit-fixture-", dir=base) as temporary:
            root = Path(temporary)
            replacements = {
                "/fixture/packwiz/bin/packwiz": shutil.which("true"),
                "/fixture/java/bin/java": shutil.which("true"),
                "/fixture/curl/bin/curl": shutil.which("curl"),
            }
            self.assertTrue(all(replacements.values()), "true and curl CLIs are required")
            units = self.module["lifecycleUnits"]
            for name, unit in units.items():
                suffix = ".target" if name == "minecraft" else ".service"
                text = []
                for section, fields in unit.items():
                    text.append(f"[{section}]")
                    for key, value in fields.items():
                        if value == []:
                            continue
                        if isinstance(value, bool):
                            value = "yes" if value else "no"
                        elif isinstance(value, list):
                            value = " ".join(value)
                        value = re.sub(r"\\\s*\n\s*", " ", str(value)).strip()
                        for original, replacement in replacements.items():
                            value = value.replace(original, replacement)
                        text.append(f"{key}={value}")
                (root / (name + suffix)).write_text("\n".join(text) + "\n")
                if suffix == ".service":
                    wanted = root / "minecraft.target.wants"
                    wanted.mkdir(exist_ok=True)
                    (wanted / (name + suffix)).symlink_to(root / (name + suffix))
            environment = os.environ.copy()
            environment["SYSTEMD_UNIT_PATH"] = str(root) + ":"
            result = subprocess.run(
                [
                    "systemd-analyze", "--user", "--man=no", "--generators=no", "verify",
                    str(root / "minecraft.target"),
                    *[str(root / (name + ".service")) for name in units if name != "minecraft"],
                ],
                env=environment,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")

    def run_readiness(self, statuses):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                status = statuses[min(len(requests) - 1, len(statuses) - 1)]
                self.send_response(status)
                self.end_headers()
                self.wfile.write(b'pack-format = "packwiz:1.1.0"\n')

            def log_message(self, *_):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            command = shlex.split(
                self.module["lifecycleUnits"]["packwiz-serve"]["Service"]["ExecStartPost"]
            )
            self.assertEqual(command[0], "/fixture/curl/bin/curl")
            command[0] = shutil.which("curl")
            self.assertIsNotNone(command[0], "curl CLI is required")
            self.assertEqual(command[-1], "http://127.0.0.1:8180/pack.toml")
            command[-1] = f"http://127.0.0.1:{server.server_port}/pack.toml"
            environment = os.environ.copy()
            # The actual --noproxy flag must keep loopback off inherited proxies.
            environment.update(
                http_proxy="http://127.0.0.1:1",
                ALL_PROXY="http://127.0.0.1:1",
                no_proxy="",
                NO_PROXY="",
            )
            base = "/tmp/opencode" if Path("/tmp/opencode").is_dir() else None
            with tempfile.TemporaryDirectory(prefix="curl-config-fixture-", dir=base) as config:
                # --disable must prevent user curl settings from changing the probe.
                (Path(config) / ".curlrc").write_text('request = "POST"\n')
                environment["CURL_HOME"] = config
                result = subprocess.run(
                    command,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=40,
                    check=False,
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertTrue(requests)
        self.assertEqual(set(requests), {"/pack.toml"})
        return result, requests

    def test_ready_manifest_succeeds_without_proxy(self):
        result, requests = self.run_readiness([200])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(requests), 1)

    def test_transient_http_failure_is_retried(self):
        result, requests = self.run_readiness([503, 200])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(requests), 2)

    def test_missing_manifest_fails_with_bounded_production_retries(self):
        result, requests = self.run_readiness([404])
        self.assertNotEqual(result.returncode, 0)
        self.assertGreater(len(requests), 1)
        self.assertLessEqual(len(requests), 31)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module_json", type=Path)
    args, remaining = parser.parse_known_args()
    LifecycleTests.module = json.loads(args.module_json.read_text())
    unittest.main(argv=[__file__, *remaining])
