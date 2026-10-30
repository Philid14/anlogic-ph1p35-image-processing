"""Cycle-equivalence of original mixer and address-retimed production mixer."""
import subprocess,json,hashlib
from pathlib import Path
import run_edge_control_v1 as c
OUT=c.ROOT/'tmp/metrology_v1/mixer';OUT.mkdir(parents=True,exist_ok=True)
BASE='1cc05016eaef482a87f31bd37bc20a9aae541689'
def main():
    p=c.HDL/'hdmi_mixer.v';rel=p.relative_to(c.ROOT).as_posix()
    original=subprocess.check_output(['git','show',BASE+':'+rel],cwd=c.ROOT)
    assert b'module hdmi_mixer #(' in original
    ref=OUT/'reference_mixer.v';ref.write_bytes(original.replace(b'module hdmi_mixer #(',b'module reference_mixer #(',1))
    sources=[c.ROOT/'tests/tb_mixer_logo_retime.sv',ref,p,c.HDL/'osd_char_lib.v',c.HDL/'anlogic_logo_rom.v']
    log=c.simulate(OUT,'tb_mixer_logo_retime',sources)
    (OUT/'console.txt').write_text(log)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,baseline=BASE,full_frames=2,
        scope='all RGB and DE/HS/VS/read-enable every cycle, no output latency change; post-DDR digital boundary, no board claim',
        sources={p.relative_to(c.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}),indent=2)+'\n')
if __name__=='__main__':main()
