"""Re-use immutable old reference vectors without overwriting old evidence."""
import importlib,sys,os
from vision_sim import ROOT,HDL,simulate as native_simulate
CASES={c:'run_inspection_'+c for c in ('font','shape','drawing','track','config','reset','select','contract','legacy','integrated','track_stream')}
CASES['background_full']='run_measure_background_full'

def simulate(out,top,sources,**kwargs):
    files=list(sources)
    # These legacy ISP tests deliberately stub the AWB boundary; arithmetic
    # equivalence is verified separately against the actual native IP/RAM.
    # Accept the new implementation-only parameter without changing the
    # immutable old stub or the independent expected pixel vectors.
    if any(p.name=='isp_top.v' for p in files):
        for index,p in enumerate(files):
            if p.name=='isp_boundary_stubs.v':
                original=p.read_text();needle='module awb #(parameter IMG_HEIGHT=720, IMG_WIDTH=1280)'
                assert needle in original
                out.mkdir(parents=True,exist_ok=True)
                compat=out/'awb_interface_compat.v'
                compat.write_text(original.replace(needle,needle[:-1]+', FRAME_SERIAL_DIV=0)',1))
                files[index]=compat
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
