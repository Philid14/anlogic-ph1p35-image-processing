"""Historical checks with a probe-specific frozen-file allowlist.

The old freeze manifest deliberately rejects the seven documented integration
files. Replace only that old guard, never its vectors or assertions.
"""
from pathlib import Path
import sys,tempfile
import run_edge_quality_v1 as quality
import run_edge_control_v1 as control
from run_edge_stability_probe import frozen

def main():
 frozen();quality.frozen=lambda:None
 sys.argv=['run_edge_quality_v1.py','--small'];quality.main()
 with tempfile.TemporaryDirectory(prefix='probe-controls-') as tmp:
  d=Path(tmp);h=control.HDL;r=control.ROOT
  s=[r/'tests/tb_edge_control_keys.v',h/'edge_key_control.v',h/'edge_config_cdc.v']
  control.simulate(d,'tb_edge_control_keys',s);control.simulate(d,'tb_edge_control_mailbox',s)
  s=[r/'tests/tb_edge_control_sensor.v',h/'edge_key_control.v']+[h/'uics500_cfg'/n for n in ('uicfgcs500_720p.v','uics500reg_720p60.v','uics500regAE.v','SC500GainTbl.v')]
  control.simulate(d,'tb_edge_control_sensor',s)
  control.simulate(d,'tb_edge_control_decimal',[r/'tests/tb_edge_control_decimal.v',h/'edge_status_osd.v',h/'osd_char_lib.v'])
 frozen();print('PASS PROBE disabled regression and unchanged controls',flush=True)

if __name__=='__main__':main()
