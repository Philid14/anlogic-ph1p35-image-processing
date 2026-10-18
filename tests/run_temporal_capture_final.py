"""Focused final capture/timestamp test; synthetic input, actual 720p counts."""
from pathlib import Path
import tempfile,json,hashlib
import numpy as np
from run_edge_control_v1 import ROOT,HDL,simulate
from run_edge_temporal_research import capture_expected
import temporal_transport as t

def main():
    target=ROOT/'tmp/temporal_capture_final_words.txt'
    with tempfile.TemporaryDirectory(prefix='temporal-final-capture-') as tmp:
        opts=[f'-Ptb_temporal_capture.{k}={v}' for k,v in zip(('W','H','RW','RH','RX','RY','N'),(1280,720,128,32,576,344,8))]
        log=simulate(Path(tmp),'tb_temporal_capture',[ROOT/'tests/tb_temporal_capture.v',HDL/'isp/temporal_roi_capture.v',HDL/'data_96bit_to_128bit.v'],opts,[f'+OUT={target.as_posix()}'])
    words=np.array([int(x,16) for x in target.read_text().splitlines()],np.uint32)
    pre,post,meta,g=t.unpack_capture(words)
    assert np.array_equal(pre,capture_expected(1280,720,128,32,576,344,8))
    intervals=np.diff(meta[:,15].astype(np.int64))
    expected=1+64+720*(1280//4+8)+100 # testbench SOF + idle + rows + end gap
    assert np.all(intervals==expected),(intervals,expected)
    result=dict(log=log,frames=8,roi=[128,32],words=len(words),capture_id=f'{int(g[15]):08X}',sof_intervals=intervals.tolist(),pre_gain_post_crc=True,raw_word_sha256=hashlib.sha256(t.words_bytes(words)).hexdigest(),real_sensor=False)
    out=ROOT/'docs/edge_temporal_evidence';out.mkdir(exist_ok=True)
    (out/'rtl_capture_final.json').write_text(json.dumps(result,indent=2)+'\n')
    np.savez_compressed(ROOT/'tmp/temporal_synthetic_capture.npz',pre=pre,post=post,meta=meta,global_header=g)
    print('PASS final timestamped capture and independent reconstruction')

if __name__=='__main__':main()
