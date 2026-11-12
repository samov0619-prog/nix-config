"""Actual monitor parsing, read-only collection and append-only loop with fake devices."""

from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "gpu-monitor.py"
SPEC = importlib.util.spec_from_file_location("gpu_monitor", SOURCE)
monitor = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = monitor
SPEC.loader.exec_module(monitor)
VALID = "NVIDIA GeForce RTX 5060 Laptop GPU, 67, 62.45, 98, 4096, 8192\n"


class MonitorTests(unittest.TestCase):
    def test_real_query_fields_and_vram_percentage(self):
        metric = monitor.parse_metrics(VALID)
        self.assertEqual(metric.temperature, 67)
        self.assertEqual(metric.watts, 62.45)
        self.assertEqual(metric.utilization, 98)
        self.assertEqual(metric.memory_percent, 50)

    def test_unsupported_values_are_not_invented_zeroes(self):
        metric = monitor.parse_metrics("GPU, N/A, [Not Supported], [N/A], N/A, 8192")
        self.assertIsNone(metric.memory_percent)
        text = monitor.row(monitor.Sample("12:00:00", "balanced", metric))
        self.assertIn("n/a", text)

    def test_invalid_metrics_are_rejected(self):
        for value in (
            "", VALID + VALID, "GPU, 50, 10, 101, 1, 2",
            "GPU, nan, 10, 10, 1, 2", "GPU, 50, -1, 10, 1, 2",
            "GPU, 50, 10, 10, 3, 2", "GPU, 50, 10, 10, 0, 0",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                monitor.parse_metrics(value)

    def test_collection_is_read_only_with_bounded_timeouts(self):
        replies = [subprocess.CompletedProcess([], 0, "performance\n"),
                   subprocess.CompletedProcess([], 0, VALID)]
        with patch.object(monitor.subprocess, "run", side_effect=replies) as run:
            sample = monitor.collect("0000:02:00.0")
        self.assertEqual(sample.profile, "performance")
        self.assertFalse(sample.error)
        self.assertEqual(run.call_args_list[0].args[0], ["powerprofilesctl", "get"])
        self.assertEqual(run.call_args_list[1].args[0], [
            "nvidia-smi", "--id=0000:02:00.0", f"--query-gpu={monitor.FIELDS}",
            "--format=csv,noheader,nounits",
        ])
        self.assertEqual([call.kwargs["timeout"] for call in run.call_args_list], [1, 2])

    def test_profile_failure_does_not_hide_valid_gpu_metrics(self):
        with patch.object(monitor.subprocess, "run", side_effect=[
            FileNotFoundError(), subprocess.CompletedProcess([], 0, VALID),
        ]):
            sample = monitor.collect("0")
        self.assertEqual(sample.profile, "?")
        self.assertIsNotNone(sample.metrics)
        self.assertIn("PPD", sample.error)

    def test_query_failure_is_not_a_stale_success(self):
        with patch.object(monitor.subprocess, "run", side_effect=[
            subprocess.CompletedProcess([], 0, "balanced\n"),
            subprocess.TimeoutExpired("nvidia-smi", 2),
        ]):
            sample = monitor.collect("0")
        self.assertIsNone(sample.metrics)
        self.assertIn("query failed", monitor.row(sample))

    def test_unknown_profile_is_not_mislabeled_as_balanced(self):
        with patch.object(monitor.subprocess, "run", side_effect=[
            subprocess.CompletedProcess([], 0, "unknown\n"),
            subprocess.CompletedProcess([], 0, VALID),
        ]):
            sample = monitor.collect("0")
        self.assertEqual(sample.profile, "?")
        self.assertIn("PPD", sample.error)

    def test_once_performs_one_collection_and_exits(self):
        sample = monitor.Sample("12:00:00", "balanced", monitor.parse_metrics(VALID))
        with patch.object(monitor, "collect", return_value=sample) as collect, \
             patch.object(monitor.signal, "signal"), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(monitor.main(["--once"]), 0)
        collect.assert_called_once_with("0000:02:00.0")
        self.assertIn("50.0", output.getvalue())

    def test_invalid_interval_never_queries_gpu(self):
        with patch.object(monitor, "collect") as collect:
            for value in ("0", "-1", "nan", "inf"):
                with self.subTest(value=value), redirect_stdout(io.StringIO()), \
                     patch.object(monitor.sys, "stderr", io.StringIO()), self.assertRaises(SystemExit):
                    monitor.main([f"--interval={value}", "--once"])
        collect.assert_not_called()

    def test_no_twenty_row_limit_and_profile_per_sample(self):
        metric = monitor.parse_metrics(VALID)
        samples = [monitor.Sample(f"12:00:{index:02}", "balanced" if index < 20 else "performance", metric) for index in range(25)]
        output = io.StringIO()
        with patch.object(monitor, "collect", side_effect=samples), \
             patch.object(monitor.time, "monotonic", return_value=0), \
             patch.object(monitor.time, "sleep", side_effect=[None] * 24 + [KeyboardInterrupt]), \
             redirect_stdout(output):
            with self.assertRaises(KeyboardInterrupt):
                monitor.stream(SimpleNamespace(interval=5, gpu="0"))
        text = output.getvalue()
        self.assertIn("12:00:00", text)
        self.assertIn("12:00:24", text)
        self.assertIn("balanced", text)
        self.assertIn("performance", text)
        self.assertEqual(len([line for line in text.splitlines() if line.startswith("12:00:")]), 25)

    def test_terminal_control_codes_are_removed(self):
        self.assertEqual(monitor.safe_text("GPU\x1b[2J\n"), "GPU?[2J?")

    def test_loop_accounts_for_query_time_without_bursting(self):
        sample = monitor.Sample("12:00:00", "balanced", monitor.parse_metrics(VALID))
        with patch.object(monitor, "collect", return_value=sample) as collect, \
             patch.object(monitor.time, "monotonic", side_effect=[0, 0.5, 5, 12]), \
             patch.object(monitor.time, "sleep", side_effect=[None, KeyboardInterrupt]) as sleep, \
             redirect_stdout(io.StringIO()):
            with self.assertRaises(KeyboardInterrupt):
                monitor.stream(SimpleNamespace(interval=5, gpu="0"))
        self.assertEqual(collect.call_count, 2)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [4.5, 5])


if __name__ == "__main__":
    unittest.main()
