import json,os
from vision_sim import ROOT,HDL,simulate
import run_edge_nms_v1 as nms
import run_edge_denoise_v1 as gaussian
OUT=ROOT/os.environ.get('LATENCY_ROWS_OUT','tmp/latency_performance/rows')
def main():
    counts={}
    for name,model,top,rtl in [('gaussian',gaussian.gaussian_vectors,'tb_gaussian_pair','gaussian_pair_3x3.v'),
                               ('nms',nms.unit_vectors,'tb_nms_gradient_pair','nms_gradient_pair_3x3.v')]:
        folder=OUT/name;folder.mkdir(parents=True,exist_ok=True);stim,beats=model(folder)
        source=HDL/'isp'/rtl
        helper=HDL/'vision/edge_row_history.v'
        if os.environ.get('LATENCY_STAGING')=='1':
            stage=ROOT/os.environ.get('LATENCY_STAGE_ROOT','tmp/latency_performance/staging')
            source=stage/'isp'/rtl
            if (stage/'vision/edge_row_history.v').exists():helper=stage/'vision/edge_row_history.v'
        log=simulate(folder,top,[ROOT/'tests'/(top+'.v'),source,helper],
                     plus=['+STIM='+stim.as_posix()],eram=True)
        assert 'PASS ' in log
        (folder/'console.txt').write_text(log);counts[name]=beats
        print(name,'PASS native rows against old independent model',beats,flush=True)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,beats=counts,native=True),indent=2)+'\n')
if __name__=='__main__':main()
