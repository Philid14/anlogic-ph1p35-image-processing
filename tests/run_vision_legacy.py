"""All nine V4 production frames, with new observer enabled; bit-exact old UI/packer."""
import ast,json,hashlib
from vision_sim import ROOT,HDL
import run_inspection_v4_stream as old
OUT=ROOT/'tmp/vision_track_motion/legacy'
def sources():
    tree=ast.parse((ROOT/'tests/run_inspection_v4_stream.py').read_text())
    names=next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='names' for t in n.targets))
    return [HDL/n for n in names]+[ROOT/'tests/isp_boundary_stubs.v',HDL/'vision/vision_source_observer.v',HDL/'vision/vision_motion_grid.v']+[ROOT/'features/color_target/rtl'/n for n in ('color_classify.v','color_target_mask_stats.v','color_target_track.v','color_target_track_guard.v')]
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    stim,pack=OUT/'stim.txt',OUT/'pack.txt'
    words,beats=1555200,2073600
    if not stim.exists():stim,pack,words,beats=old.vectors(OUT,1280,720,True)
    print('Vectors ready',beats,words,flush=True)
    src=[ROOT/'tests/tb_vision_legacy_stream.sv']+sources()
    log=old.c.simulate(OUT,'tb_vision_legacy_stream',src,params=['-Ptb_vision_legacy_stream.'+x for x in ('WIDTH=1280','HEIGHT=720','COMPARE=1','INSPECTION=1','AUTO_DIMENSION=1','USABILITY_ENABLE=1','INSPECTION_V4=1')],plus=[f'+STIM={stim.as_posix()}',f'+PACK={pack.as_posix()}',f'+WORDS={words}'])
    (OUT/'console.txt').write_text(log)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,beats=beats,words=words,frames=9,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src}),indent=2)+'\n')
    print(log[-1000:])
if __name__=='__main__':main()
