"""Check text updates while conversion is running, using only public ports.

A visible tuple must be one complete input snapshot, never a mixture. The
oracle uses decimal formatting, not a copy of the RTL conversion state machine.
Intermediate input changes may coalesce; the latest stable tuple must become
visible within 140 clocks. Reset discards both pending and published data.
"""

import argparse
import importlib.util
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = ("SEARCH", "ACQ   ", "TRACK ", "HOLD  ")
ZERO = (0, 0, 0, 0, 0)  # show, state, count, x, y


def snapshot(value):
    show, state, count, x, y = value
    return (f"RED X{min(x, 9999):04d} Y{min(y, 999):03d}",
            f"N{min(count, 999999):06d} {NAMES[state]}",
            0xFFFFFF if show else 0x808080)


def stimuli(xw, yw):
    rows, checks, allowed = [], [], {snapshot(ZERO)}

    def add(value, cycles, name, update=0, reset=False, settled=False):
        nonlocal allowed
        for i in range(cycles):
            if reset:
                allowed = {snapshot(ZERO)}
            else:
                allowed.add(snapshot(value))
            show, state, count, x, y = value
            rows.append((0 if reset else 1, update if i == 0 else 0,
                         show, state, count, x, y))
            expected = snapshot(ZERO) if reset else snapshot(value) if settled else None
            checks.append((name, set(allowed), expected))

    def settle(value, name, update=0):
        add(value, 140, name, update=update)
        add(value, 3, name + "/settled", settled=True)

    a = (1, 2, 123456, 789, 321)
    b = (0, 3, 654321, 123, 456)
    c = (1, 1, 99999, 1001, 719)
    d = (0, 0, 345678, 456, 123)
    add(ZERO, 2, "reset", reset=True)
    settle(ZERO, "zero_without_update")
    settle(a, "atomic_publish", update=1)
    settle(b, "automatic_change")
    # Arrivals during each conversion round and at its final publish boundary.
    for delay in (1, 8, 25, 48, 68, 69, 70):
        add(a, delay, f"busy_at_{delay}", update=1)
        settle(c, f"latest_after_{delay}", update=1)
        settle(b, f"restore_after_{delay}")
    add(a, 8, "burst_first", update=1)
    add(b, 22, "burst_second", update=1)
    add(c, 24, "burst_third", update=1)
    settle(d, "burst_latest", update=1)
    settle((d[0], 3, *d[2:]), "state_only")
    settle((1, 3, *d[2:]), "show_only")
    for i in range(160):
        add((i & 1, i % 4, i * 1111, i * 3, i * 2), 1,
            "continuous_updates", update=1)
    settle(a, "continuous_updates_stop")
    add(b, 31, "before_reset", update=1)
    add(c, 2, "reset_in_flight", reset=True)
    settle(c, "after_reset")
    maximum = (1, 2, 1048575, min(16000, (1 << xw) - 1),
               min(2000, (1 << yw) - 1))
    settle(maximum, "saturation")
    # A transient input may be coalesced, but must not corrupt the final tuple.
    add(a, 10, "return_to_previous", update=1)
    add(b, 1, "transient", update=1)
    settle(a, "return_latest")
    return rows, checks


def main():
    spec = importlib.util.spec_from_file_location("ct_simlib", HERE / "tools" / "simlib.py")
    simlib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(simlib)
    ap = simlib.add_args(argparse.ArgumentParser(description=__doc__))
    ap.add_argument("--rtl", type=Path, default=HERE / "rtl" / "color_target_text_overlay.v",
                    help="Override the RTL file to check a historical implementation")
    args = ap.parse_args()
    total, failures = 0, 0
    for xw, yw in ((11, 10), (14, 12)):
        rows, checks = stimuli(xw, yw)
        with tempfile.TemporaryDirectory(prefix="cttxt-update-") as td:
            tmp = Path(td)
            stim, outp = tmp / "stim.txt", tmp / "dut.txt"
            stim.write_text("".join(" ".join(map(str, row)) + "\n" for row in rows),
                            encoding="ascii")
            ok, out, err = simlib.simulate(
                srcs=[args.rtl.resolve(), HERE / "tb" / "tb_color_target_text_updates.v"],
                tb_top="tb_color_target_text_updates", params=dict(XW=xw, YW=yw),
                plusargs=dict(STIM=stim.as_posix(), OUT=outp.as_posix()),
                requested=args.sim, msim_root=args.msim, workdir=tmp, name="updates")
            if not ok or "FAIL" in out or "PASS color_target_text_updates" not in out:
                print("FAIL simulation\n" + (err or out)[-2500:])
                return 2
            samples = outp.read_text(encoding="ascii").splitlines()
        if len(samples) != len(checks):
            print(f"FAIL dump length {len(samples)} != {len(checks)}")
            return 2
        bad, mixed_digits = [], []
        for i, (line, (name, allowed, expected)) in enumerate(zip(samples, checks)):
            index, hex0, hex1, tone = line.split()
            if int(index) != i:
                print(f"FAIL sample index {index} != {i}")
                return 2
            got = (bytes.fromhex(hex0).decode("ascii"),
                   bytes.fromhex(hex1).decode("ascii"), int(tone, 16))
            if got not in allowed or (expected is not None and got != expected):
                bad.append((i, name, got, expected))
            if (got[0], got[1][:7]) not in {(a[0], a[1][:7]) for a in allowed}:
                mixed_digits.append((i, name, got))
        total += len(samples)
        if bad:
            failures += len(bad)
            print(f"FAIL XW={xw}/YW={yw}: {len(bad)}/{len(samples)} clocks")
            for item in bad[:5]:
                print(f"      cycle={item[0]} case={item[1]} got={item[2]!r} expected={item[3]!r}")
            if mixed_digits:
                print(f"      mixed digit tuples={len(mixed_digits)}; first={mixed_digits[0]!r}")
        else:
            print(f"PASS XW={xw}/YW={yw}: {len(samples)} clocks, atomic tuples and latest-value progress")
    print(f"{'FAIL' if failures else 'PASS'} text updates: {total} clocks, {failures} violations")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
