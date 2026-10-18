"""Archive a passing EDGE_MULTI_MODE_V1 routed build without overwriting history."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project"
TMP = ROOT / "tmp/edge_multi_mode_v1"
VERSION = "EDGE_MULTI_MODE_V1"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    snap = json.loads((TMP / "prebuild.json").read_text())
    start = datetime.fromisoformat(snap["time"]).timestamp()
    for name, digest in snap["files"].items():
        assert sha(ROOT / name) == digest, name
    for name, digest in snap["old_bits"].items():
        assert sha(ROOT / name) == digest, name

    syn = P / "camera_to_dsi_display_Runs/syn_1"
    phy = P / "camera_to_dsi_display_Runs/phy_1"
    syn_log = max(syn.glob("td_*.log"), key=lambda path: path.stat().st_mtime)
    phy_log = max(phy.glob("td_*.log"), key=lambda path: path.stat().st_mtime)
    syn_text = syn_log.read_text(errors="replace")
    phy_text = phy_log.read_text(errors="replace")
    bit = phy / "camera_to_dsi_display.bit"
    assert not re.search(r"\bERROR\s*:", syn_text + phy_text)
    assert "export_db camera_to_dsi_display_gate.db" in syn_text
    assert "Flow Statistics" in syn_text
    assert "Timing Mode      : final" in phy_text
    assert "BIT-1004 : Generate file camera_to_dsi_display.bit." in phy_text
    assert min(bit.stat().st_mtime, syn_log.stat().st_mtime, phy_log.stat().st_mtime) >= start
    assert bit.stat().st_size > 1_000_000
    assert sha(bit) not in snap["old_bits"].values()

    for directory in (syn, phy):
        paths = re.findall(
            r'<File Path="([^"]+)"',
            (directory / "camera_to_dsi_display.prj").read_text(),
        )
        assert [
            (directory / path).resolve().relative_to(ROOT).as_posix() for path in paths
        ] == list(snap["files"])

    area = (phy / "camera_to_dsi_display_phy.area").read_text()
    qor = (phy / "route.qor").read_text()
    area_value = lambda name: int(
        re.search(r"^\s*" + re.escape(name) + r"\s+(\d+)", area, re.M)[1]
    )
    qor_value = lambda name: int(re.search(re.escape(name) + r"\s*\|\s*(-?\d+)", qor)[1])
    passed = (
        all(qor_value(name) >= 0 for name in ("Setup WNS", "Hold WNS"))
        and all(
            qor_value(name) == 0
            for name in ("Setup TNS", "Hold TNS", "Num of violated S-EP", "Num of violated H-EP")
        )
    )
    assert passed, "STA failed; do not issue a candidate"
    timing = (phy / "final_timing.rpt").read_text(errors="replace")
    coverage = re.search(r"STA coverage\s*:\s*([^\n]+)", timing)[1].strip()
    critical = sorted(set(re.findall(r"(\w+-\d+) CRITICAL-WARNING", syn_text + phy_text)))
    previous_logs = "\n".join(
        path.read_text(errors="replace")
        for path in (ROOT / "artifacts/bitstreams/EDGE_TEMPORAL_V1/build_evidence").glob("*.log")
    )
    new_critical = sorted(
        set(critical) - set(re.findall(r"(\w+-\d+) CRITICAL-WARNING", previous_logs))
    )
    result = dict(
        version=VERSION,
        source_commit=snap["source_commit"],
        bit_sha256=sha(bit).upper(),
        bit_size=bit.stat().st_size,
        lut=area_value("#lut6"),
        ff=area_value("#slice reg"),
        slice=area_value("#slice"),
        eram=area_value("#eram"),
        dsp=area_value("#dsp"),
        setup_wns_ns=qor_value("Setup WNS") / 1000,
        hold_wns_ns=qor_value("Hold WNS") / 1000,
        setup_tns_ps=qor_value("Setup TNS"),
        hold_tns_ps=qor_value("Hold TNS"),
        timing_passed=passed,
        sta_coverage=coverage,
        critical_warning_types=critical,
        new_critical_warning_types=new_critical,
        additional_pipeline_cycles_from_temporal=0,
        per_branch_alignment_cycles=27,
        osd_cycles=2,
        pack_cycles=1,
        candidate_eligible=True,
        board_test="pending; all visual modes, threshold persistence and 30-minute stability unverified",
    )
    result["delta_from_temporal"] = {
        name: result[name] - value
        for name, value in dict(lut=16119, ff=15657, slice=17684, eram=75, dsp=9).items()
    }

    dest = ROOT / "artifacts/bitstreams" / VERSION
    assert not dest.exists(), "never overwrite an archive"
    evidence = dest / "build_evidence"
    evidence.mkdir(parents=True)
    shutil.copy2(bit, dest / bit.name)
    copies = [
        (syn, syn_log.name, "syn_" + syn_log.name),
        (phy, phy_log.name, "phy_" + phy_log.name),
        (syn, "gate.qor", "syn_gate.qor"),
        (syn, "camera_to_dsi_display_gate.area", "syn.area"),
        (syn, "settings.cfg", "syn_settings.cfg"),
        (phy, "settings.cfg", "phy_settings.cfg"),
    ]
    for directory, name, target in copies:
        shutil.copy2(directory / name, evidence / target)
    for name in (
        "route.qor",
        "camera_to_dsi_display_phy.area",
        "camera_to_dsi_display_phy.ts",
        "final_timing.rpt",
        "ignored_timing.rpt",
        "camera_to_dsi_display_exception.timing",
        "route_clock_utilization.txt",
    ):
        shutil.copy2(phy / name, evidence / name)
    for name in (
        "prebuild.json",
        "final_flow.tcl",
        "syn_1_stdout.txt",
        "phy_1_stdout.txt",
        "rtl_results.json",
        "rtl_console.log",
    ):
        if (TMP / name).exists():
            shutil.copy2(TMP / name, evidence / name)

    (evidence / "FINAL_CHECKS.json").write_text(json.dumps(result, indent=2) + "\n")
    (evidence / "SOURCE_MANIFEST.json").write_text(
        json.dumps(dict(source_commit=snap["source_commit"], files=snap["files"]), indent=2)
        + "\n"
    )
    (evidence / "PREVIOUS_BITS_UNCHANGED.json").write_text(
        json.dumps(snap["old_bits"], indent=2) + "\n"
    )
    (evidence / "CRITICAL_WARNINGS.txt").write_text(
        "\n".join(
            line for line in (syn_text + phy_text).splitlines() if "CRITICAL-WARNING" in line
        )
        + "\n"
    )

    build_time = datetime.fromtimestamp(
        bit.stat().st_mtime, timezone(timedelta(hours=8))
    ).isoformat()
    info = f"""# BUILD_INFO — {VERSION}

| 项目 | 实际值 |
|---|---|
| Version / Role | {VERSION} / MAIN |
| Branch | codex/main/edge-multi-mode-v1 |
| 实际TD输入源码commit | {snap['source_commit']} |
| Git Tag | edge-multi-mode-v1-candidate |
| 基线 / PR | EDGE_TEMPORAL_V1 b47105f；Draft PR 以 codex/main/edge-temporal-v1 为 base，不自动合并 |
| Build Time | {build_time} |
| Device / Top / TD | PH1P35MDG324 / design_top_wrapper / Tang Dynasty6.2.168116 |
| 原始bit | {bit} |
| 归档bit | artifacts/bitstreams/{VERSION}/{bit.name} |
| SHA-256 / bytes | {result['bit_sha256']} / {result['bit_size']} |
| Build Result | Synthesis → Physical Design → final Timing Check → bitgen；PASS |
| Release Decision | candidate; board validation pending |
| LUT6 | {result['lut']} / 21216 |
| FF | {result['ff']} / 42432 |
| Slice | {result['slice']} / 21216 ({100*result['slice']/21216:.2f}%) |
| ERAM20K / DSP | {result['eram']} / 108；{result['dsp']} / 40 |
| Setup WNS / Hold WNS | {result['setup_wns_ns']:+.3f}ns / {result['hold_wns_ns']:+.3f}ns |
| Setup TNS / Hold TNS | {result['setup_tns_ps']}ps / {result['hold_tns_ps']}ps |
| STA coverage | {coverage} |
| Critical warnings | {critical}；新增类型{new_critical}，原始上下文随附 |
| Board Test Status | 待用户烧录；四模式、独立阈值保留、FIFO稳态、长期与光照变化验收均未完成 |

## 数据与配置

配置为18位`{{mode[1:0],edge_threshold[7:0],binary_threshold[7:0]}}`，复位`EDGE/080/130`。K3按`EDGE→ORIGIN→GRAY→BINARY→EDGE`循环；K4短按−10、长按+10，只修改当前模式阈值，10..250饱和。24 MHz源域与MIPI接收域继续使用整包保持+toggle/ack邮箱，不逐位跨域。

四个分支均从AWB后RGB888出发，使用同一27拍对齐窗口；Edge Gaussian/Sobel/NMS/四跳/单帧时间保持始终运行。ORIGIN保持原RGB，GRAY/BINARY按`Y=(77R+150G+29B+128)>>8`逐像素生成，末端选择后才进入原2拍OSD和1拍96→128打包。无新增整帧缓存、反压、中心偏移或DDR/HDMI结构变化。

## 验证与风险

逐像素模型覆盖黑/白/中性灰/红/绿/蓝、RGB随机值、T=10/130/250及Y=T边界；K3/K4与18位CDC原子包测试通过。混合9帧小尺寸流覆盖四模式、提前/同拍SOF、valid间隙、帧内请求变化和帧首/行尾；完整720p×2帧完成460800有效拍、345600打包字逐字节对照。与EDGE_TEMPORAL_V1相比，18个算法/ISP/DDR/HDMI/Logo/引脚/SDC文件SHA保持不变。

STA通过不等于长期硬件稳定；既有FIFO Gray指针覆盖缺口和PHY关键warning风险未修复。任何S计数增长均应阻断正式验收并先检查FIFO/DDR。实板四模式画质、模式/阈值一致性、30分钟与光照变化尚无证据。

回滚：烧录`artifacts/bitstreams/EDGE_TEMPORAL_V1/camera_to_dsi_display.bit`，SHA-256 `14A36D98BC0A1547F84588087D796C14098AD4441CB30B5878D8F81CBADC95C4`。
"""
    (dest / "BUILD_INFO.md").write_text(info, encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("Archived", dest)


if __name__ == "__main__":
    main()
