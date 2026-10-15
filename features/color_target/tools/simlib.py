"""四个自检脚本共用的仿真内核调用。

**为什么单独成文件（复查时发现的缺陷）**：原先四个 runner 各自复制了一份 iverilog /
ModelSim 的探测与调用逻辑，而且把 ModelSim 路径写死成作者本机的
`D:\\altera\\14.1\\modelsim_ase\\win32aloem`。协议 §5.1 明确要求"使用相对路径，不写死
负责人的 D 盘路径"；而且找不到仿真器时原代码只打印一个 `None`，对队友毫无帮助。
这里收敛成一处，并把路径改成可配置。

**仿真器查找顺序**
  Icarus：PATH 上的 `iverilog`/`vvp` → 环境变量 `COLOR_TARGET_IVERILOG_DIR` → `C:\\iverilog\\bin`
  ModelSim：显式 `--msim` → 环境变量 `COLOR_TARGET_MSIM` → 几个常见安装位置
两者都没有时，返回一段说明怎么装/怎么指路的话，而不是沉默或 `None`。
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

IVERILOG_ENV = "COLOR_TARGET_IVERILOG_DIR"
MSIM_ENV = "COLOR_TARGET_MSIM"

# 只作为"最后的顺手一试"，不作为假设：找不到就明确报错并给出指定方法
_COMMON_IVERILOG = [r"C:\iverilog\bin"]
_COMMON_MSIM = [
    r"C:\altera\14.1\modelsim_ase\win32aloem",
    r"D:\altera\14.1\modelsim_ase\win32aloem",
    r"C:\intelFPGA\18.1\modelsim_ase\win32aloem",
    r"C:\intelFPGA_lite\18.1\modelsim_ase\win32aloem",
]


def add_args(ap):
    """给 runner 的 argparse 加上统一的 --sim / --msim。"""
    ap.add_argument("--sim", default="auto", choices=["auto", "iverilog", "modelsim"])
    ap.add_argument("--msim", default=None,
                    help=f"ModelSim 的 win32aloem 目录（未给时查环境变量 {MSIM_ENV}）")
    return ap


def find_iverilog():
    iv, vvp = shutil.which("iverilog"), shutil.which("vvp")
    if iv and vvp:
        return (iv, vvp)
    dirs = []
    if os.environ.get(IVERILOG_ENV):
        dirs.append(os.environ[IVERILOG_ENV])
    dirs += _COMMON_IVERILOG
    for d in dirs:
        iv, vvp = Path(d) / "iverilog.exe", Path(d) / "vvp.exe"
        if iv.exists() and vvp.exists():
            return (str(iv), str(vvp))
    return None


def find_modelsim(root=None):
    cands = []
    if root:
        cands.append(Path(root))
    if os.environ.get(MSIM_ENV):
        cands.append(Path(os.environ[MSIM_ENV]))
    cands += [Path(p) for p in _COMMON_MSIM]
    for c in cands:
        if (c / "vlog.exe").exists() and (c / "vsim.exe").exists():
            return c
    return None


def pick(requested="auto", msim_root=None):
    """返回 (kind, info)。kind ∈ {None, "iverilog", "modelsim"}；kind 为 None 时 info 是说明。"""
    iv, ms = find_iverilog(), find_modelsim(msim_root)
    if requested == "iverilog" and not iv:
        return None, _no_sim("指定了 Icarus，但没找到 iverilog / vvp")
    if requested == "modelsim" and not ms:
        return None, _no_sim("指定了 ModelSim，但没找到 vlog.exe / vsim.exe 所在目录")
    if requested == "iverilog" or (requested == "auto" and iv):
        return "iverilog", iv
    if requested == "modelsim" or (requested == "auto" and ms):
        return "modelsim", ms
    return None, _no_sim("既没找到 Icarus Verilog，也没找到 ModelSim")


def _no_sim(head):
    return (
        f"{head}。请任选其一：\n"
        f"  1) 安装 Icarus Verilog（仓库既有 runner 的默认选择），或用环境变量 "
        f"{IVERILOG_ENV}=<bin 目录> 指定；\n"
        f"  2) 用 --msim <win32aloem 路径>，或用环境变量 {MSIM_ENV} 指定 ModelSim 安装位置。\n"
        f"  说明：本目录的脚本不假设任何人的 D 盘路径（协议 §5.1）。"
    )


def _env_with(root):
    env = dict(os.environ)
    env["PATH"] = f"{root}{os.pathsep}{env.get('PATH', '')}"
    return env


def _build_iverilog(srcs, tb_top, params, vvp_path, cwd):
    iv, _ = find_iverilog()
    cmd = [iv, "-g2005", "-Wall", "-s", tb_top]
    for k, v in params.items():
        cmd.append(f"-P{tb_top}.{k}={v}")
    cmd += ["-o", str(vvp_path)] + [str(s) for s in srcs]
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return None if r.returncode == 0 else f"[iverilog 编译失败]\n{r.stdout}\n{r.stderr}"


def _build_modelsim(srcs, root, cwd):
    exe = lambda n: str(Path(root) / n)
    env = _env_with(root)
    subprocess.run([exe("vlib.exe"), "work"], cwd=cwd, capture_output=True, text=True, env=env)
    r = subprocess.run([exe("vlog.exe"), "-quiet", "-work", "work"] + [str(s) for s in srcs],
                       cwd=cwd, capture_output=True, text=True, env=env)
    return None if r.returncode == 0 else f"[vlog 失败]\n{r.stdout}\n{r.stderr}"


def simulate(srcs, tb_top, params, plusargs, requested="auto", msim_root=None,
             workdir=".", name="sim"):
    """编译并跑一次。返回 (ok, 输出文本, 错误说明)。

    srcs     按 iverilog 顺序给出的源文件（含 tb）
    params   tb 顶层参数覆盖，两端都映射成同名覆盖（iverilog 用 -P，ModelSim 用 -g）
    plusargs 运行时 plusargs，键不带 `+`
    """
    kind, info = pick(requested, msim_root)
    if kind is None:
        return False, "", info
    wd = Path(workdir)
    if kind == "iverilog":
        vvp = wd / f"{name}.vvp"
        err = _build_iverilog(srcs, tb_top, params, vvp, wd)
        if err:
            return False, "", err
        _, vvp_exe = find_iverilog()
        cmd = [vvp_exe, str(vvp)] + [f"+{k}={v}" for k, v in plusargs.items()]
        r = subprocess.run(cmd, cwd=wd, capture_output=True, text=True)
    else:
        err = _build_modelsim(srcs, info, wd)
        if err:
            return False, "", err
        exe = lambda n: str(Path(info) / n)
        cmd = [exe("vsim.exe"), "-c", "-quiet"]
        for k, v in params.items():
            cmd.append(f"-g{k}={v}")
        cmd += [f"work.{tb_top}"] + [f"+{k}={v}" for k, v in plusargs.items()]
        cmd += ["-do", "run -all; quit -f"]
        r = subprocess.run(cmd, cwd=wd, capture_output=True, text=True, env=_env_with(info))
    return True, r.stdout + r.stderr, ""


def make_workdir(prefix):
    """给调用方一个临时工作目录（返回 Path；调用方负责在用完后清理）。"""
    return Path(tempfile.mkdtemp(prefix=prefix))
