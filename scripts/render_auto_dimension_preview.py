"""Synthetic screen previews only; never treat them as board/camera data."""
from pathlib import Path
import sys,json
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
import run_edge_control_v1 as c
from auto_dimension_model import draw
def main():
    out=ROOT/'docs/evidence/INSPECTION_AUTO_DIMENSION_V2';out.mkdir(parents=True,exist_ok=True)
    base=np.full((720,1280,3),220,np.uint8);base[240:460,400:820]=35;base[314:390,600:680]=220
    obj=dict(valid=True,present=True,box=(400,819,240,459),sizes=(420,220,80,76),gap=(True,True))
    font=c.glyph_table()
    image=draw(base,obj,font,True,500,500,False,3,(600,679,314,389))
    Image.fromarray(image).save(out/'DRAWING_MODEL_PREVIEW.png')
    Image.fromarray(draw(np.full_like(base,100),dict(valid=False,present=False),font,False,0,0,True,0)).save(out/'CAL_MODEL_PREVIEW.png')
    (out/'PREVIEW_SCOPE.json').write_text(json.dumps(dict(scope='Independent synthetic model, not board photos or user workpiece measurements',example_scale='500px/100mm shared X/Y'),indent=2)+'\n')
if __name__=='__main__':main()
