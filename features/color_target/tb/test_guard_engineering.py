"""Independent rejection witnesses for new resource/configuration tooling."""
import importlib.util
import json
from pathlib import Path
import unittest
import tempfile

HERE=Path(__file__).resolve().parents[1]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


synth=module('guard_measurement',HERE/'run_guard_synthesis.py')
config=module('target_preflight',HERE/'tools/check_target_config.py')


class ConfigWitnesses(unittest.TestCase):
    def valid(self):
        result=json.loads((HERE/'integration/TARGET_CONFIG_PENDING.json').read_text())
        result.update(max_target_age_ticks=1000003,max_reliable_age_ticks=2000003,
            tick_hz=100000000,max_capture_to_display_start_ticks=100,max_scan_ticks=200)
        return result

    def test_pending_is_unknown(self):
        pending=json.loads((HERE/'integration/TARGET_CONFIG_PENDING.json').read_text())
        self.assertEqual(config.evaluate(pending)['configuration_status'],'UNKNOWN')

    def test_valid_declaration_never_proves_integration(self):
        got=config.evaluate(self.valid())
        self.assertEqual(got['configuration_status'],'PASS')
        self.assertFalse(got['integration_verified'])
        self.assertFalse(got['elaborated_parameters_verified'])

    def test_zero_negative_overflow_and_wrong_types_rejected(self):
        for field in ('max_target_age_ticks','max_reliable_age_ticks'):
            for value in (0,-1,1<<64,True,1.0,'123'):
                with self.subTest(field=field,value=value):
                    candidate=self.valid();candidate[field]=value
                    self.assertEqual(config.evaluate(candidate)['configuration_status'],'FAIL')

    def test_largest_unsigned_age_accepted(self):
        candidate=self.valid();candidate.update(max_target_age_ticks=(1<<64)-1,
                                               max_reliable_age_ticks=(1<<64)-1)
        self.assertEqual(config.evaluate(candidate)['configuration_status'],'PASS')

    def test_wrong_lanes_filter_width_and_clamped_counts_rejected(self):
        for field,value in [('lane_order','LSB_FIRST'),('filter_enable',True),
                ('filter_enable',0),('width',1279),('ppc',1),('time_w',32),
                ('acq_frames',0),('lost_frames',256),('tick_hz',True)]:
            with self.subTest(field=field):
                candidate=self.valid();candidate[field]=value
                self.assertEqual(config.evaluate(candidate)['configuration_status'],'FAIL')

    def test_budget_overflow_warns_hide_without_changing_limits(self):
        candidate=self.valid();candidate.update(max_scan_ticks=(1<<64)-1)
        got=config.evaluate(candidate)
        self.assertEqual(got['configuration_status'],'PASS')
        self.assertFalse(got['declared_budget']['fits_both_limits'])
        self.assertTrue(any(c['status']=='WARN' for c in got['checks']))
        self.assertEqual(candidate['max_target_age_ticks'],1000003)

    def test_unknown_key_rejected(self):
        candidate=self.valid();candidate['max_target_age_tick']=123
        self.assertEqual(config.evaluate(candidate)['configuration_status'],'FAIL')

    def test_duplicate_key_and_non_json_number_rejected(self):
        for raw in (b'{"max_target_age_ticks":0,"max_target_age_ticks":123}',
                    b'{"tick_hz":NaN}'):
            with self.assertRaises(ValueError):config.load_config(raw)

    def test_modified_rtl_cannot_match_delivery(self):
        repo=HERE.parents[1]
        manifest=json.loads((HERE/'board/TARGET_DELIVERY.json').read_text())
        with tempfile.TemporaryDirectory(prefix='guard_binding_') as tmp:
            root=Path(tmp)
            for row in manifest['files']:
                dest=root/row['path'];dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes((repo/row['path']).read_bytes())
            self.assertTrue(config.source_binding(root)['matched'])
            changed=root/manifest['files'][-1]['path']
            changed.write_bytes(changed.read_bytes()+b'\n// changed witness\n')
            result=config.source_binding(root)
            self.assertFalse(result['matched'])
            self.assertEqual(sum(r['matched'] for r in result['files']),8)


class SynthesisWitnesses(unittest.TestCase):
    LOG='GUARD_SYNTH_COMPLETE time_w=64 enabled=1\n'
    AREA='''#lut 1132
#reg 1471
#eram 0
#dsp 0
#slice* 1113
|top|guard_synth_top|586|341|1471|0|0|0|0|0|0|0|0|
|u_guard|color_target_track_guard|244|341|581|0|0|0|0|0|0|0|0|
|u_track|color_target_track|53|0|101|0|0|0|0|0|0|0|0|
'''
    TIMING='SWNS: 1.494ns, STNS: 0.000ns.\nHWNS: 0.502ns, HTNS: 0.000ns.\n'
    SUMMARY='STA coverage : 73.51%\nBegin Point : source\nEnd Point : endpoint\nLogic Level : 8\n'

    def parse(self,**kw):
        args=dict(log=self.LOG,area=self.AREA,timing=self.TIMING,
                  summary=self.SUMMARY,tw=64,enabled=1);args.update(kw)
        return synth.parse_reports(**args)

    def test_complete_report_parses_native_hierarchy_units(self):
        got=self.parse();self.assertEqual(got['top_level']['lut'],1132)
        self.assertEqual(got['hierarchy'][1]['seq'],581)

    def test_disabled_slice_spelling_is_accepted(self):
        self.parse(area=self.AREA.replace('#slice*','#slice'))

    def test_missing_duplicate_or_wrong_completion_rejected(self):
        for value in ('',self.LOG*2,self.LOG.replace('64','32'),self.LOG+'ERROR bad\n'):
            with self.subTest(log=value),self.assertRaises(ValueError):self.parse(log=value)

    def test_optimized_away_track_rejected_for_active_configuration(self):
        for value in (self.AREA.replace('|u_track|color_target_track|53|0|101|0|0|0|0|0|0|0|0|',''),
                      self.AREA.replace('track|53|0|101|','track|53|0|0|')):
            with self.assertRaises(ValueError):self.parse(area=value)

    def test_missing_timing_and_duplicate_area_rejected(self):
        for kw in (dict(timing=''),dict(area=self.AREA+'#lut 1\n'),dict(summary='')):
            with self.assertRaises(ValueError):self.parse(**kw)

    def test_negative_slack_is_evidence_not_timing_pass(self):
        got=self.parse(timing=self.TIMING.replace('1.494','-1.494'))
        self.assertFalse(got['experimental_gate_timing_met'])


if __name__=='__main__':unittest.main(verbosity=2)
