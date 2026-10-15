"""color_target_overlay 的独立自检：生成逐像素激励 -> 仿真 -> 与参考模型比对。

只验证模块本身。纯组合模块，因此激励是"像素 + 整帧结果"的组合，不需要时钟。

用法：
    python features/color_target/run_color_target_overlay.py
    python features/color_target/run_color_target_overlay.py --sim modelsim
"""

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RTL = HERE / "rtl"
TB = HERE / "tb"
MSIM = Path(r"D:\altera\14.1\modelsim_ase\win32aloem")
TB_NAME = "tb_color_target_overlay"
MOD_NAME = "color_target_overlay"   # tb 里 $display 用的字样


def load_model():
    spec = importlib.util.spec_from_file_location(
        "ref_ct_ov", HERE / "model" / "ref_color_target_overlay.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# (名称, 结果参数, 叠加参数覆盖)
def build_cases():
    def c(name, **kw):
        return (name, kw)
    return [
        c("no_result", present=0, xmin=100, xmax=299, ymin=80, ymax=199, cx=199, cy=139),
        c("result_invalid", rv=0, present=1, xmin=100, xmax=299, ymin=80, ymax=199,
          cx=199, cy=139),
        c("box_and_cross_basic", present=1, xmin=100, xmax=299, ymin=80, ymax=199,
          cx=199, cy=139),
        c("box_at_origin", present=1, xmin=0, xmax=7, ymin=0, ymax=5, cx=3, cy=2),
        c("box_at_far_corner", present=1, xmin=1272, xmax=1279, ymin=714, ymax=719,
          cx=1275, cy=716),
        c("box_smaller_than_thick", present=1, xmin=10, xmax=11, ymin=10, ymax=11,
          cx=10, cy=10),
        c("cross_at_edge", present=1, xmin=0, xmax=31, ymin=0, ymax=31, cx=0, cy=0),
        c("degenerate_single_pixel_box", present=1, xmin=40, xmax=40, ymin=40, ymax=40,
          cx=40, cy=40),
        c("thick_cross", present=1, xmin=100, xmax=299, ymin=80, ymax=199, cx=199, cy=139,
          ov={"cross_thick": 3}),
        c("thick_box", present=1, xmin=100, xmax=299, ymin=80, ymax=199, cx=199, cy=139,
          ov={"box_thick": 1}),
    ]


def write_stim(path, rows):
    with open(path, "w", encoding="ascii") as f:
        for r in rows:
            f.write("%d %d %d %d %d %d %d %d %d %d %d\n" % r)


def compile_iverilog(tmp, params):
    iv = shutil.which("iverilog") or "C:/iverilog/bin/iverilog.exe"
    if not Path(iv).exists():
        return None
    cmd = [iv, "-g2005", "-Wall", "-s", TB_NAME]
    for k, v in params.items():
        cmd.append(f"-P{TB_NAME}.{k}={v}")
    cmd += ["-o", str(tmp / "ov.vvp"), str(TB / "tb_color_target_overlay.v"),
            str(RTL / "color_target_overlay.v")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return "iverilog" if r.returncode == 0 else f"[iverilog 编译失败]\n{r.stdout}\n{r.stderr}"


def compile_modelsim(tmp, params):
    if not MSIM.exists():
        return None
    exe = lambda n: str(MSIM / n)
    env = dict(os.environ)
    env["PATH"] = f"{MSIM};{env.get('PATH','')}"
    subprocess.run([exe("vlib.exe"), "work"], cwd=tmp, capture_output=True, text=True, env=env)
    r = subprocess.run([exe("vlog.exe"), "-quiet", "-work", "work",
                        str(RTL / "color_target_overlay.v"),
                        str(TB / "tb_color_target_overlay.v")],
                       cwd=tmp, capture_output=True, text=True, env=env)
    return "modelsim" if r.returncode == 0 else f"[vlog 失败]\n{r.stdout}\n{r.stderr}"


def run_sim(sim, tmp, params, stim, outp):
    if sim == "iverilog":
        vvp = shutil.which("vvp") or "C:/iverilog/bin/vvp.exe"
        cmd = [vvp, str(tmp / "ov.vvp"), f"+STIM={stim.as_posix()}", f"+OUT={outp.as_posix()}"]
        r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
    else:
        exe = lambda n: str(MSIM / n)
        env = dict(os.environ)
        env["PATH"] = f"{MSIM};{env.get('PATH','')}"
        cmd = [exe("vsim.exe"), "-c", "-quiet"]
        for k, v in params.items():
            cmd.append(f"-g{k}={v}")
        cmd += [f"work.{TB_NAME}", f"+STIM={stim.as_posix()}", f"+OUT={outp.as_posix()}",
                "-do", "run -all; quit -f"]
        r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, env=env)
    return r.stdout + r.stderr


def symmetry_violations(rows, got, cx, cy, arm, pad=2):
    """**不依赖参考模型**的独立断言：中心附近的覆盖图案必须 180 度旋转对称。

    为什么需要它：模型是照着同一套设计写的，若 RTL 与模型"一起错"，逐行对拍永远一致。
    本题就发生过一次——十字线宽原本只向一侧生长（横臂落在 cy..cy+T-1），模型也照此实现，
    于是对拍全绿，直到人工复查才发现视觉中心偏离了模块对外报告的 center_*。
    这里改用与实现无关的不变量：以 (cx,cy) 为中心，点 (cx+dx, cy+dy) 与 (cx-dx, cy-dy)
    必须同为覆盖或同为不覆盖。
    """
    if cx < arm + pad or cy < arm + pad or cx > 1279 - (arm + pad) or cy > 719 - (arm + pad):
        return []          # 贴边时会被裁掉，对称性不成立，跳过
    cov = {(r[1], r[2]): (1 if v else 0) for r, v in zip(rows, got)}
    bad = []
    for dx in range(-pad, pad + 1):
        for dy in range(-pad, pad + 1):
            a = cov.get((cx + dx, cy + dy))
            b = cov.get((cx - dx, cy - dy))
            if a is not None and b is not None and a != b:
                bad.append((dx, dy, a, b))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", default="auto", choices=["auto", "iverilog", "modelsim"])
    args = ap.parse_args()

    model = load_model()
    total = passed = 0
    for name, kw in build_cases():
        ov_p = dict(model.OVERLAY_DEFAULTS, **kw.get("ov", {}))
        res = dict(rv=kw.get("rv", 1), present=kw.get("present", 1),
                   xmin=kw.get("xmin", 0), xmax=kw.get("xmax", 0),
                   ymin=kw.get("ymin", 0), ymax=kw.get("ymax", 0),
                   cx=kw.get("cx", 0), cy=kw.get("cy", 0))
        xs, ys = model.overlay_window(res["xmin"], res["xmax"], res["ymin"], res["ymax"],
                                      res["cx"], res["cy"])
        # 额外加几个远离目标的像素，确认"框外不覆盖"
        xs = xs + [1279, 0]
        ys = ys + [719, 0]
        rows = [(1, x, y, res["rv"], res["present"], res["xmin"], res["xmax"],
                 res["ymin"], res["ymax"], res["cx"], res["cy"])
                for y in sorted(set(ys)) for x in sorted(set(xs))]
        want = [model.overlay_pixel(x, y, res["rv"], res["present"], res["xmin"],
                                    res["xmax"], res["ymin"], res["ymax"], res["cx"],
                                    res["cy"], ov_p) for (_p, x, y, *_r) in rows]

        total += 1
        params = dict(XW=11, YW=10, BOX_THICK=ov_p["box_thick"], BOX_RGB=ov_p["box_rgb"],
                      CROSS_ARM=ov_p["cross_arm"], CROSS_THICK=ov_p["cross_thick"],
                      CROSS_RGB=ov_p["cross_rgb"])
        with tempfile.TemporaryDirectory(prefix="ctov-") as td:
            tmp = Path(td)
            stim, outp = tmp / "stim.txt", tmp / "dut.txt"
            write_stim(stim, rows)
            sim = args.sim
            if sim == "auto":
                sim = compile_iverilog(tmp, params) or compile_modelsim(tmp, params)
            else:
                sim = compile_iverilog(tmp, params) if sim == "iverilog" \
                      else compile_modelsim(tmp, params)
            if sim not in ("iverilog", "modelsim"):
                print(sim)
                return 2
            out = run_sim(sim, tmp, params, stim, outp)
            # 注意匹配的是 tb 里 $display 的实际字样（模块名），不是 tb 文件名
            if "FAIL" in out or f"PASS {MOD_NAME}" not in out:
                print(f"FAIL  {name}  [仿真台]\n      " + out.strip().replace("\n", "\n      "))
                continue

            got = []
            if outp.exists():
                for line in outp.read_text().splitlines():
                    if line.strip():
                        v, rgb = line.split()
                        got.append(int(rgb, 16) if int(v) else 0)
            if got != want:
                bad = [(rows[i], got[i], want[i]) for i in range(min(len(got), len(want)))
                       if got[i] != want[i]]
                print(f"FAIL  {name}  [与模型不符]  {len(bad)}/{len(want)} 像素不同")
                for row, g, w in bad[:6]:
                    print(f"      像素 x={row[1]} y={row[2]}: got=0x{g:06x} want=0x{w:06x}")
                continue
            # 与实现无关的不变量：中心附近的覆盖图案必须 180 度旋转对称。
            # 这一条能抓到"RTL 与模型一起错"的缺陷，逐行对拍抓不到。
            if res["present"] and res["rv"]:
                sym = symmetry_violations(rows, got, res["cx"], res["cy"], ov_p["cross_arm"])
                if sym:
                    print(f"FAIL  {name}  [对称性不变量]  {len(sym)} 处不对称")
                    for dx, dy, a, b in sym[:6]:
                        print(f"      ({res['cx']+dx},{res['cy']+dy})={a} 与 "
                              f"({res['cx']-dx},{res['cy']-dy})={b} 不一致")
                    continue
            passed += 1
            print(f"PASS  {name}  (pixels={len(want)})")

    print(f"\n{passed}/{total} 用例通过  [sim={args.sim}]")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
