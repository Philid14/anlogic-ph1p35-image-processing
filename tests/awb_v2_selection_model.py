"""Small RGB888 AWB sample-selection model; not an RTL timing simulation.

Run: python tests/awb_v2_selection_model.py
The scenes exercise the exact AWB_V2 candidate gate and existing Q4.16
gain clamp/step policy before a Tang Dynasty build and board comparison.
"""

from pathlib import Path
import re


RTL = (
    Path(__file__).resolve().parents[1]
    / "in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd"
    / "user_source/hdl_source/awb.v"
).read_text(encoding="utf-8")


def constant(name: str, radix: str) -> int:
    match = re.search(rf"\b{name}\s*=\s*\d+'{radix}([0-9a-f]+)", RTL)
    assert match is not None, f"missing RTL constant {name}"
    return int(match.group(1), {"d": 10, "h": 16}[radix])


CHROMA = constant("CHROMA_THRESHOLD", "d")
MIN_SAMPLES = constant("MIN_SAMPLES", "d")
GAIN_MIN = constant("GAIN_MIN", "h")
GAIN_MAX = constant("GAIN_MAX", "h")
GAIN_STEP = constant("GAIN_STEP", "h")
ONE = constant("GAIN_ONE", "h")


def usable(pixel: tuple[int, int, int], neutral_only: bool) -> bool:
    lo, hi = min(pixel), max(pixel)
    return 24 <= hi < 240 and (not neutral_only or hi - lo < CHROMA)


def frame_target(
    scene: list[tuple[tuple[int, int, int], int]],
    neutral_only: bool,
    prior: tuple[int, int] = (ONE, ONE),
) -> tuple[tuple[int, int], int]:
    sums = [0, 0, 0]
    count = 0
    for pixel, repeats in scene:
        if usable(pixel, neutral_only):
            count += repeats
            for channel in range(3):
                sums[channel] += pixel[channel] * repeats
    if count < MIN_SAMPLES or min(sums) == 0:
        return prior, count
    targets = [
        max(GAIN_MIN, min(GAIN_MAX, (sums[1] << 16) // sums[channel]))
        for channel in (0, 2)
    ]
    return tuple(
        old + max(-GAIN_STEP, min(GAIN_STEP, target - old))
        for old, target in zip(prior, targets)
    ), count


def show(name: str, scene: list[tuple[tuple[int, int, int], int]]) -> None:
    old, old_count = frame_target(scene, False)
    new, new_count = frame_target(scene, True)
    print(
        f"{name:18} V1 count={old_count:6d} gain={tuple(round(x / ONE, 4) for x in old)}"
        f" | V2 count={new_count:6d} gain={tuple(round(x / ONE, 4) for x in new)}"
    )
    if name in ("red", "green", "blue"):
        assert new_count == 0 and new == (ONE, ONE)
    elif name in ("gray", "white"):
        assert new_count >= MIN_SAMPLES and new == (ONE, ONE)
    elif name == "cyan-white":
        assert new_count >= MIN_SAMPLES and new[0] > ONE
    elif name == "red-on-gray":
        assert new_count >= MIN_SAMPLES and new[0] == ONE and old[0] < ONE


if __name__ == "__main__":
    print(f"RTL: chroma<{CHROMA}, min samples={MIN_SAMPLES}, frame step={GAIN_STEP / ONE}")
    show("red", [((200, 30, 30), 1280 * 720)])
    show("green", [((30, 200, 30), 1280 * 720)])
    show("blue", [((30, 30, 200), 1280 * 720)])
    show("gray", [((128, 128, 128), 1280 * 720)])
    show("white", [((220, 220, 220), 1280 * 720)])
    show("cyan-white", [((160, 185, 180), 1280 * 720)])
    show("red-on-gray", [((200, 30, 30), 230_400), ((128, 128, 128), 691_200)])
