"""Archive actual routed results; failed STA is never a candidate."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,hashlib,json,re,shutil

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project'
TMP=ROOT/'tmp/edge_temporal_v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--failed',action='store_true');parser.add_argument('--rejected-reason',default='');args=parser.parse_args()
    version='EDGE_TEMPORAL_V1_R0' if args.failed else 'EDGE_TEMPORAL_V1'
    snap=json.loads((TMP/'prebuild.json').read_text());start=datetime.fromisoformat(snap['time']).timestamp()
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
    assert passed or args.failed,'STA failed: archive --failed, do not issue candidate'
    timing=(phy/'final_timing.rpt').read_text(errors='replace');coverage=re.search(r'STA coverage\s*:\s*([^\n]+)',timing)[1].strip()
    critical=sorted(set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',st+pt)))
    old='\n'.join(p.read_text(errors='replace') for p in (ROOT/'artifacts/bitstreams/EDGE_QUALITY_V1/build_evidence').glob('*.log'))
    new=sorted(set(critical)-set(re.findall(r'(\w+-\d+) CRITICAL-WARNING',old)))
    result=dict(version=version,source_commit=snap['source_commit'],resume_driver_commit=snap.get('resume_driver_commit'),
        baseline_commit='b64daf39af09980621adb1138df1674a8501ea09',bit_sha256=sha(bit).upper(),bit_size=bit.stat().st_size,
        lut=av('#lut6'),ff=av('#slice reg'),slice=av('#slice'),eram=av('#eram'),dsp=av('#dsp'),
        setup_wns_ns=qv('Setup WNS')/1000,hold_wns_ns=qv('Hold WNS')/1000,setup_tns_ps=qv('Setup TNS'),hold_tns_ps=qv('Hold TNS'),
        timing_passed=passed,sta_coverage=coverage,critical_warning_types=critical,new_critical_warning_types=new,
        additional_pipeline_cycles=2,additional_frame_wait=0,candidate_eligible=passed and not args.failed,rejection_reason=args.rejected_reason,
        board_test='not issued for board testing' if args.failed else 'pending; FIFO steady recurrence and actual visual quality unverified')
    result['delta_from_quality']={n:result[n]-v for n,v in dict(lut=16162,ff=15423,slice=17894,eram=47,dsp=9).items()}
    dest=ROOT/'artifacts/bitstreams'/version;assert not dest.exists(),'never overwrite an archive';e=dest/'build_evidence';e.mkdir(parents=True)
    shutil.copy2(bit,dest/bit.name)
    for directory,n,target in [(syn,sl.name,'syn_'+sl.name),(phy,pl.name,'phy_'+pl.name),(syn,'gate.qor','syn_gate.qor'),(syn,'camera_to_dsi_display_gate.area','syn.area'),(syn,'settings.cfg','syn_settings.cfg'),(phy,'settings.cfg','phy_settings.cfg')]:shutil.copy2(directory/n,e/target)
    for n in ('route.qor','camera_to_dsi_display_phy.area','camera_to_dsi_display_phy.ts','final_timing.rpt','ignored_timing.rpt','camera_to_dsi_display_exception.timing','route_clock_utilization.txt'):shutil.copy2(phy/n,e/n)
    for n in ('prebuild.json','final_flow.tcl','syn_1_stdout.txt','phy_1_stdout.txt','build_driver.log','build_resume.log','rtl_full.log','final_small.log','legacy_small.log','reliability_osd.log','rtl_results.json','scope_checks.json','balanced_eol_r0_failure.txt','balanced_eol.txt','balanced_eol_fixed_pass.txt','fixed_full.log','fixed_rtl_results.json'):
        if (TMP/n).exists():shutil.copy2(TMP/n,e/n)
    (e/'FINAL_CHECKS.json').write_text(json.dumps(result,indent=2)+'\n')
    (e/'SOURCE_MANIFEST.json').write_text(json.dumps(dict(source_commit=snap['source_commit'],files=snap['files']),indent=2)+'\n')
    (e/'PREVIOUS_BITS_UNCHANGED.json').write_text(json.dumps(snap['old_bits'],indent=2)+'\n')
    (e/'CRITICAL_WARNINGS.txt').write_text('\n'.join(x for x in (st+pt).splitlines() if 'CRITICAL-WARNING' in x)+'\n')
    tag='edge-temporal-v1-candidate' if passed and not args.failed else 'not issued'
    bt=datetime.fromtimestamp(bit.stat().st_mtime,timezone(timedelta(hours=8))).isoformat()
    info=f'''# BUILD_INFO — {version}

| 项目 | 实际值 |
|---|---|
| Version / Role | {version} / MAIN |
| Branch | codex/main/edge-temporal-v1 |
| 实际TD输入源码commit | {snap['source_commit']} |
| PHY恢复脚本commit | {snap.get('resume_driver_commit','not needed')}；仅修正面积行匹配，64项TD输入逐字节匹配原综合，无重新综合 |
| Git Tag | {tag}；解析tag^{{commit}}恢复包含bit的归档提交 |
| 基线 / PR | QUALITY b64daf39af09980621adb1138df1674a8501ea09；Draft #10→#6→#4→#3，均不自动合并 |
| Build Time | {bt} |
| Device / Top / TD | PH1P35MDG324 / design_top_wrapper / Tang Dynasty6.2.168116 |
| 原始bit | {bit} |
| 归档bit | artifacts/bitstreams/{version}/{bit.name} |
| SHA-256 / bytes | {result['bit_sha256']} / {result['bit_size']} |
| Build Result | Synthesis → Physical Design → final Timing Check → bitgen；{'PASS' if passed else 'STA FAILED; not a candidate'} |
| Release Decision | {'REJECTED: '+args.rejected_reason if args.failed else 'candidate; board validation pending'} |
| LUT6 | {result['lut']} / 21216 |
| FF | {result['ff']} / 42432 |
| Slice | {result['slice']} / 21216 ({100*result['slice']/21216:.2f}%) |
| ERAM20K / DSP | {result['eram']} / 108；{result['dsp']} / 40 |
| Setup WNS / Hold WNS | {result['setup_wns_ns']:+.3f}ns / {result['hold_wns_ns']:+.3f}ns |
| Setup TNS / Hold TNS | {result['setup_tns_ps']}ps / {result['hold_tns_ps']}ps |
| STA coverage | {coverage} |
| Critical warnings | {critical}；新增类型{new}，原始上下文随附 |
| Board Test Status | {'REJECTED；不用于上板验收' if args.failed else '待用户烧录；真实画质、FIFO稳态复发、长期与光照变化验收均未完成'} |

## 算法与预算

E_t=Q_t OR (Q_(t-1) AND 当前同坐标未抑制Sobel幅值>=floor(TH/2))。历史只保存原始QUALITY边缘，最多一帧、非递归，当前边缘不删除。原先Gaussian/Sobel/NMS/四跳不改；新增4级支持位中心搬运及1位/内部点历史缓存，未继承ROI大缓存/编码页面。

相比QUALITY路由净增{result['delta_from_quality']}；包含只读FIFO计数及第三行OSD的成本，不把净增量当单独算法模块成本。新增2寄存周期，Edge/Original27+OSD2+pack1=30；无整帧等待和新增空间偏移。慢速运动可能短暂增厚/双线，既有真实ROI无可靠轮廓真值，模型收益不冒充板上收益。

Sensor Exposure1990 half-lines/VTS1000/HTS1600/Gain15.75×、BLC15/AWB_V2/Original颜色、K3/K4/Logo/CNT/视频规格/MIPI/DDR/HDMI控制与PLL/SDC保持；64项TD输入和旧bit均已校验。只有已有OSD扩展B/S历史计数行；FIFO控制不改。

## 验证与风险

完整720p×10采集帧2,304,000有效拍/1,728,000打包字逐字节对照通过；Original、帧内配置锁存、提前/同拍SOF、全生产历史地址及中心搬运覆盖。单元另测复位、短帧、缺EOL、超长帧、TH变更、支持撤销与非递归释放；旧QUALITY/NMS小尺寸及所有link尾数/1280宽地址回归通过。FIFO计数启动/稳态/重复/饱和/复位与实际OSD字形打包独立验证。

综合已成功；驱动首次因查找实例面积行的辅助脚本错误停在综合之后，修正后验证全部TD输入不变及综合DB哈希，只恢复PHY，没有借此重编多个算法候选。原失败驱动日志保留。

STA通过不证明长期硬件稳定；既有FIFO Gray max_delay受clock groups覆盖的风险未修复、全局约束未改。S计数若增加，作为正式验收阻断项先查FIFO/DDR，不能用本算法掩盖。详见docs/EDGE_TEMPORAL_V1_DESIGN.md及最终报告/BOARD_TEST。

回滚：重新PROGRAM_SRAM烧录artifacts/bitstreams/EDGE_QUALITY_V1/camera_to_dsi_display.bit，SHA629ACAA828EF8151DED0261779ED8B91F0FA618EED66DD46C72D6E799ADCC9D5；默认TEMPORAL_ENABLE=0也可恢复旧算法。候选未自动合并，不继续下一版本。
'''
    (dest/'BUILD_INFO.md').write_text(info,encoding='utf-8');print(json.dumps(result,indent=2));print('Archived',dest)


if __name__=='__main__':main()
