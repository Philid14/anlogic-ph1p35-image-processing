"""Add the reviewed production TARGET files and MAIN adapters to TD once."""
import os
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project/camera_to_dsi_display.al'
text=P.read_text(encoding='utf-8')
sources=sorted((P.parent.parent/'user_source/hdl_source/target').glob('*.v'))
sources += [p for p in sorted((ROOT/'features/color_target/rtl').glob('*.v')) if p.name!='color_target_detect.v']
assert len(sources)==15
assert '/target/frame_transaction_ledger.v' not in text
order=max(map(int,re.findall(r'Name="CompileOrder" Val="(\d+)"',text)))
blocks=[]
for i,p in enumerate(sources):
    relative=Path(os.path.relpath(p,P.parent)).as_posix()
    blocks.append(f'''            <File Path="{relative}">
                <FileInfo>
                    <Attr Name="UsedInSyn" Val="true"/>
                    <Attr Name="UsedInP&R" Val="true"/>
                    <Attr Name="BelongTo" Val="design_1"/>
                    <Attr Name="CompileOrder" Val="{order+i+1}"/>
                </FileInfo>
            </File>
''')
text=text.replace('        </Verilog>',''.join(blocks)+'        </Verilog>')
import xml.etree.ElementTree as ET
ET.fromstring(text.replace('::','__').replace('&','_and_'))
P.write_text(text,encoding='utf-8')
print('TD production inputs',len(re.findall('<File Path=',text)))
