"""Extract actual mapped STYLE RAM configurations from the TD gate export."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tmp/edge_style_fill_v1'
def main():
    path=OUT/'gate.v';text=path.read_text(encoding='utf-8')
    rows=[]
    for m in re.finditer(r'PH1P_PHY_ERAM_V2\s*#\((.*?)\)\s+([^\n]+)\((.*?)\)\);',text,re.S):
        params,instance,ports=m.groups()
        if not re.search(r'\.wea\(\\u_isp_top/g_control\$u_control/g_style_delayed\$u_style/row_(odd|even)_n ',ports):continue
        config=dict(re.findall(r'\.(\w+)\("([^"\n]*)"\)',params))
        selected={k:v for k,v in config.items() if k in ('MODE','DATA_WIDTH_A','DATA_WIDTH_B','WRITEMODE_A','WRITEMODE_B','REGMODE_A','REGMODE_B')}
        rows.append(dict(instance=instance.strip(),bank='odd' if '/row_odd_n' in ports else 'even',configuration=selected))
    assert len(rows)==10,len(rows)
    assert sum(x['bank']=='odd' for x in rows)==5
    result=dict(source_commit=json.loads((OUT/'prebuild.json').read_text())['source_commit'],
        export_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),logical_storage_bits=2*1280*24,
        mapped_eram=rows,method='TD synthesis gate export; configuration inspection, NOT gate/SDF simulation')
    (OUT/'RAM_MAPPING.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS mapped STYLE RAM:',len(rows),'ERAM; banks 5+5; sample',rows[0]['configuration'])
if __name__=='__main__':main()
