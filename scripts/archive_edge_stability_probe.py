"""Archive fresh TD evidence, refusing to call a timing failure a candidate."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,hashlib,json,re,shutil,subprocess

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--version',default='EDGE_STABILITY_PROBE_V1');ap.add_argument('--allow-failed',action='store_true');args=ap.parse_args()
 assert re.fullmatch(r'EDGE_STABILITY_PROBE_V1(?:_R\d+)?',args.version)
 snap=json.loads((ROOT/'tmp/probe_prebuild.json').read_text());source=snap['source_commit']
 for name,digest in snap['files'].items():assert sha(ROOT/name)==digest,name
 for name,digest in snap['old_bits'].items():assert sha(ROOT/name)==digest,name
 syn=P/'camera_to_dsi_display_Runs/syn_1';phy=P/'camera_to_dsi_display_Runs/phy_1'
 sl=max(syn.glob('td_*.log'),key=lambda f:f.stat().st_mtime);pl=max(phy.glob('td_*.log'),key=lambda f:f.stat().st_mtime)
 st=sl.read_text(errors='replace');pt=pl.read_text(errors='replace')
 assert not re.search(r'\bERROR\s*:',st+pt)
 assert 'export_db camera_to_dsi_display_gate.db' in st and 'Flow Statistics' in st
 assert 'Timing Mode      : final' in pt and 'BIT-1004 : Generate file camera_to_dsi_display.bit.' in pt
 bit=phy/'camera_to_dsi_display.bit';started=datetime.fromisoformat(snap['time']).timestamp()
 assert bit.stat().st_mtime>=started and sl.stat().st_mtime>=started and pl.stat().st_mtime>=started
 assert bit.stat().st_size>1000000 and sha(bit) not in snap['old_bits'].values()
 for run in (syn,phy):
  inputs=re.findall(r'<File Path="([^"]+)"',(run/'camera_to_dsi_display.prj').read_text())
  assert [(run/f).resolve().relative_to(ROOT).as_posix() for f in inputs]==list(snap['files'])
 area=(phy/'camera_to_dsi_display_phy.area').read_text()
 def av(name):return int(re.search(r'^\s*'+re.escape(name)+r'\s+(\d+)',area,re.M)[1])
 q=(phy/'route.qor').read_text()
 def qv(name):return int(re.search(re.escape(name)+r'\s*\|\s*(-?\d+)',q)[1])
 setup=qv('Setup WNS');hold=qv('Hold WNS');passed=setup>=0 and hold>=0 and qv('Setup TNS')==0 and qv('Hold TNS')==0 and qv('Num of violated S-EP')==qv('Num of violated H-EP')==0
 assert passed or args.allow_failed,'Timing failed: archive under an R0 checkpoint with --allow-failed, not as candidate'
 assert passed or args.version!='EDGE_STABILITY_PROBE_V1'
 timing_path=phy/'final_timing.rpt';assert timing_path.stat().st_mtime>=started
 timing=timing_path.read_text(errors='replace');coverage=re.search(r'STA coverage\s*:\s*([^\n]+)',timing)[1].strip()
 critical=sorted(set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',st+pt)))
 baseline=ROOT/'artifacts/bitstreams/EDGE_QUALITY_V1/build_evidence'
 oldlog='\n'.join(p.read_text(errors='replace') for p in baseline.glob('*.log'))
 new_types=sorted(set(critical)-set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',oldlog)))
 result=dict(version=args.version,source_commit=source,base_commit='8b3b9853cb900ca2305872b4ad9e129274efdbdf',
  bit_sha256=sha(bit).upper(),bit_size=bit.stat().st_size,lut6=av('#lut6'),ff=av('#slice reg'),slice=av('#slice'),eram=av('#eram'),dsp=av('#dsp'),
  setup_wns_ns=setup/1000,hold_wns_ns=hold/1000,sta_coverage=coverage,timing_passed=passed,
  critical_warning_types=critical,new_critical_warning_types=new_types,syn_log=sl.name,phy_log=pl.name,
  probe_hierarchy=[line for line in area.splitlines() if any(n in line for n in ('probe_stream_monitor','probe_fixed_rgb','edge_link_pair_3x3'))])
 a=ROOT/'artifacts/bitstreams'/args.version;assert not a.exists(),'Never overwrite an archived experiment'
 e=a/'build_evidence';e.mkdir(parents=True);shutil.copy2(bit,a/bit.name)
 copies=[(syn,sl.name,'syn_'+sl.name),(phy,pl.name,'phy_'+pl.name),
  (syn,'gate.qor','syn_gate.qor'),(syn,'camera_to_dsi_display_gate.area','camera_to_dsi_display_gate.area'),(syn,'settings.cfg','syn_settings.cfg'),
  (phy,'route.qor','phy_route.qor'),(phy,'camera_to_dsi_display_phy.area','camera_to_dsi_display_phy.area'),(phy,'camera_to_dsi_display_phy.ts','camera_to_dsi_display_phy.ts'),
  (phy,'final_timing.rpt','final_timing.rpt'),(phy,'ignored_timing.rpt','ignored_timing.rpt'),(phy,'camera_to_dsi_display_exception.timing','camera_to_dsi_display_exception.timing'),
  (phy,'route_clock_utilization.txt','route_clock_utilization.txt'),(phy,'settings.cfg','phy_settings.cfg')]
 for directory,name,target in copies:shutil.copy2(directory/name,e/target)
 for name in ('probe_failed_cli_path.txt','probe_prebuild.json','probe_final_flow.tcl','probe_syn_1_stdout.txt','probe_phy_1_stdout.txt','probe_regression_final.txt','probe_bypass_controls.txt','probe_fifo_final.txt','probe_after_boot_small.txt','probe_seq16_small.txt'):
  shutil.copy2(ROOT/'tmp'/name,e/name)
 shutil.copy2(ROOT/'tmp/probe_fifo_boot_final.txt',e/'probe_fifo_boot_final.txt')
 for f in (ROOT/'tmp/probe_aborted_boot_arming').glob('*'):
  if f.is_file():
   dest=e/'ABORTED_BOOT_ARMING';dest.mkdir(exist_ok=True);shutil.copy2(f,dest/f.name)
 (e/'SOURCE_MANIFEST.json').write_text(json.dumps(dict(source_commit=source,files=snap['files']),indent=2)+'\n')
 (e/'PREVIOUS_BITS_UNCHANGED.json').write_text(json.dumps(snap['old_bits'],indent=2)+'\n')
 (e/'FINAL_CHECKS.json').write_text(json.dumps(result,indent=2)+'\n')
 lines=timing.splitlines();(e/'final_timing_summary.txt').write_text('\n'.join(lines[:81])+'\n')
 (e/'CRITICAL_WARNINGS.txt').write_text('\n'.join(line for line in (st+'\n'+pt).splitlines() if 'CRITICAL-WARNING' in line)+'\n')
 tag='edge-stability-probe-v1-candidate' if passed and args.version=='EDGE_STABILITY_PROBE_V1' else '未签发candidate'
 bt=datetime.fromtimestamp(bit.stat().st_mtime,timezone(timedelta(hours=8))).isoformat()
 info=f'''# BUILD_INFO — {args.version}

| 项目 | 值 |
|---|---|
| Version / Role / Branch | {args.version} / MAIN / codex/main/edge-stability-probe-v1 |
| Git Commit SHA（实际构建源码/配置） | {source} |
| Git Tag（归档commit） | {tag}；通过git rev-parse tag^{{commit}}唯一恢复包含bit的提交 |
| 基线 / PR依赖 | 8b3b985诊断 / b64daf3 QUALITY；Draft base codex/main/edge-stability-diag-v1，依赖#7/#6/#4/#3，未合并 |
| Build Time | {bt}；日志{sl.name} / {pl.name} |
| Device / Top / TD | PH1P35MDG324 / design_top_wrapper / Tang Dynasty6.2.168116 |
| 原始bit路径 | {bit} |
| 归档bit路径 | {a/bit.name} |
| Bit SHA-256 / 大小 | {result['bit_sha256']} / {result['bit_size']} bytes |
| Build Result | Synthesis → Physical Design → final Timing Check → bitgen全部完成；时序判定{'PASS' if passed else 'FAIL，不推荐烧录'} |
| LUT6 | {result['lut6']} / 21216 ({100*result['lut6']/21216:.2f}%) |
| FF | {result['ff']} / 42432 ({100*result['ff']/42432:.2f}%) |
| Slice | {result['slice']} / 21216 ({100*result['slice']/21216:.2f}%) |
| RAM / ERAM20K | {result['eram']} / 108 |
| DSP | {result['dsp']} / 40 |
| Setup WNS / TNS / 违例端点 | {setup/1000:+.3f}ns / {qv('Setup TNS')}ps / {qv('Num of violated S-EP')} |
| Hold WNS / TNS / 违例端点 | {hold/1000:+.3f}ns / {qv('Hold TNS')}ps / {qv('Num of violated H-EP')} |
| STA coverage | {coverage}；Routed最终报告 |
| Critical warnings | {', '.join(critical)}；新增类型{new_types}，原始上下文见CRITICAL_WARNINGS.txt；不等于无warning |
| Board Test Status | 待用户PROGRAM_SRAM、拍照反馈；未在本机烧录或量到实板数值 |

## 唯一实验目的与冻结

只增加固定EDGE RGB源和旁路观察诊断。ORIGIN仍为真实摄像头RGB，AWB后的真实valid/提前SOF/tlast原样保留。
Sensor初始化/Exposure1990 half-lines/VTS1000/HTS1600/Gain15.75×/BLC15/AWB_V2、Gaussian/Sobel/NMS/四跳、K3/K4/CDC、原状态OSD/安路Logo/CNT、MIPI/DDR/HDMI正式数据处理、PLL/SDC均冻结。
增加FIFO事件只读输出、两级独立单调旗标CDC、DDR前诊断面板；不修打包器、不修Gray约束、不开发时间滤波。63项实际入口与构建提交一致，构建前{len(snap['old_bits'])}份bit和既有归档不变。

## 实际可观察与局限

诊断面板显示历史SEQ、IN/PACK、算法二值CRC、行数/最后行拍数、SOF间隔/气泡、行/非对齐段错误、累计坏帧/CRC变化、sticky事件/首气泡位置及FIFO armed/样本valid。
无完整测量为W；两FIFO未armed为未测；面板数值十六进制。CRC在OSD前只覆盖两个独立二值采样位，可能碰撞/漏掉复制RGB位错误，不替代完整DDR读回或精确帧身份。
TH80参考CRC6B6DB7D0，TH60=2B018224，TH40=417312EE。软件参考不是板测值。
Edge/Original25拍、OSD2、pack1，总28拍不变；正常每帧230400拍/172800字。

## 验证与风险

新完整RTL6帧720p为1382400有效拍/1036800字；256×160六帧61440拍/46080字；独立异常监测/FIFO事件与关闭probe旧路径/按键/CDC/Sensor/decimal回归通过。实际厂商PHY和真实Sensor控制未模拟；源域观察和CRC不证明物理CDC长期可靠。
首次CLI反斜杠路径在真正综合前失败，守卫拒绝并保留；其后完整重跑。监测单元phase期望修正等记录见VERIFICATION。
当前全设计净增量：LUT6 {result['lut6']-16162:+d}、FF {result['ff']-15423:+d}、Slice {result['slice']-17894:+d}、ERAM {result['eram']-47:+d}、DSP {result['dsp']-9:+d}。全设计重映射值，单模块见area层级。
时序结果不证明实板无抖动；Gray约束覆盖仍需看本轮exception/ignored报告，未通过放宽SDC消除违例。
操作、位定义、判读和回滚见docs/EDGE_STABILITY_PROBE_V1_*。旧QUALITY bit SHA629ACAA828EF8151DED0261779ED8B91F0FA618EED66DD46C72D6E799ADCC9D5。
等待人类Philid14审查最新归档提交和上板反馈，不自动合并或继续下一版本。
'''
 (a/'BUILD_INFO.md').write_text(info,encoding='utf-8')
 print(json.dumps(result,indent=2),flush=True);print('PASS archived fresh build, source63, preserved prior bits',flush=True)

if __name__=='__main__':main()
