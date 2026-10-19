"""Archive a passing EDGE_STYLE_FILL_V2 routed build without overwriting history."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project"
TMP = ROOT / "tmp/edge_style_fill_v2"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default="")
    parser.add_argument("--rejected-reason", default="")
    args = parser.parse_args()
    rejected = bool(args.checkpoint)
    version = (
        f"EDGE_STYLE_FILL_V2_{args.checkpoint}" if rejected else "EDGE_STYLE_FILL_V2"
    )
    tag = (
        "edge-style-fill-v2-r0-build"
        if args.checkpoint == "R0"
        else "edge-style-fill-v2-candidate"
    )
    release = (
        "REJECTED: " + args.rejected_reason
        if rejected
        else "candidate; board validation pending"
    )
    snap = json.loads((TMP / "prebuild.json").read_text())
    rtl = json.loads((TMP / "rtl_results.json").read_text())
    assert any(x["width"] == 1280 and x["height"] == 720
               and x["beats"] == 1152000 and x["packed_words"] == 864000
               for x in rtl["streams"]), "full five-mode 720p regression required"
    units = json.loads((TMP / "unit_results.json").read_text())
    assert len(units) == 5 and all(x["frames"] >= 60 for x in units)
    frozen = json.loads((TMP / "frozen_inputs.json").read_text())
    assert len(frozen["frozen_td_inputs"]) == 65 and frozen["td_options_unchanged"]
    mapping = json.loads((TMP / "RAM_MAPPING.json").read_text())
    assert mapping["source_commit"] == snap["source_commit"] and len(mapping["mapped_eram"]) == 10
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
    assert passed, "STA failed; do not archive as a passing build"
    timing = (phy / "final_timing.rpt").read_text(errors="replace")
    coverage = re.search(r"STA coverage\s*:\s*([^\n]+)", timing)[1].strip()
    critical = sorted(set(re.findall(r"(\w+-\d+) CRITICAL-WARNING", syn_text + phy_text)))
    previous_logs = "\n".join(
        path.read_text(errors="replace")
        for path in (ROOT / "artifacts/bitstreams/EDGE_STYLE_FILL_V1/build_evidence").glob("*.log")
    )
    new_critical = sorted(
        set(critical) - set(re.findall(r"(\w+-\d+) CRITICAL-WARNING", previous_logs))
    )
    result = dict(
        version=version,
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
        additional_pipeline_cycles_from_style_v1=0,
        per_branch_alignment_cycles=27,
        osd_cycles=2,
        pack_cycles=1,
        candidate_eligible=not rejected,
        release_decision=release,
        board_test=(
            "REJECTED; not for board testing"
            if rejected
            else "pending; STYLE appearance, five-mode switching, B/S and 30-minute stability unverified"
        ),
    )
    result["delta_from_style_v1"] = {
        name: result[name] - value
        for name, value in dict(lut=16592, ff=16972, slice=17792, eram=85, dsp=21).items()
    }

    dest = ROOT / "artifacts/bitstreams" / version
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
        "unit_results.json",
        "unit_console.log",
        "model_console.log",
        "frozen_inputs.json",
        "RAM_MAPPING.json",
        "gate_inspect.log",
        "inspect_gate.tcl",
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
    info = f"""# BUILD_INFO — {version}

| 项目 | 实际值 |
|---|---|
| Version / Role | {version} / MAIN |
| Branch | codex/main/edge-style-fill-v2 |
| 实际TD输入源码commit | {snap['source_commit']} |
| Git Tag | {tag} |
| 基线 / PR | EDGE_STYLE_FILL_V1 e17a1af；Draft PR 以 codex/main/edge-style-fill-v1 为 base，不自动合并 |
| Build Time | {build_time} |
| Device / Top / TD | PH1P35MDG324 / design_top_wrapper / Tang Dynasty6.2.168116 |
| 原始bit | {bit} |
| 归档bit | artifacts/bitstreams/{version}/{bit.name} |
| SHA-256 / bytes | {result['bit_sha256']} / {result['bit_size']} |
| Build Result | Synthesis → Physical Design → final Timing Check → bitgen；PASS |
| Release Decision | {release} |
| LUT6 | {result['lut']} / 21216 |
| FF | {result['ff']} / 42432 |
| Slice | {result['slice']} / 21216 ({100*result['slice']/21216:.2f}%) |
| ERAM20K / DSP | {result['eram']} / 108；{result['dsp']} / 40 |
| Setup WNS / Hold WNS | {result['setup_wns_ns']:+.3f}ns / {result['hold_wns_ns']:+.3f}ns |
| Setup TNS / Hold TNS | {result['setup_tns_ps']}ps / {result['hold_tns_ps']}ps |
| STA coverage | {coverage} |
| Critical warnings | {critical}；新增类型{new_critical}，原始上下文随附 |
| Board Test Status | {result['board_test']} |

## 实际功能与验证

V2仅修改STYLE渲染：同色保守均值、9档共享明度/低色度中性保护、相干亮度暗侧描边。
仍为5拍局部STYLE与原27拍对齐窗口、2拍OSD、1拍打包；端到端新增0拍。
其余65个TD输入与V1一致；原四模式、EDGE_TEMPORAL、Sensor/ISP、按键/OSD、DDR/HDMI、PLL/SDC冻结。
模型、RTL结果与实板反馈边界见 docs/EDGE_STYLE_FILL_V2_DESIGN.md / REPORT.md / BOARD_TEST.md。
历史FIFO/Gray约束风险未修复，V2真实画质待用户上板。
回滚：artifacts/bitstreams/EDGE_STYLE_FILL_V1/camera_to_dsi_display.bit，
SHA256 B4FBB61FABD6A510B26EEC6DAD4D950FF8A3D2B6F561753D5611B334274B336E。

"""
    (dest / "BUILD_INFO.md").write_text(info, encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("Archived", dest)


if __name__ == "__main__":
    main()
