"""Independent image-domain model: bounded 2x2 color-region cartoon style.

This is local region stylization, NOT closed-contour/flood/connected-component
filling. Output is anchored at the bottom-right input pixel, with safe pointwise
palette fallback at top/left borders. No history or contour parity is used.
"""
import numpy as np


def style(rgb, details=False):
    rgb = np.asarray(rgb, dtype=np.uint8)
    v = rgb.astype(np.uint16)
    result = ((v >> 6) * 85).astype(np.uint8)
    flat = np.zeros(rgb.shape[:2], bool)
    outline = flat.copy()
    if min(rgb.shape[:2]) > 1:
        window = np.stack((v[:-1, :-1], v[:-1, 1:], v[1:, :-1], v[1:, 1:]))
        bins = window >> 4
        span = bins.max(axis=0) - bins.min(axis=0)
        flat[1:, 1:] = (span <= 2).all(axis=2)
        outline[1:, 1:] = (span >= 4).any(axis=2)
        # Round the four-pixel average, then quantize to a 64-color palette.
        palette_mean = (((window.sum(axis=0) + 2) >> 2) >> 6) * 85
        result[flat] = palette_mean[flat[1:, 1:]].astype(np.uint8)
        result[outline] = 0
    return (result, flat, outline) if details else result


def scenes(w=128, h=72):
    yy, xx = np.indices((h, w))
    def image(mask, fg=(210, 120, 65), bg=(45, 75, 115)):
        return np.where(mask[..., None], fg, bg).astype(np.uint8)
    rect = (xx >= w//4) & (xx < 3*w//4) & (yy >= h//4) & (yy < 3*h//4)
    circle = (xx-w//2)**2 + (yy-h//2)**2 < (h//3)**2
    gap = rect.copy(); gap[h//4:h//4+2, w//2:w//2+2] = False
    line = (abs(yy-h//3) <= 1) & (xx > w//8) & (xx < 7*w//8)
    multi = ((xx-w//4)**2+(yy-h//2)**2 < (h//5)**2) | ((xx-3*w//4)**2+(yy-h//2)**2 < (h//5)**2)
    nested = image(rect); nested[circle & rect] = (40, 200, 100)
    border = (xx < w//3) & (yy < h//2)
    small = (abs(xx-w//2) < 2) & (abs(yy-h//2) < 2)
    rng = np.random.default_rng(910)
    low = image(rect, (112, 117, 123), (105, 110, 116)).astype(np.int16)
    low = np.clip(low+rng.integers(-5, 6, low.shape), 0, 255).astype(np.uint8)
    inner = (xx >= w//4+2) & (xx < 3*w//4-2) & (yy >= h//4+2) & (yy < 3*h//4-2)
    ring = circle & ((xx-w//2)**2+(yy-h//2)**2 >= max(0,h//3-2)**2)
    return dict(rectangle=image(rect), circle=image(circle), gap=image(gap),
                open_line=image(line), independent=image(multi), nested=nested,
                border=image(border), small=image(small), low_noise=low,
                hollow_rectangle=image(rect & ~inner), hollow_circle=image(ring))


def research(out):
    from PIL import Image, ImageDraw
    import json
    out.mkdir(parents=True, exist_ok=True)
    cases = scenes()
    report = {}
    sheet = Image.new('RGB', (128*3, (72+18)*len(cases)), '#222222')
    draw = ImageDraw.Draw(sheet)
    for i, (name, rgb) in enumerate(cases.items()):
        result, flat, ink = style(rgb, True)
        point = (rgb.astype(np.uint16) >> 6)*85
        report[name] = dict(flat_pixels=int(flat.sum()), outline_pixels=int(ink.sum()),
            changed_from_origin=int((rgb != result).any(2).sum()),
            changed_from_palette_only=int((point != result).any(2).sum()))
        # Any constant 2x2 interior must be filled with exactly its own palette
        # color, never a color propagated from another object or earlier row.
        same = (rgb[1:,1:] == rgb[:-1,1:]).all(2) & (rgb[1:,1:] == rgb[1:,:-1]).all(2) & (rgb[1:,1:] == rgb[:-1,:-1]).all(2)
        assert np.array_equal(result[1:,1:][same], point[1:,1:][same])
        report[name]['constant_interior_pixels'] = int(same.sum())
        report[name]['constant_interior_errors'] = 0
        for j, im in enumerate((rgb, point.astype(np.uint8), result)):
            sheet.paste(Image.fromarray(im), (j*128, i*90+18))
        draw.text((0, i*90), name+' | RGB / palette only / STYLE', fill='white')
    sheet.resize((768, len(cases)*180)).save(out/'scenes.png')
    # Locality bound: one changed input pixel can affect ONLY its four 2x2
    # windows, irrespective of gaps, object size, nesting or scanline length.
    base = cases['rectangle']; altered = base.copy(); altered[36, 64] = (0, 255, 0)
    delta = (style(base) != style(altered)).any(2)
    allowed = np.zeros(delta.shape, bool); allowed[36:38, 64:66] = True
    assert not (delta & ~allowed).any()
    report['locality'] = dict(changed_pixels=int(delta.sum()), max_possible=4,
                              beyond_2x2=0)
    # A gap in a one-pixel rectangle is enough to invert a scanline parity
    # fill to the far right; use this only as a counterexample, not an algorithm
    # quality benchmark with arbitrary expected scene truth.
    edge = np.zeros((72,128), bool); edge[18:55,32]=True; edge[18:55,95]=True
    before = np.logical_xor.accumulate(edge, axis=1)
    edge[36,95]=False
    after = np.logical_xor.accumulate(edge, axis=1)
    report['scanline_gap_counterexample'] = dict(changed_pixels=int((before^after).sum()),
                                               changed_right_of_object=int((before^after)[:,96:].sum()))
    # Frame-independent function: disappearance releases immediately; moving
    # shapes exactly equal isolated evaluation at their new coordinates.
    bg = np.full_like(base, 96)
    moved = [np.roll(base, dx, axis=1) for dx in (0,1,2,16,0)] + [bg]
    outputs = [style(x) for x in moved]
    assert np.array_equal(outputs[-1], style(bg))
    report['motion'] = dict(history_frames=0, residual_after_disappearance=0,
                            evaluated_offsets=[0,1,2,16,0])
    (out/'model_results.json').write_text(json.dumps(report, indent=2)+'\n')
    return report
