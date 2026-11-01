"""Frozen physical interfaces, exact teammate blobs and declaration-only compatibility."""
from pathlib import Path
import subprocess,json,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
BASE='43ff61b4f1791782e74100c92b9612317e0d2249'
HDL='in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/'
def old(rel):return subprocess.check_output(['git','show',BASE+':'+rel],cwd=ROOT).decode().replace('\r\n','\n')
def main():
    from build_vision_track_motion_v1 import snapshot
    snap=snapshot();proof={}
    # These two frozen algorithms only move one declaration; removing that
    # exact line from both versions must leave identical source bytes.
    for name,marker in [('isp/edge_detect_96.v','wire [13:0] low_threshold='),('isp/color_compare_osd.v','wire [1:0] comparison_status=')]:
        rel=HDL+name;a=old(rel);b=(ROOT/rel).read_text()
        la=[s for s in a.splitlines(True) if marker in s];lb=[s for s in b.splitlines(True) if marker in s]
        assert len(la)==len(lb)==1 and la==lb
        assert a.replace(la[0],'')==b.replace(lb[0],'');proof[rel]='Only exact declaration relocation'
    for directory in ('user_source/ip_source/','user_source/constraints_source/'):
        prefix=HDL.replace('user_source/hdl_source/',directory)
        assert not subprocess.check_output(['git','diff',BASE,'--',prefix],cwd=ROOT)
    for name in ('video_in.v','video_out.v','osd_char_lib.v','isp/style_fill_96.v','isp/edge_temporal_hold.v','isp/awb.v'):
        rel=HDL+name
        if (ROOT/rel).exists():assert (ROOT/rel).read_text()==old(rel);proof[rel]='Exact baseline content'
    for item in json.loads((ROOT/'docs/evidence/VISION_TRACK_MOTION_V1/TARGET_SOURCE.json').read_text())['files']:
        content=(ROOT/item['path']).read_bytes();blob=subprocess.check_output(['git','hash-object','--stdin'],input=content,cwd=ROOT).decode().strip()
        assert blob==item['git_blob'];proof[item['path']]='Exact immutable teammate git blob'
    sdc=Path(HDL).parents[1]/'td_project/camera_to_dsi_display.sdc'
    assert (ROOT/sdc).read_text()==old(sdc.as_posix())
    top=(ROOT/(HDL+'design_top_wrapper.v')).read_text()
    for literal in ("assign S_ae_req = 1'b0", "assign S_ae = 16'd1990"):
        # Whitespace independent check; no Sensor parameter adjustment.
        assert re.sub(r'\s+','',literal) in re.sub(r'\s+','',top),literal
    out=ROOT/'tmp/vision_track_motion/SCOPE.json'
    out.write_text(json.dumps(dict(passed=True,baseline=BASE,files=proof,source_commit=snap['source_commit'],td_input_count=len(snap['files'])),indent=2)+'\n')
    print('PASS frozen physical interfaces, exact teammate files, two declaration-only moves; TD inputs',len(snap['files']))
if __name__=='__main__':main()
