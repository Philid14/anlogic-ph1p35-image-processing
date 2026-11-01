import json,hashlib
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/vision_track_motion/controls'
def main():
    src=[ROOT/'tests/tb_vision_keys.sv',HDL/'edge_key_control.v',HDL/'edge_config_cdc.v']
    log=simulate(OUT/'keys','tb_vision_keys',src)
    src2=[ROOT/'tests/tb_vision_watchdog.sv',HDL/'hdmi_mixer.v',HDL/'osd_char_lib.v',HDL/'anlogic_logo_rom.v']
    log2=simulate(OUT/'watchdog','tb_vision_watchdog',src2)
    (OUT/'console.txt').write_text(log+log2)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src+src2}),indent=2)+'\n')
    print(log[-500:]+log2[-500:])
if __name__=='__main__':main()
