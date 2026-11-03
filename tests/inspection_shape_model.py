"""Reproducible synthetic reflectance comparison, not board-quality evidence."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/INSPECTION_SHAPE_TRACK_V1'
def bounds(mask):
 y,x=np.where(mask)
 return None if not len(x) else (int(x.min()),int(x.max()),int(y.min()),int(y.max()))
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 plane=np.full((160,256),190,np.uint8);image=plane.copy();image[40:120,60:200]=45;image[40:120,130:200]=240;image[65:95,105:155]=190
 truth=np.zeros(plane.shape,bool);truth[40:120,60:200]=True
 old=image<130;new=np.abs(image.astype(int)-plane.astype(int))>=12
 fig=Image.new('RGB',(1200,340),'white');draw=ImageDraw.Draw(fig);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
 for n,(data,title) in enumerate(zip((image,old,new),('Synthetic mixed reflectance','Previous: gray <130','Learned: |Y-bg| >=12'))):
  draw.text((n*400+12,8),title,font=font,fill='black')
  panel=Image.fromarray(data if data.dtype==np.uint8 else data.astype(np.uint8)*255).resize((384,240),Image.Resampling.NEAREST)
  fig.paste(panel,(n*400+8,48))
 draw.text((12,310),'Synthetic model only. Not a board image or an accuracy claim.',font=font,fill='black')
 fig.save(OUT/'synthetic_reflection.png')
 cases={'old':bounds(old),'learned':bounds(new),'true_outer':bounds(truth)}
 assert cases['old']==(60,129,40,119) and cases['learned']==cases['true_outer']==(60,199,40,119)
 # A completely invisible edge cannot be restored: Y equals the background.
 invisible=plane.copy();assert not np.any(np.abs(invisible.astype(int)-plane.astype(int))>=12)
 result=dict(synthetic_only=True,outer_bounds=cases,old_width_px=70,new_width_px=140,truth_width_px=140,
  old_foreground=int(old.sum()),new_foreground=int(new.sum()),limitations=['Surface holes remain in mask; envelope measures exterior only','No recovery when workpiece and background are optically identical','No board accuracy or glare-recovery-rate claim'])
 (OUT/'model.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':main()
