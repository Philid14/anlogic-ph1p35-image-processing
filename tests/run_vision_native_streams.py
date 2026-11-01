"""Full production ISP regression with REAL vendor ERAM, native ModelSim.

Reuses independent pixel/packer vectors, never the Icarus test RAM contract.
Only post-AWB sensor output and synchronized inspection controls are boundaries.
"""
import argparse,json,hashlib
from run_vision_legacy import sources
from vision_sim import ROOT,simulate
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--case',choices=['legacy','features'],required=True);a=ap.parse_args()
    case=a.case;name='legacy' if case=='legacy' else 'feature'
    vectors=ROOT/'tmp/vision_track_motion'/case;out=vectors/'native';out.mkdir(exist_ok=True)
    beats,words,frames=(2073600,1555200,9) if case=='legacy' else (1843200,1382400,8)
    top='tb_vision_'+name+'_stream';src=[ROOT/'tests'/(top+'.sv')]+[p for p in sources() if p.name!='vision_eram_contract.v']
    print('Native stream starting',case,beats,flush=True)
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}
    log=simulate(out,top,src,parameters=['-g'+x for x in ('WIDTH=1280','HEIGHT=720','COMPARE=1','INSPECTION=1','AUTO_DIMENSION=1','USABILITY_ENABLE=1','INSPECTION_V4=1')],plus=[f'+STIM={(vectors/"stim.txt").as_posix()}',f'+PACK={(vectors/"pack.txt").as_posix()}',f'+WORDS={words}'],eram=True,timeout=900)
    assert hashes=={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}
    (out/'console.txt').write_text(log)
    (out/'results.json').write_text(json.dumps(dict(passed=True,beats=beats,words=words,frames=frames,sources=hashes,vendor_memory='Actual local PH1P_LOGIC_ERAM/GSR; see SIM_SOURCE_MANIFEST.json',vectors={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (vectors/'stim.txt',vectors/'pack.txt')}),indent=2)+'\n')
    print(log[-800:])
if __name__=='__main__':main()
