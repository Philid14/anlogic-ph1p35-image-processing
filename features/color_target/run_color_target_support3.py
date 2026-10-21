"""Independent set oracle vs public RTL ports, with default-bypass assertions.

No frame buffering is added to the product; this host test can hold full frames.
"""
import argparse
import hashlib
import importlib.util
import json
import random
import tempfile
from pathlib import Path

from model.ref_color_target_support3 import selfcheck, support3, words

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("simlib", HERE / "tools" / "simlib.py")
simlib = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simlib)


def cases(w, h, exhaustive):
    yield "empty", set()
    yield "solid", {(x, y) for y in range(h) for x in range(w)}
    yield "isolated_last_lane", {(w - 1, h - 1)}
    yield "edges_and_lanes", {(x, y) for y in range(h) for x in range(w)
                              if x in (0, 3, 4, w - 1) or y in (0, h - 1)}
    yield "diagonal", {(x, x % h) for x in range(w)}
    yield "cluster", {(x, y) for x in range(min(w, 2)) for y in range(min(h, 2))}
    rng = random.Random(731 + w * 1009 + h)
    for i in range(8 if w < 1280 else 1):
        yield f"random_{i}", {(x, y) for y in range(h) for x in range(w)
                              if rng.random() < (0.08, 0.35, 0.75)[i % 3]}
    if exhaustive:
        for phase in range(4):
            for bits in range(512):
                yield f"neighborhood_{phase}_{bits}", {(4 + phase + i % 3, 1 + i // 3)
                                                      for i in range(9) if bits & (1 << i)}


def run(w, h, args, exhaustive=False):
    # rows: reset, valid, mask, x, y, sof, eol, eof, session, frame, abort.
    rows, epochs, epoch = [], [], {"expected": [], "cut": False}
    fault_cycles = set()
    eof_cycles = {}
    rng = random.Random(1417 + w + h)
    names = []
    def idle(n=1):
        # Non-valid bus noise must neither advance the filter nor trigger errors.
        for _ in range(n):
            rows.append((1, 0, 15, w-4, h-1, 1, 1, 1, 987, 654, 1))
    def reset(cut=False):
        nonlocal epoch
        epoch["cut"] = cut
        epochs.append(epoch)
        rows.append((0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
        epoch = {"expected": [], "cut": False}
    def frame(points, sid, fid, gaps=False, abort_at=None, fault=None):
        filtered = support3(points)
        assert filtered <= points
        for index, (x, y, mask) in enumerate(words(points, w, h)):
            first = x == 0 and y == 0
            last = x == w-4 and y == h-1
            inp = [1, 1, mask, x, y, int(first), int(x == w-4), int(last), sid, fid,
                   int(index == abort_at)]
            if fault and index == 1:
                if fault == "id": inp[9] ^= 1
                elif fault == "eol": inp[6] ^= 1
                elif fault == "xy": inp[3] ^= 1
                fault_cycles.add(len(rows))
            if last: eof_cycles[(sid, fid)] = len(rows)
            rows.append(tuple(inp))
            if gaps and not last: idle(rng.randrange(4))
        for x, y, mask in words(filtered, w, h):
            epoch["expected"].append((mask, x, y, int(x == 0 and y == 0),
                                      int(x == w-4), int(x == w-4 and y == h-1), sid, fid,
                                      bool(abort_at is not None or fault)))
    reset()
    for fid, (name, points) in enumerate(cases(w, h, exhaustive)):
        names.append(name)
        # Consecutive IDs cross frame-id wrap and a session change.
        frame(points, 17 + fid // 3, (0xfffffffd + fid) & 0xffffffff,
              gaps=(fid % 3 == 2))
    idle(w//4 + 7)  # final row must drain without a future valid pixel
    reset()
    # Abort propagation and sticky protocol failures; recovery at complete-frame
    # boundary is allowed, but a truncated stream is recovered only by reset.
    for fid in range(3):
        frame({(x, y) for x in range(w) for y in range(h)}, 91, fid,
              gaps=True, abort_at=(0, w*h//8, w*h//4-1)[fid])
    idle(w//4 + 7)
    if w*h//4 > 1:
        for fault_i, fault in enumerate(("id", "eol", "xy")):
            reset()
            frame(set(), 92, fault_i, fault=fault)
            frame(set(), 93, fault_i)  # invalid frame must not poison next one
            idle(w//4 + 7)
    reset()
    # Reset while RAM has stale ones and while a word is pending.
    for x, y, mask in words({(x, y) for y in range(h) for x in range(w)}, w, h):
        rows.append((1, 1, mask, x, y, int(x == 0 and y == 0), int(x == w-4),
                     int(x == w-4 and y == h-1), 100, 1, 0))
        if y == min(1, h-1): break
    reset(cut=True)
    frame(set(), 101, 1)
    idle(w//4 + 7)
    # Reset in autonomous tail flush: compare the observed prefix, allow only
    # explicit reset to discard the remaining words of this frame.
    frame({(x, y) for y in range(h) for x in range(w)}, 102, 1)
    idle(max(1, w//8))
    reset(cut=True)
    frame(set(), 103, 1)
    idle(w//4 + 7)
    epochs.append(epoch)

    with tempfile.TemporaryDirectory(prefix="ct_support3_") as td:
        td = Path(td)
        stim, out = td / "stim.txt", td / "out.txt"
        with stim.open("w", encoding="ascii") as f:
            for r in rows:
                f.write(f"{r[0]} {r[1]} {r[2]:x} " + " ".join(map(str, r[3:])) + "\n")
        srcs = [args.rtl or HERE / "rtl/color_target_support3.v"]
        if args.gate_netlist:
            vendor = args.td_sim_dir
            assert vendor and vendor.is_dir(), "--gate-netlist requires --td-sim-dir <TD/sim_release>"
            srcs += [vendor / "common" / f for f in
                     ("al_map_lut.v", "al_map_seq.v", "al_phy_glbl.v")]
            srcs += [vendor / "ph1p" / f for f in
                     ("ph1p_phy_gsr.v", "ph1p_phy_config_v2.v", "ph1p_phy_eram_v2.v",
                      "ph1p_phy_hd_pad.v", "ph1p_phy_hr_pad_v2.v")]
            srcs += [args.gate_netlist]
        srcs += [HERE / "tb/tb_color_target_support3.v"]
        ok, transcript, err = simlib.simulate(
            srcs, "tb_color_target_support3",
            {"WIDTH": w, "HEIGHT": h, "GATE": int(bool(args.gate_netlist))}, {"STIM": stim, "OUT": out},
            args.sim, args.msim, td, "support3")
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.with_suffix(f".{w}x{h}.sim.log").write_text(err+transcript, encoding="utf-8")
        if not ok or "FAIL" in transcript or "PASS support3" not in transcript:
            raise AssertionError(err + "\n" + transcript)
        actual = out.read_text(encoding="ascii").splitlines()
        assert len(actual) == len(rows), (len(actual), len(rows))
        epoch_i, expect_i, sticky, checked, output_eofs = 0, 0, False, 0, {}
        first_output, last_output = {}, {}
        digest = hashlib.sha256()
        for cycle, (line, row) in enumerate(zip(actual, rows)):
            fields = line.split()
            assert len(fields) == 12 and int(fields[0]) == cycle, line
            assert not any("x" in v.lower() or "z" in v.lower() for v in fields), line
            ov = int(fields[1]); mask = int(fields[2], 16)
            vals = list(map(int, fields[3:]))
            ox, oy, os, ol, oe, sid, fid, abort, error = vals
            if not row[0]:
                ep = epochs[epoch_i]
                assert ep["cut"] or expect_i == len(ep["expected"]), (w,h,"reset lost output",expect_i)
                epoch_i += 1; expect_i = 0; sticky = False
                assert not ov and not error
                continue
            sticky |= cycle in fault_cycles
            assert error == sticky, (cycle, "protocol flag", error, sticky)
            if not ov: continue
            ep = epochs[epoch_i]
            # A reset-discarded partial frame without a complete oracle may
            # emit an arbitrary-length prefix before reset. No cross-reset tail
            # is accepted, since the next epoch starts from its exact first word.
            if not ep["expected"] and ep["cut"]: continue
            assert expect_i < len(ep["expected"]), (w,h,cycle,"extra output")
            exp = ep["expected"][expect_i]
            got = (mask, ox, oy, os, ol, oe, sid, fid)
            assert got == exp[:8], (w,h,cycle,expect_i,got,exp)
            if oe:
                assert bool(abort) == exp[8], (cycle,"EOF abort",abort,exp[8])
                output_eofs[(sid,fid)] = cycle
                assert cycle - eof_cycles[(sid,fid)] == w//4 + 2, (cycle,"tail deadline")
            if not exp[8]: assert not abort, (cycle,"unexpected abort")
            first_output.setdefault((sid,fid),cycle)
            last_output[(sid,fid)] = cycle
            digest.update((str(got)+"\n").encode("ascii"))
            expect_i += 1; checked += 1
        assert expect_i == len(epochs[-1]["expected"]), (w,h,"missing final output")
        # The first two frames are unbroken input bursts. Output must also be
        # one word every clock, including their boundary and both EOF lanes.
        keys = [(17,0xfffffffd), (17,0xfffffffe)]
        for key in keys:
            assert last_output[key]-first_output[key]+1 == w*h//4, (key,"throughput")
        assert first_output[keys[1]] == last_output[keys[0]]+1, "frame boundary bubble"
        result = {"width":w,"height":h,"input_cycles":len(rows),"checked_words":checked,
                  "checked_pixels":checked*4,"completed_frames":len(output_eofs),
                  "exhaustive_3x3":exhaustive,"output_sha256":digest.hexdigest(),
                  "max_tail_clocks":max(output_eofs[k]-eof_cycles[k] for k in output_eofs)}
        print("PASS", json.dumps(result))
        return result


def main():
    ap = simlib.add_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("--full", action="store_true", help="also test 1280x720")
    ap.add_argument("--out", type=Path, help="write a compact JSON evidence file")
    ap.add_argument("--rtl", type=Path, help="alternate RTL, for negative controls")
    ap.add_argument("--geometry", help="test just WIDTHxHEIGHT (WIDTH divisible by 4)")
    ap.add_argument("--gate-netlist", type=Path, help="TD support3_synth_top netlist; geometry must match")
    ap.add_argument("--td-sim-dir", type=Path, help="vendor TD sim_release directory; read only")
    args = ap.parse_args()
    selfcheck()
    dims = [(4,1),(4,2),(8,1),(8,3),(12,7),(32,9)]
    if args.full: dims.append((1280,720))
    if args.geometry:
        w,h = map(int, args.geometry.lower().split("x"))
        assert w >= 4 and w % 4 == 0 and h >= 1 and w <= 2048 and h <= 1024
        dims = [(w,h)]
    if args.gate_netlist:
        assert args.geometry, "Specify the exact gate-harness geometry with --geometry"
    results = [run(w,h,args,exhaustive=(w==32 and h>=5)) for w,h in dims]
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps({"schema":1,"results":results},indent=2)+"\n",encoding="utf-8")
    print("PASS support3 all geometries; default bypass, set oracle, tags, tail and throughput")


if __name__ == "__main__":
    main()
