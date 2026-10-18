"""Export fixed-source signatures and the actual font panel (not board data)."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from run_edge_stability_probe import OUT,pattern,checksum,panel_for,diagnostic_overlay
from run_edge_control_v1 import glyph_table
import edge_quality_model as quality

def main():
 OUT.mkdir(exist_ok=True);rgb=pattern(1280,720);values={}
 for th in range(10,251,10):
  edge=quality.edges(rgb,th)
  values[str(th)]=dict(crc=f'{checksum(edge):08X}',white_pixels=int((edge!=0).sum()))
 Image.fromarray(rgb).save(OUT/'fixed_rgb.png')
 panel=panel_for(0,1280,720,int(values['80']['crc'],16),60)
 image=np.zeros((320,512,3),np.uint8);font=glyph_table()
 for y in range(320):
  for x in range(0,512,4):
   p=diagnostic_overlay(bytes(12),x+16,y+352,panel,font)
   image[y,x:x+4]=np.frombuffer(p,np.uint8).reshape(4,3)
 Image.fromarray(image).save(OUT/'panel_reference.png')
 (OUT/'fixed_reference.json').write_text(json.dumps(dict(kind='SOFTWARE ONLY; no measured hardware values',
    width=1280,height=720,crc_algorithm='MSB-first poly04C11DB7 initFFFFFFFF no final xor, 2 bits per beat',
    thresholds=values,panel_preview_lead=60),indent=2)+'\n',encoding='utf-8')
 print('PASS reference signatures',json.dumps({k:values[k] for k in ('40','60','80')}))
if __name__=='__main__':main()
