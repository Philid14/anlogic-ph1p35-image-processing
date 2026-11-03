import json,hashlib
from vision_sim import ROOT,simulate
from run_vision_legacy import sources
import ruler_cm_stream_vectors as vectors
from vision_sim import HDL
OUT=ROOT/'tmp/inspection_shape_track/legacy'
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    from inspection_vectors import baseline
    stim,pack=baseline();words=1555200;beats=2073600;print('CM full ISP vectors ready',beats,words,flush=True)
    top='tb_inspection_legacy_stream';src=[ROOT/'tests'/(top+'.sv')]+[p for p in sources() if p.name!='vision_eram_contract.v']+[HDL/'vision/inspection_font_rom.v',HDL/'vision/measure_background.v',HDL/'vision/inspection_config_delay.v',HDL/'vision/inspection_shape_select.v']
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}
    log=simulate(OUT,top,src,parameters=['-g'+v for v in ('WIDTH=1280','HEIGHT=720','COMPARE=1','INSPECTION=1','AUTO_DIMENSION=1','USABILITY_ENABLE=1','INSPECTION_V4=1')],plus=[f'+STIM={stim.as_posix()}',f'+PACK={pack.as_posix()}',f'+WORDS={words}'],eram=True,timeout=900)
    assert hashes=={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}
    (OUT/'console.txt').write_text(log);(OUT/'results.json').write_text(json.dumps(dict(passed=True,frames=9,beats=beats,words=words,sources=hashes,boundary='Post-AWB/synchronized UI; only ruler search height12, full production288 search separately tested'),indent=2)+'\n');print(log[-800:])
if __name__=='__main__':main()
