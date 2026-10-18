"""Controlled counterexamples only; does not select a real-camera algorithm."""
import json
from pathlib import Path
import numpy as np
from temporal_roi_analysis import proposals,metrics,analyze
from run_edge_temporal_research import capture_expected

def main():
    e=np.zeros((8,24,32),bool)
    for f in range(8):e[f,8:16,8+f]=1
    a=proposals(e,np.full(e.shape,100),80)
    assert not a['majority3'][2:].any(), 'moving thin line majority counterexample'
    assert a['one_frame_gradient_support'][1:].sum()==2*e[1:].sum(), 'one-frame persistence doubles moving width'
    roi=np.ones(e.shape[1:],bool)
    measured={k:metrics(v,roi,e) for k,v in a.items()}
    pre=capture_expected(1280,720,128,32,576,344,8)
    meta=np.zeros((8,16),np.uint32);meta[:,1:3]=65536
    r=analyze(pre,pre,meta,80)
    assert r['ground_truth_available'] is False
    assert r['candidates']['current']['contour_recall'] is None
    assert r['causal_contribution_percentages'] is None
    result=dict(moving_line_counterexample=measured,software_pipeline_validated=True,real_camera_data=False,selected_algorithm=None)
    out=Path(__file__).resolve().parents[1]/'docs/edge_temporal_evidence';out.mkdir(exist_ok=True)
    (out/'research_tool_tests.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS temporal metrics: moving-line loss/width counterexamples; unlabeled completeness stays unmeasured')

if __name__=='__main__':main()
