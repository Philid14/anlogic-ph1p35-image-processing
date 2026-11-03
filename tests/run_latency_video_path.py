import json,os
from vision_sim import ROOT,HDL,simulate
OUT=ROOT/'tmp/latency_performance/video_path'
IP=HDL.parent/'ip_source'
def main():
    sources=[ROOT/'tests/tb_latency_video_path.sv']
    sources +=[HDL/p for p in ('video_in.v','video_out.v','mc_to_user_interface.v','hdmi_mixer.v',
        'isp/fifo_event_counter.v','anlogic_logo_rom.v','osd_char_lib.v',
        'vision/latency_capture_tag.v','vision/latency_slot_journal.v','vision/latency_tagged_fifo.v')]
    for kind,core in [('w128','4057d6b76aa6'),('w155','f58e8b3e1f3d')]:
        folder=IP/(kind+'_d512_fifo')
        sources +=[folder/(kind+'_d512_fifo.v'),folder/('soft_fifo_al_'+core+'.v')]
    if os.environ.get('LATENCY_STAGING')=='1':
        sources=[ROOT/'tmp/latency_performance/staging'/p.relative_to(HDL)
                 if p.is_relative_to(HDL) and (ROOT/'tmp/latency_performance/staging'/p.relative_to(HDL)).exists()
                 else p for p in sources]
    log=simulate(OUT,'tb_latency_video_path',sources,eram=True,timeout=600)
    assert 'PASS native complete DDR/mixer latency path' in log
    (OUT/'console.txt').write_text(log)
    (OUT/'results.json').write_text(json.dumps(dict(passed=True,native=True,boundary='1280x4, actual240-word bursts and real native FIFO/MC/unpack/mixer, not physical DDR PHY'),indent=2)+'\n')
    print(log[-700:])
if __name__=='__main__':main()
