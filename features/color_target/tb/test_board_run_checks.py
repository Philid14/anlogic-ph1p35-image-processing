"""Software-only hard expectations; fixtures are not hardware observations."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOL = Path(__file__).resolve().parents[1]/'tools/check_board_run.py'
spec = importlib.util.spec_from_file_location('board_check', TOOL)
board = importlib.util.module_from_spec(spec); spec.loader.exec_module(board)


class BoardChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='target_board_software_test_')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.bit = self.base/'synthetic.bit'; self.bit.write_bytes(b'synthetic-unit-test-only')
        (self.base/'synthetic-observation.txt').write_text('NOT board evidence')
        sample = dict(boot_id='synthetic-1', t_s=30, phase='steady',
            identity_line='S00000001 F00000003 G00000001 L0 D0000 C0000 Q0000',
            reason_line='D0000 R0000 W0000 I0000 V0000 C0000 S0000 T0000 O0000',
            counters=dict(fifo_startup=0, fifo_steady=0),
            observations={k: True for k in board.OBSERVATIONS}, evidence=['synthetic-observation.txt'])
        second = copy.deepcopy(sample);second['t_s']=60
        self.data = dict(schema='target-board-run-v1',
            version=dict(tag='synthetic-test', source_commit='1'*40, bit_sha256=hashlib.sha256(self.bit.read_bytes()).hexdigest()),
            environment=dict(camera_height_mm=100, field_of_view_mm=[100, 100], lighting='synthetic', sensor_settings='synthetic'),
            samples=[sample,second])

    def run_check(self):
        return board.evaluate(self.data,self.base,self.bit)

    def test_complete_software_fixture_is_not_certified(self):
        r=self.run_check();self.assertEqual(r['assessment'],'NO_OBSERVED_FAILURE');self.assertEqual(r['board_acceptance'],'NOT_CERTIFIED')

    def test_steady_full_counter_increment_fails(self):
        self.data['samples'][1]['counters']['fifo_steady']=1
        self.assertEqual(self.run_check()['assessment'],'OBSERVED_FAILURE')

    def test_startup_events_are_not_steady_events(self):
        self.data['samples'][1]['counters']['fifo_startup']=2
        self.assertEqual(self.run_check()['assessment'],'NO_OBSERVED_FAILURE')

    def test_saturated_zero_delta_is_unknown(self):
        for s in self.data['samples']:s['counters']['fifo_steady']=65535
        r=self.run_check();self.assertEqual(r['assessment'],'INCOMPLETE')
        self.assertEqual(r['intervals'][0]['counters']['fifo_steady']['status'],'saturated_unknown')

    def test_reaching_saturation_retains_positive_lower_bound(self):
        self.data['samples'][0]['counters']['fifo_steady']=65534
        self.data['samples'][1]['counters']['fifo_steady']=65535
        r=self.run_check();self.assertEqual(r['assessment'],'OBSERVED_FAILURE')
        self.assertEqual(r['intervals'][0]['counters']['fifo_steady'],dict(status='lower_bound',value=1))

    def test_counter_decrease_not_wrapped(self):
        self.data['samples'][0]['counters']['fifo_steady']=65534
        r=self.run_check();self.assertEqual(r['assessment'],'INCOMPLETE')
        self.assertNotIn('value',r['intervals'][0]['counters']['fifo_steady'])

    def test_boot_change_prevents_delta(self):
        self.data['samples'][1]['boot_id']='synthetic-2'
        r=self.run_check();self.assertEqual(r['assessment'],'INCOMPLETE')
        self.assertEqual(r['intervals'][0]['status'],'boot_changed_no_delta')

    def test_missing_measurement_stays_incomplete(self):
        self.data['samples'][1]['observations']['video_live']=None
        self.assertEqual(self.run_check()['assessment'],'INCOMPLETE')

    def test_diagnostic_increment_is_review_not_automatic_hardware_failure(self):
        self.data['samples'][1]['reason_line']='D0001 R0000 W0000 I0000 V0000 C0000 S0000 T0000 O0000'
        self.assertEqual(self.run_check()['assessment'],'REVIEW_REQUIRED')

    def test_duplicate_and_skipped_display_ids_not_errors(self):
        self.assertEqual(self.run_check()['assessment'],'NO_OBSERVED_FAILURE')
        self.data['samples'][1]['identity_line']='S00000001 F00000009 G00000002 L1 D0000 C0000 Q0000'
        self.assertEqual(self.run_check()['assessment'],'NO_OBSERVED_FAILURE')

    def test_offline_osd_is_valid_but_incomplete(self):
        self.data['samples'][1]['identity_line']=self.data['samples'][1]['identity_line'].replace('S','!',1)
        self.assertEqual(self.run_check()['assessment'],'INCOMPLETE')

    def test_wrong_bit_is_failure(self):
        self.data['version']['bit_sha256']='0'*64
        self.assertEqual(self.run_check()['assessment'],'OBSERVED_FAILURE')

    def test_conflicting_manual_counter_rejected(self):
        self.data['samples'][1]['counters']['duplicate']=1
        with self.assertRaisesRegex(ValueError,'conflicting'):self.run_check()

    def test_bool_counter_rejected(self):
        self.data['samples'][1]['counters']['fifo_steady']=True
        with self.assertRaisesRegex(ValueError,'uint16'):self.run_check()

    def test_bad_hex_rejected(self):
        self.data['samples'][1]['reason_line']=self.data['samples'][1]['reason_line'].replace('D0000','D00O0')
        with self.assertRaisesRegex(ValueError,'does not match'):self.run_check()

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            board.load_record('{"samples": [], "samples": [1]}')

    def test_non_json_number_rejected(self):
        with self.assertRaisesRegex(ValueError,'Non-JSON'):
            board.load_record('{"t_s": NaN}')

    def test_cli_missing_data_and_invalid_structure_exit_codes(self):
        wrong_version=copy.deepcopy(self.data);wrong_version['version']=[]
        for n,data,expected in [('template',board.template(),2),('invalid',[],3),('version',wrong_version,3)]:
            p=self.base/(n+'.json');p.write_text(json.dumps(data))
            r=subprocess.run([sys.executable,'-B',str(TOOL),str(p),'--out',str(self.base/(n+'-result.json'))],capture_output=True,text=True)
            self.assertEqual(r.returncode,expected,r.stderr)
            self.assertEqual(json.loads((self.base/(n+'-result.json')).read_text())['board_acceptance'],'NOT_CERTIFIED')


if __name__=='__main__':unittest.main()
