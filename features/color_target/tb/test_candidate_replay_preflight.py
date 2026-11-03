"""Input contracts for the current candidate, with synthetic RGB fixtures."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

TOOL=Path(__file__).resolve().parents[1]/'tools/prepare_candidate_replay.py'
spec=importlib.util.spec_from_file_location('candidate_replay',TOOL)
replay=importlib.util.module_from_spec(spec);spec.loader.exec_module(replay)


class ReplayPreflight(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='target_replay_profile_');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        (self.base/'frame.ppm').write_bytes(b'P6\n1280 720\n255\n'+bytes(1280*720*3))
        self.data=dict(schema=1,clips=[dict(clip_id='synthetic',group_id='synthetic-group',split='validation',
            source_kind='synthetic',pixel_tap='post_awb_pre_style_rgb888',width=1280,height=720,
            frames=[dict(path='frame.ppm',session=1,frame=0,annotation=None)])])
    def evaluate(self):
        p=self.base/'manifest.json';p.write_text(json.dumps(self.data));return replay.dataset_preflight(p)
    def test_unannotated_is_unknown_not_absence(self):
        r=self.evaluate();self.assertEqual(r['unannotated_frames'],1);self.assertFalse(r['camera_material_declared'])
    def test_wrong_tap_rejected(self):
        self.data['clips'][0]['pixel_tap']='hdmi_with_osd'
        with self.assertRaisesRegex(ValueError,'pixel_tap'):self.evaluate()
    def test_geometry_not_silently_scaled(self):
        c=self.data['clips'][0];c['width']=640;c['height']=360
        (self.base/'frame.ppm').write_bytes(b'P6\n640 360\n255\n'+bytes(640*360*3))
        with self.assertRaisesRegex(ValueError,'1280x720'):self.evaluate()
    def test_tampered_pinned_classifier_rejected_even_if_local_matches(self):
        pinned=self.base/'features/color_target/rtl';pinned.mkdir(parents=True)
        local=self.base/'local';local.mkdir()
        (pinned/'classifier.v').write_bytes(b'tampered\n');(local/'classifier.v').write_bytes(b'tampered\n')
        expected={'features/color_target/rtl/classifier.v':hashlib.sha256(b'trusted\n').hexdigest()}
        with self.assertRaisesRegex(ValueError,'hash mismatch'):replay.bind_replay_rtl(self.base,expected,local)
    def test_missing_pinned_classifier_rejected(self):
        local=self.base/'local';local.mkdir();(local/'classifier.v').write_bytes(b'trusted\n')
        expected={'features/color_target/rtl/classifier.v':hashlib.sha256(b'trusted\n').hexdigest()}
        with self.assertRaisesRegex(ValueError,'file set'):replay.bind_replay_rtl(self.base,expected,local)
if __name__=='__main__':unittest.main()
