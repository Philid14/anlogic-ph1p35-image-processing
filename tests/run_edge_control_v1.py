"""Checkpoint A-D evidence: independent image model, actual packer and ISP route.

Python 3 + Icarus; all vectors/executables stay in temporary directories.
Camera/DDR/HDMI IP and physical board behavior are outside this unit test.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
HDL = ROOT / "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source"
spec = importlib.util.spec_from_file_location("edge_reference", ROOT / "tests/run_edge_v1.py")
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
IV = shutil.which("iverilog") or "C:/iverilog/bin/iverilog.exe"
VVP = shutil.which("vvp") or "C:/iverilog/bin/vvp.exe"


def frozen():
    manifest = json.loads((ROOT / "tests/edge_control_frozen_manifest.json").read_text(encoding="utf-8"))
    for kind in ("frozen_main", "read_only_reference", "hardware_sources"):
        for name, digest in manifest[kind].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
        print(f"PASS {kind}: {len(manifest[kind])} hashes unchanged", flush=True)
    top = (HDL / "design_top_wrapper.v").read_text(encoding="utf-8")
    assert re.search(r"assign\s+S_ae_req\s*=\s*1'b0\s*;", top)
    assert re.search(r"assign\s+S_ae\s*=\s*16'd1990\s*;", top)
    assert re.search(r"assign\s+S_ag\s*=\s*16'd0\s*;", top)
    assert "ae_set u_ae_set" not in top
    assert ".keys_n(I_button)" in top and ".I_ae_req(S_ae_req)" in top
    assert ".requested_config(S_edge_requested_config)" in top
    assert ".received_config(S_edge_received_config)" in top
    assert ".I_edge_config   (S_edge_received_config)" in top
    adc = (HDL.parent / "constraints_source/pin.adc").read_text(encoding="utf-8")
    assert re.search(r"I_button\[0\].*LOCATION = B9", adc)
    assert re.search(r"I_button\[1\].*LOCATION = C7", adc)
    baseline_adc = subprocess.check_output(["git", "show", "edge-v1-candidate:" +
        (HDL.parent / "constraints_source/pin.adc").relative_to(ROOT).as_posix()], cwd=ROOT).decode()
    assert re.sub(r"I_button\[0\].*?LOCATION = B9", "I_button[0] }\t\t\t{ LOCATION = N2", adc).replace(
        "LOCATION = C7", "LOCATION = J14") == baseline_adc
    assert "DEBOUNCE_CYCLES = 480000" in (HDL / "edge_key_control.v").read_text()
    assert "LONG_CYCLES = 16800000" in (HDL / "edge_key_control.v").read_text()
    print("PASS actual Top sensor isolation, CDC wiring, key-only ADC change, production timers", flush=True)


def simulate(directory, top, sources, params=(), plus=()):
    exe = directory / (top + ".vvp")
    command = [IV, "-g2012", "-Wall", "-s", top, *params, "-o", str(exe), *map(str, sources)]
    compiled = subprocess.run(command, capture_output=True, text=True)
    if compiled.returncode:
        raise AssertionError(compiled.stdout + compiled.stderr)
    run = subprocess.run([VVP, str(exe), *plus], capture_output=True, text=True)
    if run.returncode or "FAIL" in run.stdout or "PASS" not in run.stdout:
        raise AssertionError(run.stdout + run.stderr)
    print(run.stdout.strip(), flush=True)
    return run.stdout


def glyph_table():
    # Read the frozen font as glyph data; text content/decimal/pixel selection
    # is independently calculated here, not by the RTL OSD implementation.
    text = (HDL / "osd_char_lib.v").read_text(encoding="utf-8")
    names = dict(re.findall(r"localparam\s+(CHAR_\w+)\s*=\s*8'h([0-9a-f]+)", text))
    result = {}
    for name, code in names.items():
        match = re.search(r"\b" + name + r": begin(.*?)endcase", text, re.S)
        if match:
            result[int(code, 16)] = {int(row): int(bits, 16) for row, bits in
                re.findall(r"4'd(\d+): O_row_bits = 16'h([0-9a-f]+)", match.group(1))}
    assert all(ord(c) in result for c in "MODEORIGINTHRESHOLD:0123456789")
    return result


def overlay(pixels, x, y, mode, threshold, font):
    out = []
    for lane, rgb in enumerate(pixels):
        px = x + lane
        if 800 <= px < 1248 and 16 <= y < 88:
            local_y = y - 16
            if local_y < 32:
                text = "MODE: EDGE    " if mode else "MODE: ORIGIN  "
                row = local_y // 2
            elif local_y >= 40:
                text = f"THRESHOLD: {threshold:03d}"
                row = (local_y - 40) // 2
            else:
                text, row = " " * 14, 0
            col, offset = divmod(px - 800, 32)
            bits = font.get(ord(text[col]), {}).get(row, 0)
            rgb = (255, 255, 0) if bits & (1 << (15 - offset // 2)) else (16, 16, 16)
        out.append(rgb)
    return bytes(c for pixel in out for c in pixel)


def vectors(directory, width, height, full):
    configs = [(1, 80, "threshold"), (1, 70, "threshold"), (1, 60, "threshold"),
               (0, 80, "channels"), (1, 90, "threshold"), (1, 100, "threshold"),
               (1, 10, "random"), (1, 250, "diagonal"), (0, 10, "uniform"),
               (1, 40, "threshold"), (0, 250, "random")]
    if full:
        configs = [(1, 80, "threshold"), (0, 80, "channels"),
                   (1, 20, "threshold"), (0, 250, "random")]
    stimulus, packed = directory / "stim.txt", directory / "pack.txt"
    font = glyph_table()
    beats, words = 0, 0
    active = (1 << 8) | 80
    requested = active
    with stimulus.open("w", encoding="ascii") as sf, packed.open("w", encoding="ascii") as pf:
        def cycle(v=0, u=0, l=0, rgb=0, expected=b"\0" * 12, request=None):
            nonlocal requested
            if request is not None:
                requested = request
            sf.write(f"{v} {u} {l} {requested:03x} {rgb:024x} {expected.hex()}\n")

        for frame, (mode, threshold, pattern) in enumerate(configs):
            image = reference.scene(width, height, pattern, 13)  # same scene for threshold sweep
            edge = reference.spatial_edges(image, threshold)
            active = (mode << 8) | threshold
            early = frame % 2 == 0
            if early:
                cycle(u=1, request=active)
                for _ in range(60):
                    cycle()
            for y in range(height):
                row_bytes = bytearray()
                for x in range(0, width, 4):
                    if not early and y == 0 and x == 0:
                        requested = active
                    # Fast request churn within a frame must not affect data
                    # or either status line. Even the first invalid SOF's
                    # config must be carried through the branch pipeline.
                    if x % 20 == 4:
                        requested = (((frame + x) & 1) << 8) | (10 + ((x + y) % 25) * 10)
                    pixels = image[y][x:x+4] if not mode else [(e, e, e) for e in edge[y][x:x+4]]
                    output = overlay(pixels, x, y, mode, threshold, font)
                    rgb = int.from_bytes(bytes(c for pixel in image[y][x:x+4] for c in pixel), "big")
                    cycle(1, int(not early and y == 0 and x == 0), int(x == width-4), rgb, output)
                    row_bytes.extend(output)
                    beats += 1
                for off in range(0, len(row_bytes), 16):
                    pf.write(row_bytes[off:off+16].hex()+"\n"); words += 1
                for _ in range(3 + y % 5):
                    cycle()
            # No extra frame drain: next SOF may commit while prior pixels
            # remain in the 7-stage chain. Each beat retains its config.

        if not full:
            # Partial frame then SOF recovery, including a malformed early
            # tlast. No assumption that tlast means end-of-frame.
            cycle(u=1, request=(1 << 8) | 80)
            for _ in range(10): cycle()
            for x in range(4):
                cycle(1, 0, int(x == 1), (1 << 96)-1); beats += 1
            for _ in range(3):pf.write("0"*32+"\n"); words += 1
            for _ in range(4):cycle()
            cycle(u=1, request=(1 << 8) | 10)
            for _ in range(60):cycle()
            for y in range(height):
                row = bytearray()
                for x in range(0, width, 4):
                    out=overlay([(0,0,0)]*4,x,y,1,10,font)
                    cycle(1,0,int(x==width-4),int.from_bytes(b"\xa0"*12,"big"),out)
                    row.extend(out);beats += 1
                for off in range(0,len(row),16):pf.write(row[off:off+16].hex()+"\n");words += 1
                for _ in range(4):cycle()
    return stimulus, packed, words, beats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    frozen()
    with tempfile.TemporaryDirectory(prefix="edge-control-units-") as temporary:
        d=Path(temporary)
        common=[ROOT/"tests/tb_edge_control_keys.v",HDL/"edge_key_control.v",HDL/"edge_config_cdc.v"]
        simulate(d,"tb_edge_control_keys",common)
        simulate(d,"tb_edge_control_mailbox",common)
        sensor=[ROOT/"tests/tb_edge_control_sensor.v",HDL/"edge_key_control.v"]
        sensor += [HDL/"uics500_cfg"/n for n in ("uicfgcs500_720p.v","uics500reg_720p60.v","uics500regAE.v","SC500GainTbl.v")]
        simulate(d,"tb_edge_control_sensor",sensor)
        simulate(d,"tb_edge_control_decimal",[ROOT/"tests/tb_edge_control_decimal.v",HDL/"edge_status_osd.v",HDL/"osd_char_lib.v"])
    cases=[(64,16,False),(1280,96,False)]
    if args.full:cases.append((1280,720,True))
    for width,height,full in cases:
        with tempfile.TemporaryDirectory(prefix="edge-control-stream-") as temporary:
            d=Path(temporary);stim,packed,words,beats=vectors(d,width,height,full)
            sources=[ROOT/"tests/tb_edge_control_stream.v",HDL/"isp/edge_control_stream.v",
                HDL/"isp/edge_detect_96.v",HDL/"edge_status_osd.v",HDL/"osd_char_lib.v",
                HDL/"data_96bit_to_128bit.v",HDL/"isp/isp_top.v",
                HDL/"isp/data128_96/data128_96.v",ROOT/"tests/isp_boundary_stubs.v"]
            result=simulate(d,"tb_edge_control_stream",sources,
                [f"-Ptb_edge_control_stream.WIDTH={width}",f"-Ptb_edge_control_stream.HEIGHT={height}"],
                [f"+STIM={stim.as_posix()}",f"+PACK={packed.as_posix()}",f"+WORDS={words}"])
            assert f"valid_beats={beats} " in result
    frozen()
    print("PASS EDGE_CONTROL_V1 checkpoints A-D; full board/IP validation pending",flush=True)


if __name__=="__main__":main()
