"""Prove frozen detector/ISP/video inputs and the small authorized IO delta."""
from pathlib import Path
import re,json,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[1]
BASE='1cc05016eaef482a87f31bd37bc20a9aae541689'
HDL=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source'
def old(p):return subprocess.check_output(['git','show',BASE+':'+p.relative_to(ROOT).as_posix()],cwd=ROOT).decode('utf-8').replace('\r\n','\n')
def main():
    names=['awb.v','isp/color_compare_stats.v','isp/edge_detect_96.v',
      'isp/gaussian_pair_3x3.v','isp/nms_gradient_pair_3x3.v','isp/edge_link_pair_3x3.v',
      'isp/edge_center_pair_delay.v','isp/edge_temporal_hold.v','isp/style_fill_96.v',
      'isp/rgb_effects_96.v','video_in.v','video_out.v','hdmi_mixer.v','anlogic_logo_rom.v',
      'edge_key_control.v','edge_config_cdc.v','data_96bit_to_128bit.v']
    for name in names:assert (HDL/name).read_text(encoding='utf-8')==old(HDL/name),name
    p=HDL/'osd_char_lib.v';new=p.read_text();base=old(p)
    for ch in ('AN','LU'):
        pattern=r'CHAR_'+ch+r': begin(.*?)endcase'
        values=lambda text:re.findall(r"4'd(\d+): O_row_bits = 16'h([a-f0-9]+)",re.search(pattern,text,re.S)[1])
        assert values(new)==values(base),ch
    p=HDL/'isp/color_compare_osd.v';now=p.read_text();before=old(p)
    assert re.search(r'function \[3:0\] classify;(.*?)endfunction',now,re.S)[0]==re.search(r'function \[3:0\] classify;(.*?)endfunction',before,re.S)[0]
    assert 'wire compare_match=max_difference<=12;' in now
    adc=HDL.parent/'constraints_source/pin.adc';text=adc.read_text();original=old(adc)
    assert text.startswith(original)
    entries=re.findall(r'set_pin_assignment\s*\{\s*([^}]+?)\s*\}\s*\{\s*LOCATION\s*=\s*(\w+);',text)
    pins={port:pin for port,pin in entries}
    assert len(set(pins.values()))==len(pins),'Pin collision'
    assert [pins[f'I_switch[{i}]'] for i in range(4)]==['A4','B4','E11','D11']
    assert pins['I_measure_key_n']=='A9' and pins['I_button[0]']=='B9' and pins['I_button[1]']=='C7'
    sdc=HDL.parent.parent/'td_project/camera_to_dsi_display.sdc'
    assert sdc.read_text()==old(sdc),'SDC changed'
    result=dict(passed=True,baseline=BASE,unchanged_modules=names,chinese_glyphs_unchanged=True,
        color_classifier_and_tolerance_unchanged=True,pin_map=pins,sdc_unchanged=True)
    out=ROOT/'tmp/metrology_v1/SOURCE_SCOPE.json';out.write_text(json.dumps(result,indent=2)+'\n')
    print('PASS frozen algorithms, color classifier, Chinese Logo glyphs, SDC and verified pin delta')
if __name__=='__main__':main()
