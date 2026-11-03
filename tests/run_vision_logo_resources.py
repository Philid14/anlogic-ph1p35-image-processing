import json,subprocess
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/vision_track_motion/resource_logo'
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    p=HDL/'hdmi_mixer.v';rel=p.relative_to(ROOT).as_posix()
    old=subprocess.check_output(['git','show','43ff61b4:'+rel])
    ref=OUT/'reference_mixer.v';ref.write_bytes(old.replace(b'module hdmi_mixer #(',b'module reference_mixer #(',1))
    log=simulate(OUT,'tb_vision_logo_resources',[ROOT/'tests/tb_vision_logo_resources.sv',ref,p,
       HDL/'osd_char_lib.v',HDL/'anlogic_logo_rom.v',HDL/'vision/vision_logo_palette.v'],eram=True)
    assert 'PASS mixer cycle equivalence' in log
    (OUT/'console.txt').write_text(log)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,baseline='43ff61b4',rom_addresses=32768,
      frames=2,scope='Actual vendor ERAM/GSR; all mixer RGB/control cycles including reset and blanking; no latency change'),indent=2)+'\n')
    print(log[-600:])
if __name__=='__main__':main()
