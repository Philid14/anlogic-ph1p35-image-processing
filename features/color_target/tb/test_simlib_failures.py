"""Literal failure injection at the shared simulator boundary; no FPGA claim."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]/"tools/simlib.py"
spec = importlib.util.spec_from_file_location("target_simlib", SOURCE)
simlib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simlib)


class ToolFailureWitnesses(unittest.TestCase):
    def probe(self, kind, fail_stage=None, code=7, raw=b"DONE\r\n", launch=False):
        seen = []
        with tempfile.TemporaryDirectory(prefix="target_tool_witness_") as td:
            directory = Path(td)
            def fake(command, **kwargs):
                stage = Path(command[0]).stem
                seen.append(stage)
                if launch and stage == fail_stage:
                    raise OSError("injected unavailable executable")
                return subprocess.CompletedProcess(command, code if stage == fail_stage else 0,
                    raw if stage == fail_stage else b"DONE\r\n")
            with patch.object(simlib, "pick", return_value=(kind, (directory, "test fixture"))), \
                 patch.object(simlib, "find_iverilog", return_value=("iverilog", "vvp", "fixture")), \
                 patch.object(simlib.subprocess, "run", side_effect=fake), \
                 patch.dict(os.environ, COLOR_TARGET_SIM_LOG_DIR=str(directory/"logs")):
                result = simlib.simulate([directory/"source.v"], "tb", {}, {}, workdir=directory)
            records = [json.loads(p.read_text(encoding="utf-8")) for p in (directory/"logs").glob("*/stage.json")]
            logs = [p.read_bytes() for p in (directory/"logs").glob("*/output.log")]
            self.assertEqual(len(records), len(seen))
            self.assertEqual(len(logs), len(seen))
            if fail_stage:
                bad = next(x for x in records if x["stage"] == fail_stage)
                self.assertFalse(bad["passed"])
                self.assertEqual(bad["exit_code"], None if launch else code)
                if not launch:
                    self.assertIn(raw, logs, "retain original CRLF bytes even on failure")
            return result, seen

    def test_both_backends_success(self):
        for kind, stages in [("modelsim", ["vlib", "vlog", "vsim"]), ("iverilog", ["iverilog", "vvp"])]:
            with self.subTest(kind=kind):
                result, seen = self.probe(kind)
                self.assertTrue(result[0])
                self.assertEqual(seen, stages)

    def test_nonzero_at_every_stage_even_with_completion(self):
        for kind, stages in [("modelsim", ["vlib", "vlog", "vsim"]), ("iverilog", ["iverilog", "vvp"])]:
            for index, stage in enumerate(stages):
                with self.subTest(stage=stage):
                    result, seen = self.probe(kind, stage)
                    self.assertFalse(result[0], "DONE cannot override exit 7")
                    self.assertIn("nonzero_exit", result[2])
                    self.assertEqual(seen, stages[:index+1], "stop before downstream tools")

    def test_error_marker_at_exit_zero(self):
        for kind, stage in [("modelsim", "vlib"), ("modelsim", "vlog"), ("modelsim", "vsim"),
                            ("iverilog", "iverilog"), ("iverilog", "vvp")]:
            with self.subTest(stage=stage):
                result, _ = self.probe(kind, stage, code=0, raw=b"** Error: injected\r\nDONE\r\n")
                self.assertFalse(result[0])
                self.assertIn("error_marker", result[2])

    def test_launch_failure_is_not_success(self):
        result, seen = self.probe("modelsim", "vlib", launch=True)
        self.assertFalse(result[0])
        self.assertIn("launch_error", result[2])
        self.assertEqual(seen, ["vlib"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
