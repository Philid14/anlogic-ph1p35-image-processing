"""Independent spatial reference for STYLE V2; no state or RTL dependencies.

Shared lightness bands preserve chroma; low-chroma inputs become neutral.
Only very flat 2x2 windows are averaged. Coherent luma gradients ink their
dark side, preserving bright thin strokes and avoiding 2x2 black dilation.
"""
import numpy as np


def palette(rgb):
    p = np.asarray(rgb, dtype=np.int32)
    low, high = p.min(axis=-1), p.max(axis=-1)
    light = (low + high + 1) // 2
    q = np.where(light >= 240, 255, ((light + 16) // 32) * 32)
    delta = q - light
    color = np.clip(p + delta[..., None], 0, 255)
    return np.where((high-low <= 12)[..., None], q[..., None], color).astype(np.uint8)


def style(rgb, details=False, ink='coherent'):
    p = np.asarray(rgb, dtype=np.int32)
    h, w = p.shape[:2]
    base = p.copy()
    flat = np.zeros((h,w), bool)
    edge = flat.copy()
    if h > 1 and w > 1:
        # Window order is UL, U, L, C; current C is output coordinate.
        a,b,c,d = p[:-1,:-1],p[:-1,1:],p[1:,:-1],p[1:,1:]
        win = np.stack((a,b,c,d))
        bins = win >> 4
        flat[1:,1:] = (bins.max(0) == bins.min(0)).all(2)
        mean = (win.sum(0) + 2) // 4
        base[flat] = mean[flat[1:,1:]]
        ys = (win[...,0]//4 + win[...,1]//2 + win[...,2]//4)
        ya,yb,yc,yd = ys
        dx = abs((yb+yd)-(ya+yc))
        dy = abs((yc+yd)-(ya+yb))
        dark = 4*yd <= ys.sum(0)
        edge[1:,1:] = ((dx >= 96) | (dy >= 96)) & dark
        if ink == 'v1':
            edge[1:,1:] = (bins.max(0)-bins.min(0) >= 4).any(2)
    result = palette(base)
    result[edge] = 0
    return (result,flat,edge) if details else result
