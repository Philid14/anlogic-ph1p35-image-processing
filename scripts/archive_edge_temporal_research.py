"""Archive a fresh diagnostic build. Failed timing requires an explicit Rn name."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,hashlib,json,re,shutil

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--version',default='EDGE_TEMPORAL_RESEARCH_V1');ap.add_argument('--allow-failed',action='store_true');a=ap.parse_args()
    assert re.fullmatch(r'EDGE_TEMPORAL_RESEARCH_V1(?:_R\d+)?',a.version)
    snap=json.loads((ROOT/'tmp/temporal_prebuild.json').read_text());start=datetime.fromisoformat(snap['time']).timestamp()
    for n,h in snap['files'].items():assert sha(ROOT/n)==h,n
    for n,h in snap['old_bits'].items():assert sha(ROOT/n)==h,n
    syn=P/'camera_to_dsi_display_Runs/syn_1';phy=P/'camera_to_dsi_display_Runs/phy_1'
    sl=max(syn.glob('td_*.log'),key=lambda p:p.stat().st_mtime);pl=max(phy.glob('td_*.log'),key=lambda p:p.stat().st_mtime)
    st=sl.read_text(errors='replace');pt=pl.read_text(errors='replace');bit=phy/'camera_to_dsi_display.bit'
    assert not re.search(r'\bERROR\s*:',st+pt)
    assert 'export_db camera_to_dsi_display_gate.db' in st and 'Flow Statistics' in st
    assert 'Timing Mode      : final' in pt and 'BIT-1004 : Generate file camera_to_dsi_display.bit.' in pt
    assert min(bit.stat().st_mtime,sl.stat().st_mtime,pl.stat().st_mtime)>=start
    assert bit.stat().st_size>1000000 and sha(bit) not in snap['old_bits'].values()
    for directory in (syn,phy):
        paths=re.findall(r'<File Path="([^"]+)"',(directory/'camera_to_dsi_display.prj').read_text())
        assert [(directory/p).resolve().relative_to(ROOT).as_posix() for p in paths]==list(snap['files'])
    area=(phy/'camera_to_dsi_display_phy.area').read_text();q=(phy/'route.qor').read_text()
    av=lambda n:int(re.search(r'^\s*'+re.escape(n)+r'\s+(\d+)',area,re.M)[1])
    qv=lambda n:int(re.search(re.escape(n)+r'\s*\|\s*(-?\d+)',q)[1])
    passed=all(qv(n)>=0 for n in ('Setup WNS','Hold WNS')) and all(qv(n)==0 for n in ('Setup TNS','Hold TNS','Num of violated S-EP','Num of violated H-EP'))
    assert passed or (a.allow_failed and a.version!='EDGE_TEMPORAL_RESEARCH_V1'),'Failed timing cannot be candidate'
    timing=(phy/'final_timing.rpt').read_text(errors='replace');coverage=re.search(r'STA coverage\s*:\s*([^\n]+)',timing)[1].strip()
    critical=sorted(set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',st+pt)))
    old='\n'.join(p.read_text(errors='replace') for p in (ROOT/'artifacts/bitstreams/EDGE_QUALITY_V1/build_evidence').glob('*.log'))
    new=sorted(set(critical)-set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',old)))
    result=dict(version=a.version,source_commit=snap['source_commit'],baseline_commit='7343cfeb1de049e0793e63524cae071e9ae5018a',bit_sha256=sha(bit).upper(),bit_size=bit.stat().st_size,
        lut=av('#lut6'),ff=av('#slice reg'),slice=av('#slice'),eram=av('#eram'),dsp=av('#dsp'),setup_wns_ns=qv('Setup WNS')/1000,hold_wns_ns=qv('Hold WNS')/1000,
        setup_tns_ps=qv('Setup TNS'),hold_tns_ps=qv('Hold TNS'),timing_passed=passed,sta_coverage=coverage,critical_warning_types=critical,new_critical_warning_types=new)
    dest=ROOT/'artifacts/bitstreams'/a.version;assert not dest.exists(),'Never overwrite history';e=dest/'build_evidence';e.mkdir(parents=True)
    shutil.copy2(bit,dest/bit.name)
    copies=[(syn,sl.name,'syn_'+sl.name),(phy,pl.name,'phy_'+pl.name),(syn,'gate.qor','syn_gate.qor'),(syn,'camera_to_dsi_display_gate.area','syn.area'),
        (syn,'settings.cfg','syn_settings.cfg'),(phy,'settings.cfg','phy_settings.cfg')]
    for n in ('route.qor','camera_to_dsi_display_phy.area','camera_to_dsi_display_phy.ts','final_timing.rpt','ignored_timing.rpt','camera_to_dsi_display_exception.timing','route_clock_utilization.txt'):
        copies.append((phy,n,n))
    for directory,n,target in copies:shutil.copy2(directory/n,e/target)
    for n in ('temporal_prebuild.json','temporal_final_flow.tcl','temporal_syn_1_stdout.txt','temporal_phy_1_stdout.txt'):
        shutil.copy2(ROOT/'tmp'/n,e/n)
    for n in ('temporal_isp_integration.txt','temporal_regression.txt'):
        if (ROOT/'tmp'/n).exists():shutil.copy2(ROOT/'tmp'/n,e/n)
    (e/'FINAL_CHECKS.json').write_text(json.dumps(result,indent=2)+'\n')
    (e/'SOURCE_MANIFEST.json').write_text(json.dumps(dict(source_commit=snap['source_commit'],files=snap['files']),indent=2)+'\n')
    (e/'PREVIOUS_BITS_UNCHANGED.json').write_text(json.dumps(snap['old_bits'],indent=2)+'\n')
    (e/'CRITICAL_WARNINGS.txt').write_text('\n'.join(x for x in (st+pt).splitlines() if 'CRITICAL-WARNING' in x)+'\n')
    tag='edge-temporal-research-v1-candidate' if passed and a.version=='EDGE_TEMPORAL_RESEARCH_V1' else '未签发candidate'
    bt=datetime.fromtimestamp(bit.stat().st_mtime,timezone(timedelta(hours=8))).isoformat()
    text=f'''# BUILD_INFO — {a.version}

| 项目 | 值 |
|---|---|
| Version / Role | {a.version} / MAIN；独立真实RGB采样诊断，不是时间滤波优化版本 |
| Branch | codex/main/edge-temporal-research-v1 |
| 实际构建源码Git Commit | {snap['source_commit']} |
| Git Tag（包含bit的归档提交） | {tag}；git rev-parse tag^{{commit}}解析归档SHA |
| 基线 / PR依赖 | 7343cfe PROBE / QUALITY b64daf3；Draft base codex/main/edge-stability-probe-v1，依赖#8/#7/#6/#4/#3，不自动合并 |
| Build Time | {bt} |
| Device / Top / TD | PH1P35MDG324 / design_top_wrapper / Tang Dynasty6.2.168116 |
| 原始bit路径 | {bit} |
| Bit Path | artifacts/bitstreams/{a.version}/{bit.name} |
| SHA-256 / bytes | {result['bit_sha256']} / {result['bit_size']} |
| Build Result | Synthesis → Physical Design → final Timing Check → bitgen全部完成；{'PASS' if passed else '时序FAIL，不作为上板候选'} |
| LUT6 | {result['lut']} / 21216 ({100*result['lut']/21216:.2f}%) |
| FF | {result['ff']} / 42432 ({100*result['ff']/42432:.2f}%) |
| Slice | {result['slice']} / 21216 ({100*result['slice']/21216:.2f}%) |
| RAM / ERAM20K | {result['eram']} / 108 |
| DSP | {result['dsp']} / 40 |
| Setup WNS / TNS / 违例端点 | {qv('Setup WNS')/1000:+.3f}ns / {qv('Setup TNS')}ps / {qv('Num of violated S-EP')} |
| Hold WNS / TNS / 违例端点 | {qv('Hold WNS')/1000:+.3f}ns / {qv('Hold TNS')}ps / {qv('Num of violated H-EP')} |
| STA coverage | {coverage} |
| Critical warnings | {critical}；新增类型{new}；原始上下文随附 |
| Board Test Status | 待用户上板及手机录像；本机没有采集到真实ROI数据，不冒称板测通过 |

## 诊断与冻结

Edge恢复真实AWB后RGB，原Gaussian/Sobel/NMS/四跳及Original/K3/K4/旧状态OSD/Logo/CNT不变；AWB仅加只读、对齐到乘法输出的原RGB/实际增益/上次完整统计端口，没有冻结或改动正式增益。Sensor Exposure1990 half-lines/VTS1000/HTS1600/Gain15.75×/BLC15、PLL/SDC、MIPI/DDR/HDMI传输不变。
600个SOF后冻结中心X576..703/Y344..375的8个连续采集帧，RGB888不降精度；实际R/B Q16增益、统计、两侧CRC、行帧/打包数量、FIFO历史状态、32bit MIPI周期时间戳随数据输出。采样与页缓存均现有MIPI时钟，不加视频反压或像素级延迟，总25+2+1=28拍。
通过101页带header/payload CRC的黑白8像素单元画面导出，不是假设已有UART/ILA。页面每60个采集SOF切换、循环，手机录像后离线无损解码；未验证真实手机可解码性。面板覆盖是诊断用途，旧固定PROBE面板在导出时隐藏，原状态/Logo/CNT仍保留。

## 验证、追溯与风险

65项TD实际输入与源码提交一致，构建前{len(snap['old_bits'])}份bit哈希不变。独立捕获/完整720p/实际ISP边界/按拍OSD、与旧AWB全输出并行对照、光学失真/负例、旧QUALITY/PROBE/按键/CDC/Sensor回归结果见docs/edge_temporal_evidence及研究报告。
本版本使用真实RGB路径，不能套用固定PROBE的资源节省。相对QUALITY净增LUT {result['lut']-16162:+d}、FF {result['ff']-15423:+d}、Slice {result['slice']-17894:+d}、ERAM {result['eram']-47:+d}、DSP {result['dsp']-9:+d}，其中包含采样诊断，不代表正式滤波器开销。
CRC可拒绝错误但不是纠错码；模糊/反光/滚动快门可导致缺页，只重录同一冻结burst补页，不拼接不同重置。ROI保留7内部横采样/7行halo后仅50×18点可用于完整四跳比较，8帧较短，需要多场景重复burst。AWB后图由真实pre RGB与实际gain位准确重建，并由实际post CRC校验，不声称采到Bayer RAW或完整全帧。
统计seq与采集seq独立，时间戳不是TEAM同帧端到端延迟接口。FIFO历史sticky已置位后无法数重复事件；数量异常、未armed、帧内gain变化、CRC或新sticky变化必须先排查，不做算法排名。既有Gray max_delay覆盖风险未修复，实际Ignored见归档；STA通过不证明长期硬件稳定。
回滚重新PROGRAM_SRAM烧录EDGE_QUALITY_V1，SHA629ACAA828EF8151DED0261779ED8B91F0FA618EED66DD46C72D6E799ADCC9D5；固定源对照使用EDGE_STABILITY_PROBE_V1，SHA7A78AFBC6126CDA8860E70241DA7AA934C68B0C98D1DB02E7FD2F7790A061980。
'''
    (dest/'BUILD_INFO.md').write_text(text,encoding='utf8');print(json.dumps(result,indent=2));print('PASS fresh diagnostic archive; old bits unchanged')

if __name__=='__main__':main()
