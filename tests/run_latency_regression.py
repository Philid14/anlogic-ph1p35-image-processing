"""Re-use immutable old reference vectors without overwriting old evidence."""
import importlib,sys,os
from vision_sim import ROOT,HDL,simulate as native_simulate
CASES={c:'run_inspection_'+c for c in ('font','shape','drawing','track','config','reset','select','contract','legacy','integrated','track_stream')}
CASES['background_full']='run_measure_background_full'

def simulate(out,top,sources,**kwargs):
    files=list(sources)
    if any(p.name in ('inspection_config_delay.v','edge_control_stream.v') for p in files):
        helper=HDL/'vision/inspection_payload_delay.v'
        if helper not in files:files.append(helper)
    if any(p.name in ('gaussian_pair_3x3.v','nms_gradient_pair_3x3.v') for p in files):
        helper=HDL/'vision/edge_row_history.v'
        if helper not in files:files.append(helper)
    if os.environ.get('LATENCY_STAGING')=='1':
        def staged(p):
            if p.is_relative_to(HDL):
                candidate=ROOT/os.environ.get('LATENCY_STAGE_ROOT','tmp/latency_performance/staging')/p.relative_to(HDL)
                if candidate.exists():return candidate
            return p
        files=[staged(p) for p in files]
    return native_simulate(out,top,files,**kwargs)

def main():
    for case in sys.argv[1:]:
        module=importlib.import_module(CASES[case])
        module.OUT=ROOT/os.environ.get('LATENCY_REGRESSION_OUT','tmp/latency_performance/regression')/case
        if hasattr(module,'simulate'):module.simulate=simulate
        module.main()
if __name__=='__main__':main()
