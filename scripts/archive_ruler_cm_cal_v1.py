"""Never overwrite: archive timing-clean bit, frozen source and all resource attempts."""
from pathlib import Path
import json,re,shutil,datetime,subprocess
from build_ruler_cm_cal_v1 import ROOT,OUT,snapshot,sha
VERSION='RULER_CM_CAL_V1'
def copy_reports(src,dst):
    dst.mkdir(parents=True,exist_ok=True)
    for f in src.iterdir():
        if f.is_file() and f.suffix in ('.txt','.json','.tcl','.cfg','.area','.ts','.rpt','.qor','.timing','.prj','.png') and f.name not in ('vectors.txt','stim.txt','pack.txt'):
            shutil.copy2(f,dst/f.name)
    for child in src.iterdir():
        if child.is_dir() and (child.name=='regression' or src.name=='regression'):
            copy_reports(child,dst/child.name)
def main():
    frozen=json.loads((OUT/'SOURCE_MANIFEST.json').read_text());now=snapshot()
    for k in ('files','al_sha256','old_bits'):assert now[k]==frozen[k],k
    root=ROOT/'tmp/ruler_cm'
    for directory in ('unit','full_roi','stream_r1','features'):
        result=json.loads((root/directory/'results.json').read_text());assert result['passed']
        for rel,digest in result['sources'].items():assert sha(ROOT/rel)==digest,rel
    for case,beats,words in [('stream_r1',2073600,1555200),('features',1843200,1382400)]:
        result=json.loads((root/case/'results.json').read_text());assert result['beats']==beats and result['words']==words
    for directory in ('stream_r1','features'):
        native=json.loads((root/directory/'SIM_SOURCE_MANIFEST.json').read_text())
        for rel,digest in native.items():assert sha(Path(rel))==digest,rel
    logs='\n'.join((OUT/(stage+'_stdout.txt')).read_text(errors='replace') for stage in ('syn','phy','bit'))
    for stage in ('SYN','PHY','BIT'):assert stage+'_COMPLETE' in logs
    assert not re.search(r'\bERROR\s*:',logs)
    sw,st,hw,ht=map(float,re.findall(r'(?:SWNS|STNS|HWNS|HTNS):\s+(-?[\d.]+)ns',(OUT/'phy_camera_to_dsi_display_phy.ts').read_text()))
    assert sw>=0 and hw>=0 and st==ht==0
    area=(OUT/'phy_camera_to_dsi_display_phy.area').read_text()
    resources={k:int(re.search(r'^#'+n+r'\s+(\d+)',area,re.M)[1]) for k,n in [('slice','slice'),('lut6','lut6'),('ff','reg'),('eram','eram'),('dsp','dsp')]}
    assert resources['slice']<=21216 and resources['eram']<=108 and resources['dsp']<=40
    bit=OUT/'camera_to_dsi_display.bit';assert bit.stat().st_size>1_000_000 and sha(bit) not in frozen['old_bits'].values()
    previous=json.loads((ROOT/'artifacts/bitstreams/VISION_TRACK_MOTION_V1/BUILD_INFO.json').read_text())
    critical=sorted(set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',logs)))
    info=dict(version=VERSION,role='MAIN',branch='codex/main/ruler-cm-cal-v1',source_commit=frozen['source_commit'],
      archive_driver_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      tag='ruler-cm-cal-v1-candidate',build_time=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
      device='PH1P35MDG324 speed3',top='design_top_wrapper',original_bit_path=bit.as_posix(),bit_sha256=sha(bit),
      resources=resources,resource_delta_vs_VISION={k:resources[k]-v for k,v in previous['resources'].items()},
      setup_wns_ns=sw,setup_tns_ns=st,hold_wns_ns=hw,hold_tns_ns=ht,board_test='NOT_RUN',
      critical_warning_types=critical,new_critical_warning_types=sorted(set(critical)-set(previous['critical_warning_types'])),
      high_density_warning='PHY-7022' in logs,extra_common_pixel_cycles=0,common_pixel_cycles=31,
      calibration='Coarse10mm tick pitch: mean4+adjacent intervals per row then two agreeing rows; prefer largest stable pitch across27bands; same pixels-per100mm interface',
      limitations=['Metric ruler/long centimeter ticks are an operator precondition, not OCR/unit recognition',
        'Only a rough commonX/Y scale; perspective/height/blur/regular background patterns can bias scale',
        'Full720p reader/768x288 search separately validated; integrated9frame test search height12 for scheduling runtime',
        'Unchanged inherited FIFO/Gray/thermal/long-run risks and all new features still await physical board validation'],
      route_db_sha256=(OUT/'ROUTE_DB_SHA256.txt').read_text().strip())
    dest=ROOT/'artifacts/bitstreams'/VERSION;assert not dest.exists(),'Never overwrite archive'
    ev=dest/'build_evidence';ev.mkdir(parents=True);shutil.copy2(bit,dest/bit.name);copy_reports(OUT,ev)
    for directory in ('unit','full_roi','stream_r1','features'):copy_reports(root/directory,ev/directory)
    copy_reports(ROOT/'tmp/vision_track_motion/controls',ev/'controls')
    for attempt in root.glob('r[0-9]*'):
        if attempt!=OUT and attempt.is_dir():copy_reports(attempt,ev/'attempts'/attempt.name)
    (dest/'BUILD_INFO.json').write_text(json.dumps(info,indent=2)+'\n')
    text=f'''# {VERSION} BUILD_INFO

- Role / Branch: MAIN / {info['branch']}
- Actual TD source commit: {info['source_commit']}
- Tag: {info['tag']} (created after archive)
- Build time: {info['build_time']}
- Device / Top: {info['device']} / {info['top']}
- Original bit: {info['original_bit_path']}
- Bit SHA256: {info['bit_sha256']}
- Physical resources: {resources}
- Delta vs VISION_TRACK_MOTION_V1: {info['resource_delta_vs_VISION']}
- Setup WNS/TNS: {sw:+.3f}ns / {st}; Hold WNS/TNS: {hw:+.3f}ns / {ht}
- Synthesis → Physical Design → final Timing Check → bitgen: PASS
- Critical warning types: {critical}; new: {info['new_critical_warning_types']}
- Common pixel delay: 31 cycles; extra cycles0. Sensor/ISP parameters, video_in/out, DDR, PLL/pins/SDC unchanged.
- Native vendor ERAM/GSR + ISP/packer (post-AWB/UI boundary; integrated reader search height12, full288 separately tested): 17 complete720p frames, 3916800 valid beats /2937600 packed words.
- CM19-unit checks, full production1280x720/768x288 reader top/bottom search27443319 cycles; two-line mean and exact native font/measurement packing PASS. Seven-mode keys/config CDC preserved.
- Board Test Status: NOT_RUN. No physical/long-run/thermal claim. No PR merged.
- Limits: {'; '.join(info['limitations'])}.
- Rollback: VISION_TRACK_MOTION_V1 / vision-track-motion-v1-candidate / SHA256 {previous['bit_sha256']}.
'''
    (dest/'BUILD_INFO.md').write_text(text);print(json.dumps(info,indent=2))
if __name__=='__main__':main()
