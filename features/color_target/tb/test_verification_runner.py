"""Failure witnesses for the verification launcher; no FPGA claims."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]/"run_verification.py"
spec = importlib.util.spec_from_file_location("verification_runner", SOURCE)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class FailureWitnesses(unittest.TestCase):
    def probe(self, code, timeout=10):
        with tempfile.TemporaryDirectory(prefix="target_verify_witness_") as directory:
            path = Path(directory)/"child.log"
            result = runner.execute([sys.executable, "-u", "-c", code], path, r"^DONE$", timeout)
            self.assertTrue(path.is_file(), "raw child output must survive failure")
            return result

    def test_success_needs_exit_and_completion(self):
        self.assertTrue(self.probe("print('DONE')")["passed"])

    def test_printing_pass_cannot_hide_child_failure(self):
        got = self.probe("print('DONE'); raise SystemExit(7)")
        self.assertEqual((got["passed"], got["exit_code"], got["failure"]), (False, 7, "nonzero_exit"))

    def test_clean_exit_without_completion_is_failure(self):
        self.assertEqual(self.probe("print('partial output')")["failure"], "missing_completion")

    def test_fail_marker_cannot_be_hidden_by_completion(self):
        self.assertEqual(self.probe("print('FAIL sample mismatch'); print('DONE')")["failure"], "failure_marker")

    def test_timeout_cannot_be_hidden_by_early_completion(self):
        got = self.probe("import time; print('DONE'); time.sleep(30)", timeout=0.5)
        self.assertEqual((got["passed"], got["failure"]), (False, "timeout"))

    def test_track_characterization_carries_open_gaps(self):
        with tempfile.TemporaryDirectory(prefix="target_verify_track_") as directory:
            path = Path(directory)
            (path/"summary.json").write_text('{"trace_matched":true,"observed":{"S":[1]},"open_gaps":{"S":"OPEN"}}', encoding="utf-8")
            got = runner.inspect_report("track_audit", path)
            self.assertEqual(got["open_gaps"], {"S": "OPEN"})
            self.assertIn("NOT REQUIREMENTS PASS", got["scope"])

    def test_display_tool_failure_cannot_count_as_mutation_detection(self):
        rows = [dict(mutation=i, matched=True, tool_ok=True, complete=True,
                     checks=187, failures=0 if i == 0 else 1) for i in range(6)]
        with tempfile.TemporaryDirectory(prefix="target_verify_display_") as directory:
            path = Path(directory)
            report = dict(passed=True, source_unchanged=True, jobs=rows)
            (path/"summary.json").write_text(json.dumps(report), encoding="utf-8")
            self.assertEqual(runner.inspect_report("display_transactions", path)["negative_controls"], 5)
            rows[5]["tool_ok"] = False
            (path/"summary.json").write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaises(AssertionError):
                runner.inspect_report("display_transactions", path)

    def test_incomplete_transaction_report_cannot_pass(self):
        with tempfile.TemporaryDirectory(prefix="target_verify_transactions_") as directory:
            path = Path(directory)
            report = dict(passed=True, source_unchanged=True, cases=[dict(passed=True)]*32)
            (path/"summary.json").write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaises(AssertionError):
                runner.inspect_report("frame_transactions", path)


if __name__ == "__main__":
    unittest.main()
