"""Compact subset of the project's original 5x7 font; no shared glyph edits."""
from pathlib import Path
from generate_inspection_font import GLYPHS
ROOT=Path(__file__).resolve().parents[1]
CHARS='0123456789ABCDEFGILMNPRSTWX:. UH'
assert len(CHARS)<=32 and len(set(CHARS))==len(CHARS)
def main():
    out=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/hdl_source/vision/latency_font.dath'
    words=[]
    for c in CHARS.ljust(32):
        rows=GLYPHS.get(c,['00000']*7)
        words += [0]+[int('000'+''.join(b*2 for b in row)+'000',2) for row in rows for _ in range(2)]+[0]
    # Physical ROM depth1024; unused words explicitly initialized.
    out.write_text('\n'.join(f'{v:05x}' for v in words+[0]*512)+'\n')
    print('Generated original font',len(CHARS),'glyphs',out)
if __name__=='__main__':main()
