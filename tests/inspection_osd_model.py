"""Independent screen contract for switchable, transparent instrument overlays."""
import color_compare_model as color
from planar_measure_model import tenths_mm

def dimension_lines(m,calibrated,sx,sy,cal_mode,axis_y,cut,sid):
    vals=[tenths_mm(v,sy if k in (1,3) else sx) if calibrated else v*10 for k,v in enumerate(m['sizes'])]
    fmt=lambda n:f'{n//10:04d}.{n%10}'
    fields=[fmt(v) for v in vals]
    if not m.get('valid',True) or not m['present']:fields=['------']*4
    for k in (2,3):
        if not m['gap'][k-2]:fields[k]='------'
    unit='MM' if calibrated else 'PX'
    rows=[f'SIZE W:{fields[0]} H:{fields[1]} {unit}',
          f'GAPX:{fields[2]} GAPY:{fields[3]} {unit}',
          f'CUT:{cut:03d} '+('BRIGHT' if axis_y else 'DARK  ')+ 'CAL:'+('OK' if calibrated else 'NEEDED'),
          f'LAST:{sid:04X} '+('ALIGN EDGES TO X/Y' if m.get('valid',True) and m['present'] else 'NO VALID OBJECT')]
    if cal_mode:rows=[f'CAL {"Y" if axis_y else "X"} 100.0 MM SPAN:{sy if axis_y else sx:04d} PX',
        'K2 SHORT -4 HOLD +4','SW2 X/Y SW3 OFF CONFIRM','ALIGN RULER IN WORK PLANE']
    return [s.ljust(38) for s in rows]

def overlay(pixels,x,y,ui,means,sid,m,font,calibrated=False,sx=256,sy=256,cut=130):
    if not(ui&2):return color.overlay(pixels,x,y,means,sid,font,means is not None) if ui&1 else pixels
    rows=dimension_lines(m,calibrated,sx,sy,bool(ui&8),bool(ui&4),cut,sid)
    xa=640-sx//2;xb=640+sx//2;ya=352-sy//2;yb=352+sy//2
    result=[]
    for lane,p in enumerate(pixels):
        px=x+lane;p=tuple(p)
        if ui&8:
            mark=((x==640 and ya<=y<=yb) or (y in (ya,yb) and 616<=x<=664)) if ui&4 else (
                (y==352 and xa<=x<=xb) or (x in (xa//4*4,xb//4*4) and 328<=y<=376))
        else:
            mark=(252<=x<1028 and 158<=y<546 and (x<256 or x>=1024 or y<160 or y>=544))
            mark|=(x==640 and 340<=y<=364) or (y==352 and 628<=x<=652)
            if m.get('valid',True) and m['present']:
                xmin,xmax,ymin,ymax=m['box']
                mark|=(x+3>=xmin and x<=xmax and ymin<=y<=ymax and (x<xmin//4*4+4 or x>=xmax//4*4 or y in (ymin,ymax)))
        # Marker is underneath text, exactly like pixel overlay priority.
        if mark:p=(255,255,128)
        if 32<=px<1248 and 544<=y<672:
            row=(y-544)//32;col=(px-32)//32;char=rows[row][col]
            bits=font.get(ord(char),{}).get(((y-544)%32)//2,0)
            # Same four-row colors as comparison. Dim status color is cosmetic;
            # color-measurement validity and MAX retain their original meaning.
            if row==3:
                ink=(255,255,0) if means is None else (64,255,128) if max(abs(a-b) for a,b in zip(*means))<=12 else (255,128,64)
            else:ink=[(64,255,128),(64,223,255),(255,255,128)][row]
            if bits&(1<<(15-((px-32)%32)//2)):p=ink
        result.append(p)
    return result

def status(pixels,x,y,mode,et,bt,font,fifo_counts=0x1234abcd):
    mode_name=['ORIGIN','GRAY','BINARY','EDGE','STYLE'][mode]
    threshold=bt if mode==2 else et
    lines=[f'MODE: {mode_name}'.ljust(14),
        (f'THRESHOLD: {threshold:03}' if mode in (2,3) else 'THRESHOLD:').ljust(14),
        f'B:{fifo_counts>>16:04X} S:{fifo_counts&65535:04X}'.ljust(14)]
    result=[]
    for lane,p in enumerate(pixels):
        px=x+lane
        if 800<=px<1248 and ((16<=y<88) or 96<=y<128):
            ly=y-16;row=0 if ly<32 else 1 if 40<=ly<72 else 2 if ly>=80 else None
            if row is not None:
                glyph_y=(ly-[0,40,80][row])//2;col=(px-800)//32
                bits=font.get(ord(lines[row][col]),{}).get(glyph_y,0)
                if bits&(1<<(15-((px-800)%32)//2)):p=(255,255,0)
        result.append(p)
    return bytes(c for p in result for c in p)
