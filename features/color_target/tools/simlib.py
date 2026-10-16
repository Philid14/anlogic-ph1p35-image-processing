"""六个自检脚本共用的仿真内核调用。

**为什么单独成文件（复查时发现的缺陷）**：原先四个 runner 各自复制了一份 iverilog /
ModelSim 的探测与调用逻辑，而且把 ModelSim 路径写死成作者本机的
`D:\\altera\\14.1\\modelsim_ase\\win32aloem`。协议 §5.1 明确要求"使用相对路径，不写死
负责人的 D 盘路径"；而且找不到仿真器时原代码只打印一个 `None`，对队友毫无帮助。
这里收敛成一处，并把路径改成**显式指定**。

**查找顺序（刻意保持显式）**
  Icarus：PATH 上的 `iverilog`/`vvp` → 环境变量 `COLOR_TARGET_IVERILOG_DIR`
          → `C:\\iverilog\\bin`
  ModelSim：`--msim <win32aloem 路径>` → 环境变量 `COLOR_TARGET_MSIM`
两者都没有时，返回一段说明怎么装/怎么指路的话，而不是沉默或 `None`。

**为什么不给 ModelSim 列一串"常见安装位置"**：那种列表看起来就是在猜测别人的磁盘布局，
一旦命中一个陈旧安装还会静默用错版本。ModelSim 只认显式指定，代价是设一次环境变量，
换来确定性。`C:\\iverilog\\bin` 保留是因为**仓库既有的 runner 本来就这么写**
（`shutil.which("iverilog") or "C:/iverilog/bin/iverilog.exe"`），属于仓库约定而非个人路径。
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

IVERILOG_ENV = "COLOR_TARGET_IVERILOG_DIR"
MSIM_ENV = "COLOR_TARGET_MSIM"

# 与仓库既有 runner 的约定一致（不是某个人的机器布局）
_IVERILOG_FALLBACK = r"C:\iverilog\bin"

_ANNOUNCED = set()


def add_args(ap):
    """给 runner 的 argparse 加上统一的 --sim / --msim。"""
    ap.add_argument("--sim", default="auto", choices=["auto", "iverilog", "modelsim"])
    ap.add_argument("--msim", default=None,
                    help=f"ModelSim 的 win32aloem 目录（未给时查环境变量 {MSIM_ENV}）")
    return ap


def find_iverilog():
    iv, vvp = shutil.which("iverilog"), shutil.which("vvp")
    if iv and vvp:
        return (iv, vvp, "PATH")
    dirs = []
    if os.environ.get(IVERILOG_ENV):
        dirs.append((os.environ[IVERILOG_ENV], f"环境变量 {IVERILOG_ENV}"))
    dirs.append((_IVERILOG_FALLBACK, "仓库既有 runner 的默认位置"))
    for d, why in dirs:
        iv, vvp = Path(d) / "iverilog.exe", Path(d) / "vvp.exe"
        if iv.exists() and vvp.exists():
            return (str(iv), str(vvp), why)
    return None


def find_modelsim(root=None):
    cands = []
    if root:
        cands.append((Path(root), "--msim 指定"))
    if os.environ.get(MSIM_ENV):
        cands.append((Path(os.environ[MSIM_ENV]), f"环境变量 {MSIM_ENV}"))
    for c, why in cands:
        if (c / "vlog.exe").exists() and (c / "vsim.exe").exists():
            return (c, why)
    return None


def pick(requested="auto", msim_root=None):
    """返回 (kind, info)。kind ∈ {None, "iverilog", "modelsim"}；kind 为 None 时 info 是说明。

    info 在成功时是 (路径, 来源说明) —— 调用方据此打印"用的是哪个、从哪找到的"。
    """
    iv, ms = find_iverilog(), find_modelsim(msim_root)
    if requested == "iverilog" and not iv:
        return None, _no_sim("指定了 Icarus，但没找到 iverilog / vvp")
    if requested == "modelsim" and not ms:
        return None, _no_sim("指定了 ModelSim，但没找到 vlog.exe / vsim.exe 所在目录")
    if requested == "iverilog" or (requested == "auto" and iv):
        return "iverilog", (iv[0], iv[2])
    if requested == "modelsim" or (requested == "auto" and ms):
        return "modelsim", ms
    return None, _no_sim("既没找到 Icarus Verilog，也没找到 ModelSim")


def _no_sim(head):
    return (
        f"{head}。请任选其一：\n"
        f"  1) 安装 Icarus Verilog（仓库既有 runner 的默认选择），或用环境变量 "
        f"{IVERILOG_ENV}=<bin 目录> 指定；\n"
        f"  2) 用 --msim <win32aloem 路径>，或用环境变量 {MSIM_ENV} 指定 ModelSim 安装位置。\n"
        f"  说明：本目录的脚本不猜任何人的安装位置，也不写死 D 盘路径（协议 §5.1）。"
    )


def _env_with(root):
    env = dict(os.environ)
    env["PATH"] = f"{root}{os.pathsep}{env.get('PATH', '')}"
    return env


def _build_iverilog(srcs, tb_top, params, vvp_path, cwd):
    iv = find_iverilog()[0]
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
    params   tb 顶层参数覆盖（iverilog 用 -P，ModelSim 用 -g）
    plusargs 运行时 plusargs，键不带 `+`
    """
    kind, info = pick(requested, msim_root)
    if kind is None:
        return False, "", info
    if kind not in _ANNOUNCED:
        _ANNOUNCED.add(kind)
        where = info[1] if isinstance(info, tuple) else info[1]
        path = info[0] if isinstance(info, tuple) else info[0]
        print(f"[sim] 使用 {kind}：{path}（来源：{where}）")
    wd = Path(workdir)
    if kind == "iverilog":
        vvp = wd / f"{name}.vvp"
        err = _build_iverilog(srcs, tb_top, params, vvp, wd)
        if err:
            return False, "", err
        cmd = [find_iverilog()[1], str(vvp)] + [f"+{k}={v}" for k, v in plusargs.items()]
        r = subprocess.run(cmd, cwd=wd, capture_output=True, text=True)
    else:
        root = info[0]
        err = _build_modelsim(srcs, root, wd)
        if err:
            return False, "", err
        exe = lambda n: str(Path(root) / n)
        cmd = [exe("vsim.exe"), "-c", "-quiet"]
        for k, v in params.items():
            cmd.append(f"-g{k}={v}")
        cmd += [f"work.{tb_top}"] + [f"+{k}={v}" for k, v in plusargs.items()]
        cmd += ["-do", "run -all; quit -f"]
        r = subprocess.run(cmd, cwd=wd, capture_output=True, text=True, env=_env_with(root))
    return True, r.stdout + r.stderr, ""


def make_workdir(prefix):
    """给调用方一个临时工作目录（返回 Path；调用方负责在用完后清理）。"""
    return Path(tempfile.mkdtemp(prefix=prefix))
