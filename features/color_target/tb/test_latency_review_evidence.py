"""Reject incomplete/contradictory review evidence; no RTL pass claim."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_latency_handoff_review import EXPECTED_CHECKS, parse_case


def fixture(fail=None):
    rows = ["CASE id=0"]
    for name in sorted(EXPECTED_CHECKS[0]):
        bad = name == fail
        rows.append(f"CHECK setup=0 name={name} expected=1 actual={0 if bad else 1} pass={0 if bad else 1}")
    rows.append(f"LATENCY_REVIEW_COMPLETE id=0 checks=5 setup_failures=0 requirement_failures={int(fail is not None)}")
    return "\n".join(rows) + "\n"


class EvidenceTests(unittest.TestCase):
    def test_valid_and_functional_failure_are_distinct(self):
        self.assertTrue(parse_case(fixture(), 0, True)["requirements_satisfied"])
        row = parse_case(fixture("normal_stats_valid"), 0, True)
        self.assertTrue(row["evidence_valid"])
        self.assertFalse(row["requirements_satisfied"])

    def test_tool_failure_cannot_be_a_functional_witness(self):
        self.assertFalse(parse_case(fixture("normal_stats_valid"), 0, False)["evidence_valid"])

    def test_missing_duplicate_or_inconsistent_checks_are_rejected(self):
        text = fixture()
        row = text.splitlines()[1] + "\n"
        for invalid in (text.replace(row, ""), text + row,
                        text.replace("actual=1 pass=1", "actual=0 pass=1", 1),
                        text.replace("requirement_failures=0", "requirement_failures=1"),
                        text.replace("CASE id=0", "CASE id=7"),
                        text + text.splitlines()[-1] + "\n"):
            self.assertFalse(parse_case(invalid, 0, True)["evidence_valid"])

    def test_setup_failure_invalidates_evidence(self):
        text = fixture("normal_stats_valid").replace(
            "setup=0 name=normal_stats_valid", "setup=1 name=normal_stats_valid").replace(
            "setup_failures=0 requirement_failures=1", "setup_failures=1 requirement_failures=0")
        self.assertFalse(parse_case(text, 0, True)["evidence_valid"])


if __name__ == "__main__":
    unittest.main()
