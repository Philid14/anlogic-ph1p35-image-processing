"""Render model-derived synthetic UI previews; never label them board captures."""
from pathlib import Path
import sys,json
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
import run_edge_control_v1 as c
from color_compare_model import patch_means
from planar_measure_model import measure
import inspection_osd_model as osd
from run_inspection_stream_v1 import scene
OUT=ROOT/'docs/evidence/INSPECTION_UI_DIMENSION_V1';OUT.mkdir(parents=True,exist_ok=True)
def main():
    font=c.glyph_table();rgb=scene(1280,720,0)
    # A gentle two-tone backdrop makes transparent glyph pixels unambiguous.
    rgb[:150,:,0]=180;rgb[:150,:,1]=190;rgb[:150,:,2]=210
    means=patch_means(rgb);m=measure(rgb[:,:,0]>=130);m['valid']=True
    cases=[('COLOR_ON',1,False),('COLOR_OFF',0,False),('DIMENSION_MM',3,True),('CALIBRATE_X',11,False),('CALIBRATE_Y',15,False)]
    for name,ui,cal in cases:
        out=np.empty_like(rgb)
        for y in range(720):
            for x in range(0,1280,4):
                p=osd.overlay(rgb[y,x:x+4],x,y,ui,means,0x1234,m,font,cal,400,200,130)
                out[y,x:x+4]=np.frombuffer(osd.status(p,x,y,0,80,130,font,0),np.uint8).reshape(4,3)
        im=Image.new('RGB',(1280,752),'white');im.paste(Image.fromarray(out),(0,32))
        ImageDraw.Draw(im).text((12,10),'SYNTHETIC SOFTWARE MODEL - NOT BOARD PHOTO / '+name,fill='black')
        im.save(OUT/(name+'.png'))
    (OUT/'PREVIEW_SCOPE.json').write_text(json.dumps(dict(synthetic=True,board_capture=False,
        bbox=m['box'],sizes_px=m['sizes'],scale_reference_mm=100,scale_px=[400,200]),indent=2)+'\n')
if __name__=='__main__':main()
