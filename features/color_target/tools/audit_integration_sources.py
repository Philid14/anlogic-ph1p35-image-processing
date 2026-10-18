"""Read-only static evidence extractor; never runs TD or edits MAIN files."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[3]
BASE='in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/'
HDL=BASE+'user_source/hdl_source/'
POINTS={
    HDL+'design_top_wrapper.v':('S_rst_n','u_isp_top','u_video_in','I_mipi_rx_error','u_video_out','u_hdmi_mixer'),
    HDL+'isp/uial2axis.v':('assign axis_tlast','assign axis_tuser'),
    HDL+'awb.v':('signal_delay_d','valid_d2 <=','assign O_tuser','assign O_tlast','assign O_tvalid'),
    HDL+'isp/isp_top.v':('awb_O_tdata;','u_control','u_awb','algorithm_last_128'),
    HDL+'isp/data128_96/data128_96.v':('assign O_tdata',),
    HDL+'isp/demosaic_4x_2_0/bilinear_interpolation.v':("8'b0",),
    HDL+'isp/edge_control_stream.v':('early notification','valid_p <=','selected_data'),
    HDL+'video_in.v':('S_video_in_wp','O_video_out_rp','S_frame_start =','I_mipi_rx_error','S_frame_start && I_mipi_rx_error'),
    HDL+'video_out.v':('I_video_out_rp','S_video_frame_start','case(I_video_out_rp)','I_ddr_clk','I_dsi_clk'),
    HDL+'hdmi_mixer.v':('S_x_2d','S_video_data_2d','O_hdmi_data'),
    HDL+'data_96bit_to_128bit.v':('O_128b_frame_start <=','S_cnt <=','O_128b_valid <='),
    BASE+'td_project/camera_to_dsi_display.al':('Path="D:','awb.v','camera_to_dsi_display.sdc','TOP_MODULE','Run Name='),
    BASE+'td_project/camera_to_dsi_display.sdc':('create_clock','rename_clock','set_clock_groups'),
    BASE+'user_source/ip_source/PLL/Design.xml':('REQUEST_FREQ_DISP',),
    HDL+'ph1p35_ddr/ph1p35_324_ddr_wrapper.v':('O_ddr_clk =','dhi_clk',),
    'features/color_target/rtl/color_target_detect_stream.v':('FILTER_ENABLE=0','input_open','color_target_support3','color_target_mask_stats'),
    'features/color_target/rtl/color_target_track.v':('wire strobe','session_new','if (strobe)','O_out_frame_id'),
    'features/color_target/rtl/color_target_text_overlay.v':('wire start =','raw_c <= I_count','dig_c <= next_c'),
    'scripts/prepare_td_runs.py':('unescaped','settings.cfg','write_text'),
    'artifacts/bitstreams/EDGE_CONTROL_V1/BUILD_INFO.md':('Git Commit','Setup WNS','Board Test Status','冻结STA','最差setup'),
    'artifacts/bitstreams/EDGE_CONTROL_V1/build_evidence/final_timing_summary.txt':('STA coverage','SWNS:','HWNS:','MIPI_RX_BYTE_CLK','HDMI_PIXEL_CLK','pll_clk_24m','usr_clk'),
}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    files={};excerpts=[]
    for relative,patterns in POINTS.items():
        path=ROOT/relative;raw=path.read_bytes();content=raw.decode('utf-8-sig',errors='replace');lines=content.splitlines()
        hits=[i for i,line in enumerate(lines,1) if any(p in line for p in patterns)]
        files[relative]={'sha256_lf':hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest(),'lines':len(lines),'hits':hits}
        excerpts += ['\n## '+relative,'```text']
        used=set()
        for at in hits:
            for i in range(max(1,at-1),min(len(lines),at+2)+1):
                if i not in used:excerpts.append(f'{i}: {lines[i-1]}');used.add(i)
        excerpts.append('```')
    al_path=ROOT/BASE/'td_project/camera_to_dsi_display.al'
    al=al_path.read_text(encoding='utf-8')
    # Native TD format has unescaped '&'; do not parse or rewrite as XML.
    entries=re.findall(r'<File Path="([^"]+)">',al)
    resolved=[dict(path=e,exists=(al_path.parent/e).is_file()) for e in entries]
    bounded=[HDL+x for x in ('design_top_wrapper.v','awb.v','video_in.v','video_out.v','hdmi_mixer.v','isp/isp_top.v')]
    identity_hits={p:[i for i,line in enumerate((ROOT/p).read_text(encoding='utf-8-sig').splitlines(),1)
        if re.search(r'\b(session_id|frame_id|generation_id|slot_generation)\b',line)] for p in bounded}
    report=dict(kind='STATIC SOURCE EVIDENCE; no synthesis/CDC/board validation',
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
        files=files,al_entries=resolved,target_entries=[e for e in entries if 'color_target' in e],
        identity_symbol_search={'scope':bounded,'pattern':'session_id|frame_id|generation_id|slot_generation','hits':identity_hits})
    history=json.loads((ROOT/'artifacts/bitstreams/EDGE_CONTROL_V1/build_evidence/SOURCE_MANIFEST.json').read_text(encoding='utf-8-sig'))
    comparisons=[]
    tree=subprocess.check_output(['git','ls-tree','-r','-z',history['source_commit']],cwd=ROOT)
    blobs={entry.split(b'\t',1)[1].decode('utf-8'):entry.split(b'\t',1)[0].split()[2].decode('ascii')
           for entry in tree.split(b'\0') if entry}
    for relative in history['files']:
        # Blob IDs avoid Windows git-show path stat limits; no Git config edits.
        before=subprocess.check_output(['git','cat-file','blob',blobs[relative]],cwd=ROOT)
        now=(ROOT/relative).read_bytes()
        comparisons.append(dict(path=relative,same_lf=before.replace(b'\r\n',b'\n')==now.replace(b'\r\n',b'\n')))
    report['historical_main_input_comparison']=dict(source_commit=history['source_commit'],
        method='LF-normalized git object versus current files; not a fresh build',files=comparisons)
    (args.out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (args.out/'excerpts.md').write_text('\n'.join(excerpts)+'\n',encoding='utf-8')
    print('Static files:',len(files),'TD entries:',len(entries),'TARGET entries:',len(report['target_entries']))
    print('Missing TD entry paths:',sum(not e['exists'] for e in resolved))
    print('Historical MAIN inputs unchanged:',sum(c['same_lf'] for c in comparisons),'/',len(comparisons))
    print('Identity symbol search is bounded to the listed main-path files; absence is not a whole-repository proof.')

if __name__=='__main__':main()
