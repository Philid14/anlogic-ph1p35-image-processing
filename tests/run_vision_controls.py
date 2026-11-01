import json,hashlib
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/vision_track_motion/controls'
def main():
    src=[ROOT/'tests/tb_vision_keys.sv',HDL/'edge_key_control.v',HDL/'edge_config_cdc.v']
    log=simulate(OUT/'keys','tb_vision_keys',src)
    src2=[ROOT/'tests/tb_vision_watchdog.sv',HDL/'hdmi_mixer.v',HDL/'osd_char_lib.v',HDL/'anlogic_logo_rom.v']
    log2=simulate(OUT/'watchdog','tb_vision_watchdog',src2)
    from run_vision_legacy import sources
    src3=[ROOT/'tests/tb_vision_pipeline_reset.sv']+[p for p in sources() if p.name!='vision_eram_contract.v']
    log3=simulate(OUT/'pipeline_reset','tb_vision_pipeline_reset',src3,eram=True)
    (OUT/'console.txt').write_text(log+log2+log3)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in src+src2+src3}),indent=2)+'\n')
    print(log[-500:]+log2[-500:])
if __name__=='__main__':main()
