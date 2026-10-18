"""Capture/AWB/packet/optical gates; optional full720p and historical regression."""
from pathlib import Path
import argparse,subprocess,tempfile,sys,json
import numpy as np
from run_edge_control_v1 import ROOT,HDL,simulate
import temporal_transport as transport

BASE='7343cfeb1de049e0793e63524cae071e9ae5018a'
OUT=ROOT/'docs/edge_temporal_evidence'

def frozen():
    allowed={'design_top_wrapper.v','awb.v','edge_status_osd.v','isp/isp_top.v','isp/edge_control_stream.v'}
    count=0
    for n in subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'in_out_example','edge_example','artifacts/bitstreams','features'],text=True).splitlines():
        p=ROOT/n
        if p.is_relative_to(HDL) and p.relative_to(HDL).as_posix() in allowed:continue
        if n.endswith('td_project/camera_to_dsi_display.al'):continue
        b=subprocess.check_output(['git','show',BASE+':'+n])
        assert p.read_bytes().replace(b'\r\n',b'\n')==b.replace(b'\r\n',b'\n'),n
        count+=1
    print('PASS frozen temporal baseline',count,'including 17 old bits, algorithms, sensor, SDC, teammates',flush=True)
    return count

def capture_expected(w,h,rw,rh,rx,ry,n):
    f,y,x=np.indices((n,rh,rw));f=f+1;y=y+ry;beat=(x+rx)//4;lane=(x+rx)%4
    return np.stack(((f*13+y*3+beat*4+lane)%256,(f*7+y+beat*8+lane*2)%256,(f*11+y*2+beat*3+lane)%256),-1).astype(np.uint8)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--full',action='store_true');ap.add_argument('--regression',action='store_true');a=ap.parse_args();OUT.mkdir(exist_ok=True)
    frozen();summary={};logs=[]
    with tempfile.TemporaryDirectory(prefix='temporal-') as td:
        d=Path(td)
        old=subprocess.check_output(['git','show',BASE+':'+(HDL/'awb.v').relative_to(ROOT).as_posix()],text=True)
        original=d/'awb_baseline.v';original.write_text(old.replace('module awb #','module awb_baseline #'),encoding='utf8')
        logs.append(simulate(d,'tb_awb_diag',[ROOT/'tests/tb_awb_diag.v',HDL/'awb.v',original,HDL/'signal_delay.v',ROOT/'tests/tb_awb_stability.v']))
        old_osd=subprocess.check_output(['git','show',BASE+':'+(HDL/'edge_status_osd.v').relative_to(ROOT).as_posix()],text=True)
        osd=d/'edge_status_osd_baseline.v';osd.write_text(old_osd.replace('module edge_status_osd #','module edge_status_osd_baseline #'))
        logs.append(simulate(d,'tb_temporal_osd',[ROOT/'tests/tb_temporal_osd.v',HDL/'edge_status_osd.v',osd,HDL/'osd_char_lib.v']))
        cases=[(64,32,16,8,16,12,2)]
        if a.full:cases.append((1280,720,128,32,576,344,8))
        for w,h,rw,rh,rx,ry,n in cases:
            target=d/f'capture_{w}.txt'
            opts=[f'-Ptb_temporal_capture.{key}={val}' for key,val in zip(('W','H','RW','RH','RX','RY','N'),(w,h,rw,rh,rx,ry,n))]
            logs.append(simulate(d,'tb_temporal_capture',[ROOT/'tests/tb_temporal_capture.v',HDL/'isp/temporal_roi_capture.v',HDL/'data_96bit_to_128bit.v'],opts,[f'+OUT={target.as_posix()}']))
            words=np.array([int(x,16) for x in target.read_text().splitlines()],np.uint32)
            pre,post,meta,g=transport.unpack_capture(words)
            assert np.array_equal(pre,capture_expected(w,h,rw,rh,rx,ry,n))
            assert np.array_equal(transport.assemble(transport.encode(words,int(g[15]))),words)
            summary[str(w)]=dict(frames=n,roi=[rw,rh],words=len(words),pre_gain_post_crc=True,consecutive=True)
            # Reject quantity and intra-ROI gain faults instead of ranking data.
            bad=words.copy();bad[n*rw*rh//4*3+10]^=1
            try:transport.unpack_capture(bad)
            except ValueError:pass
            else:raise AssertionError('bad flow accepted')
        target=d/'packet.txt'
        logs.append(simulate(d,'tb_temporal_packet',[ROOT/'tests/tb_temporal_packet.v',HDL/'isp/temporal_packet.v'],plus=[f'+OUT={target.as_posix()}']))
        expected=transport.encode(np.array([0x12345678^(i*0x01020305 & 0xffffffff) for i in range(527)],np.uint32),0x76543210)
        actual=np.array([int(x,16) for x in target.read_text().splitlines()],dtype='>u4').reshape(5,256)
        assert all(actual[i].tobytes()==expected[i%3] for i in range(5))
    (OUT/('rtl_full.json' if a.full else 'rtl_small.json')).write_text(json.dumps(dict(summary=summary,logs=logs),indent=2)+'\n')
    if a.regression:
        import run_edge_stability_probe as probe
        probe.frozen=frozen;probe.OUT=ROOT/'tmp/temporal_probe_regression';probe.OUT.mkdir(exist_ok=True)
        sys.argv=['probe']+(['--full'] if a.full else []);probe.main()
        import run_probe_regression as regression
        regression.frozen=frozen;regression.main()
    frozen();print('PASS temporal research RTL and independent transport gates',flush=True)

if __name__=='__main__':main()
