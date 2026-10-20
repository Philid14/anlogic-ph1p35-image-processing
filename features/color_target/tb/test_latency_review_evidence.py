"""Reject incomplete/contradictory review evidence; no RTL pass claim."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_latency_handoff_review import CASES, CHECK_SPECS, KINDS, gate_results, parse_case


def fixture(fail=None):
    rows = ["CASE id=0"]
    for name, (setup, expected) in sorted(CHECK_SPECS[0].items()):
        bad = name == fail
        actual = (0 if expected else 1) if bad else expected
        rows.append(f"CHECK setup={int(setup)} name={name} expected={expected} actual={actual} pass={int(not bad)}")
    setup_failed = fail is not None and CHECK_SPECS[0][fail][0]
    requirement_failed = fail is not None and not CHECK_SPECS[0][fail][0]
    rows.append(f"LATENCY_REVIEW_COMPLETE id=0 checks=5 setup_failures={int(setup_failed)} requirement_failures={int(requirement_failed)}")
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
        self.assertFalse(parse_case(fixture('normal_complete_first_display'), 0, True)['evidence_valid'])
        text = fixture("normal_stats_valid").replace(
            "setup=0 name=normal_stats_valid", "setup=1 name=normal_stats_valid").replace(
            "setup_failures=0 requirement_failures=1", "setup_failures=1 requirement_failures=0")
        self.assertFalse(parse_case(text, 0, True)["evidence_valid"])

    def test_changed_gold_cannot_hide_wrong_result(self):
        text = fixture().replace('name=normal_stats_valid expected=1 actual=1 pass=1',
                                 'name=normal_stats_valid expected=0 actual=0 pass=1')
        self.assertFalse(parse_case(text, 0, True)["evidence_valid"])

    def test_nonbinary_flags_rejected(self):
        for old, new in [('pass=1', 'pass=2'), ('setup=0', 'setup=2')]:
            self.assertFalse(parse_case(fixture().replace(old, new, 1), 0, True)["evidence_valid"])

    def test_check_kind_cannot_be_reclassified_by_log(self):
        text = fixture().replace('setup=0 name=normal_stats_valid', 'setup=1 name=normal_stats_valid')
        self.assertFalse(parse_case(text, 0, True)["evidence_valid"])

    def test_original_real_counterexamples_are_now_rejected(self):
        # This is the exact corruption accepted by 131b438; retain valid
        # completion and numeric equality to distinguish it from truncation.
        bad = fixture().replace('name=normal_no_alarm expected=0 actual=0 pass=1',
                                'name=normal_no_alarm expected=1 actual=1 pass=1')
        self.assertFalse(parse_case(bad, 0, True)["requirements_satisfied"])


class GateTests(unittest.TestCase):
    def jobs(self):
        return [dict(case_id=i, kind=KINDS[i], evidence_valid=True, requirements_satisfied=True)
                for i in range(len(CASES))]

    def test_component_gate_does_not_certify_main_or_freeze_policy(self):
        rows = self.jobs()
        for i in (4, 5, 6, 7):
            rows[i]['requirements_satisfied'] = False
        component = gate_results(rows, True, 'component')
        self.assertTrue(component['selected_gate_satisfied'])
        self.assertFalse(component['requirements_satisfied'])
        self.assertFalse(component['integration_ready'])
        self.assertFalse(gate_results(rows, True, 'integration')['selected_gate_satisfied'])
        rows[2]['requirements_satisfied'] = False
        self.assertFalse(gate_results(rows, True, 'component')['selected_gate_satisfied'])

    def test_missing_invalid_duplicate_or_changed_evidence_blocks_all_gates(self):
        rows = self.jobs()
        self.assertFalse(gate_results(rows[:-1], True, 'component')['evidence_valid'])
        self.assertFalse(gate_results(rows+[rows[0]], True, 'component')['evidence_valid'])
        self.assertFalse(gate_results(rows, False, 'component')['evidence_valid'])
        rows[4]['evidence_valid'] = False
        self.assertFalse(gate_results(rows, True, 'component')['selected_gate_satisfied'])


if __name__ == "__main__":
    unittest.main()
