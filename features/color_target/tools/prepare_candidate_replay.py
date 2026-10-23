"""Bind existing detector replay to MAIN 5cbb1de; never invent guard timing.

Preflight only. The supplied images must explicitly declare the color tap.
The printed argv runs the existing detector replay; its legacy track columns
do not verify the integrated guard, CDC, DDR or final display commit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from model.replay_data import load_manifest

REVISION='5cbb1de3814a842067ee1ffd41df3d75bbf0de26'
PARAMETERS=dict(target_class=0,hue_half_width_deg=30,c_min=24,v_min=32,min_count=64,filter_enable=False)


def bind_replay_rtl(source, expected, local_dir=None):
    prefix='features/color_target/rtl/'
    names={k[len(prefix):] for k in expected if k.startswith(prefix) and k.endswith('.v')}
    pinned_dir=source/prefix
    local_dir=local_dir or HERE/'rtl'
    if not names or names!={p.name for p in pinned_dir.glob('*.v')} or names!={p.name for p in local_dir.glob('*.v')}:
        raise ValueError('Replay RTL file set differs from pinned manifest')
    binding={}
    for name in sorted(names):
        pinned=(pinned_dir/name).read_bytes();raw=(local_dir/name).read_bytes()
        digest=hashlib.sha256(pinned).hexdigest()
        if digest!=expected[prefix+name]:
            raise ValueError('Pinned replay RTL hash mismatch: '+name)
        if raw==pinned:
            representation='raw'
        elif b'\n' not in raw.replace(b'\r\n',b'') and raw.replace(b'\r\n',b'\n')==pinned:
            representation='uniform_CRLF_to_LF'
        else:
            raise ValueError('Local replay RTL differs from pinned candidate: '+name)
        binding[name]=dict(raw_sha256=hashlib.sha256(raw).hexdigest(),pinned_sha256=digest,representation=representation)
    return binding


def dataset_preflight(path):
    data=load_manifest(path)
    counts={};unknown=0
    for clip in data['clips']:
        if (clip['width'],clip['height'])!=(1280,720):
            raise ValueError('Integrated candidate requires 1280x720; do not silently resize annotations')
        if clip.get('pixel_tap')!='post_awb_pre_style_rgb888':
            raise ValueError('Declare pixel_tap=post_awb_pre_style_rgb888; HDMI OSD/STYLE or Bayer data is not this tap')
        key=clip['source_kind']+'/'+clip['split']
        counts[key]=counts.get(key,0)+len(clip['frames'])
        unknown+=sum(f.get('annotation') is None for f in clip['frames'])
    return dict(groups_by_source_and_split=counts,unannotated_frames=unknown,
                camera_material_declared=any(c['source_kind']=='camera' for c in data['clips']),
                input_tap_provenance='User declaration; not independently certified by the manifest')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--snapshot-manifest',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    bound=json.loads(a.snapshot_manifest.read_text(encoding='utf-8'))
    if bound['commit']!=REVISION:raise ValueError('Unsupported MAIN revision; reassess profile on revision change')
    expected={r['path']:r['sha256'] for r in bound['files']}
    prefix='in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/target/'
    files=['features/color_target/rtl/color_target_detect_stream.v',
           'features/color_target/rtl/color_target_track_guard.v',
           prefix+'target_frame_system.v',prefix+'frame_timebase.v',prefix+'target_display_commit.v']
    hashes={}
    for rel in files:
        digest=hashlib.sha256((a.source/rel).read_bytes()).hexdigest()
        if digest!=expected[rel]:raise ValueError('Pinned source changed: '+rel)
        hashes[rel]=digest
    local_binding=bind_replay_rtl(a.source,expected)
    dataset=dataset_preflight(a.manifest)
    argv=[sys.executable,'-B','-X','utf8',str(HERE/'run_color_target_replay.py'),
          '--manifest',str(a.manifest.resolve()),'--out',str((a.out/'detector-only').resolve()),
          '--mode','bypass','--min-count','64']
    result=dict(candidate_commit=REVISION,source_sha256=hashes,local_replay_rtl_binding=local_binding,
        replay_runner_sha256=hashlib.sha256((HERE/'run_color_target_replay.py').read_bytes()).hexdigest(),classifier_parameters=PARAMETERS,
        guard_configuration=dict(time_w=64,counter_w=16,acq_frames=3,lost_frames=15,
                                 max_target_age_ticks=100000,max_reliable_age_ticks=100000,
                                 tick_hz_nominal=1000000,max_scan_ticks=16501),
        dataset=dataset,detector_replay_argv=argv,preflight_passed=True,replay_executed=False,
        integrated_guard_temporal_replay_verified=False,
        scope='Input/source/configuration preflight only; existing replay uses legacy track. Add explicit trusted time/control/result/display events before guard acceptance; no assumed frame rate or derived capture timestamps.')
    (a.out/'profile.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
