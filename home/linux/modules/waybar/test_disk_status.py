"""Counter/sysfs fixtures and the actual helper; no disk load or GUI interaction."""

import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "disk_status", ROOT / "scripts/disk-status.py"
)
disk = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = disk
SPEC.loader.exec_module(disk)


class DiskStatusTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="waybar-disk-test-", dir="/tmp/opencode"
        )
        self.addCleanup(self.temporary.cleanup)
        self.sysfs = Path(self.temporary.name) / "sys"
        (self.sysfs / "dev/block").mkdir(parents=True)
        self.device = self.sysfs / "devices/block/sda"
        self.device.mkdir(parents=True)
        (self.device / "slaves").mkdir()
        (self.device / "diskseq").write_text("1\n")
        self.write_stats(100, 200, 300)
        partition = self.device / "sda2"
        partition.mkdir()
        (partition / "partition").write_text("2\n")
        (self.sysfs / "dev/block/8:2").symlink_to(partition)
        (self.sysfs / "dev/block/8:0").symlink_to(self.device)

    def write_stats(self, read, written, busy):
        (self.device / "stat").write_text(
            f"1 2 {read} 4 5 6 {written} 8 9 {busy} 11 12 13 14 15 16 17\n"
        )

    def collect(self, previous=None, timestamp=10):
        real_stat = os.stat

        def stat(path, *args, **kwargs):
            if path == "/fixture-home":
                return SimpleNamespace(st_dev=os.makedev(8, 2))
            return real_stat(path, *args, **kwargs)

        space = SimpleNamespace(
            f_blocks=100 * disk.GIB, f_bfree=25 * disk.GIB,
            f_bavail=20 * disk.GIB, f_frsize=1,
        )
        with patch.object(disk.os, "stat", side_effect=stat), patch.object(
            disk.os, "statvfs", return_value=space
        ):
            return disk.collect(
                "/fixture-home", previous, sysfs=self.sysfs, clock=lambda: timestamp
            )

    def test_partition_uses_whole_device_and_kernel_fields(self):
        counters = disk.read_counters(os.makedev(8, 2), 10, self.sysfs)
        self.assertEqual(counters.device, "sda")
        self.assertEqual(
            (counters.read_sectors, counters.written_sectors, counters.busy_ms),
            (100, 200, 300),
        )

    def test_whole_device_and_nvme_names_need_no_hardcoded_selector(self):
        self.assertEqual(
            disk.read_counters(os.makedev(8, 0), 10, self.sysfs).device, "sda"
        )
        nvme = self.device.with_name("nvme0n1")
        self.device.rename(nvme)
        (nvme / "nvme0n1p3").mkdir()
        (nvme / "nvme0n1p3/partition").write_text("3\n")
        (self.sysfs / "dev/block/259:3").symlink_to(nvme / "nvme0n1p3")
        self.assertEqual(
            disk.read_counters(os.makedev(259, 3), 10, self.sysfs).device,
            "nvme0n1",
        )

    def test_rates_use_elapsed_time_and_512_byte_stat_sectors(self):
        _, previous = self.collect()
        self.write_stats(100 + 10240, 200 + 20480, 300 + 2500)
        output, current = self.collect(previous, timestamp=15)
        self.assertEqual(disk.rates(previous, current), (50, 1, 2))
        self.assertEqual(output["text"], "disk:50% · 20/100 GiB")
        self.assertIn("Read: 1.0 MiB/s · Write: 2.0 MiB/s", output["tooltip"])
        self.assertEqual(output["class"], "ready")

    def test_available_excludes_reserved_blocks_and_first_sample_is_not_zero(self):
        output, _ = self.collect()
        self.assertEqual(output["text"], "disk:— · 20/100 GiB")
        self.assertIn("20.0 / 100.0 GiB", output["tooltip"])
        self.assertIn("first I/O interval", output["tooltip"])

    def test_idle_and_clamped_busy_values(self):
        _, old = self.collect()
        idle = disk.Counters("sda", old.identity, 15, 100, 200, 300)
        busy = disk.Counters("sda", old.identity, 15, 100, 200, 10300)
        self.assertEqual(disk.rates(old, idle), (0, 0, 0))
        self.assertEqual(disk.rates(old, busy), (100, 0, 0))

    def test_counter_reset_nonpositive_time_and_replacement_rebaseline(self):
        _, old = self.collect()
        for current in (
            disk.Counters("sda", old.identity, 15, 99, 200, 300),
            disk.Counters("sda", old.identity, 10, 100, 200, 300),
            disk.Counters("sda", old.identity, 9, 100, 200, 300),
        ):
            self.assertIsNone(disk.rates(old, current))
        (self.device / "diskseq").write_text("2\n")
        output, _ = self.collect(old, timestamp=15)
        self.assertIn("disk:—", output["text"])

    def test_missing_or_stacked_device_keeps_space_without_fake_idle(self):
        (self.device / "slaves/dm-child").touch()
        output, current = self.collect()
        self.assertIsNone(current)
        self.assertEqual(output["text"], "disk:— · 20/100 GiB")
        self.assertIn("I/O unavailable", output["tooltip"])
        (self.sysfs / "dev/block/8:2").unlink()
        output, current = self.collect()
        self.assertIsNone(current)
        self.assertEqual(output["class"], "io-unavailable")

    def test_malformed_counters_are_unavailable(self):
        for value in ("1 2 3", "not counters", "1 2 -1 4 5 6 7 8 9 10 11"):
            (self.device / "stat").write_text(value)
            output, current = self.collect()
            self.assertIsNone(current)
            self.assertNotIn("0%", output["text"])

    def test_filesystem_failure_is_explicit(self):
        with patch.object(disk.os, "stat", side_effect=OSError):
            output, current = disk.collect("/fixture-home")
        self.assertEqual(output["text"], "disk:—")
        self.assertEqual(output["class"], "unavailable")
        self.assertIsNone(current)

    def test_actual_cli_emits_one_json_line_per_sample_without_state_files(self):
        missing = Path(self.temporary.name) / "missing"
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/disk-status.py"),
             "--path", str(missing), "--interval", "0.05", "--samples", "2"],
            check=True, capture_output=True, text=True, timeout=5,
        )
        lines = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(line["text"] == "disk:—" for line in lines))
        self.assertFalse(missing.exists())

    def test_all_gui_configs_have_a_continuous_worker(self):
        linux = ROOT.parents[1]
        # Preserve quoted strings while removing JSONC comments/trailing commas.
        for host in ("laptop", "desktop", "laptop-next"):
            text = (linux / host / "waybar-config.jsonc").read_text()
            text = re.sub(
                r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/',
                lambda match: match[0] if match[0].startswith('"') else "",
                text,
            )
            text = re.sub(
                r'"(?:\\.|[^"\\])*"|,\s*(?=[}\]])',
                lambda match: match[0] if match[0].startswith('"') else "",
                text,
            )
            config = json.loads(text)
            self.assertEqual(config["modules-center"].count("custom/disk"), 1)
            custom = config["custom/disk"]
            self.assertEqual(custom["return-type"], "json")
            self.assertEqual(custom["restart-interval"], 5)
            self.assertNotIn("interval", custom)
            self.assertNotIn("signal", custom)
            self.assertNotIn("tooltip-format", custom)
            self.assertEqual(custom["exec"], "~/.config/waybar/scripts/disk-status")


if __name__ == "__main__":
    unittest.main()
