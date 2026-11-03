"""Export selected MAIN Git blobs for read-only review, without switching checkout."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

ROOT=Path(__file__).resolve().parents[3]
REVISION='5cbb1de3814a842067ee1ffd41df3d75bbf0de26'
PROJECT='in_out_example/lab_ex3_osd_SC500_720P/lab_ex3_osd/user_source/'


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);src=out/'source';src.mkdir()
    paths=['features/color_target/rtl','tests/tb_target_frame_system_active_epoch.sv',PROJECT+'hdl_source/target']
    paths += [PROJECT+'hdl_source/'+n for n in ('video_in.v','video_out.v','mc_to_user_interface.v','data_96bit_to_128bit.v','isp/fifo_event_counter.v','vtc/uivtc.v')]
    paths += [PROJECT+'ip_source/'+n for n in ('w128_d512_fifo','w155_d512_fifo')]
    raw=subprocess.check_output(['git','ls-tree','-r','-z',REVISION,'--',*paths],cwd=ROOT)
    rows=[]
    for record in raw.split(b'\0'):
        if not record:continue
        metadata,name=record.split(b'\t',1);mode,kind,blob=metadata.decode().split();rel=name.decode('utf-8')
        if kind!='blob' or mode not in ('100644','100755') or '..' in PurePosixPath(rel).parts:raise ValueError('Unsupported Git entry')
        data=subprocess.check_output(['git','cat-file','blob',blob],cwd=ROOT)
        if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=blob:raise ValueError('Git object binding failed')
        dest=src/rel
        if not dest.resolve().is_relative_to(src):raise ValueError('Escaping Git entry')
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        rows.append(dict(path=rel,git_blob=blob,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
    if not rows:raise ValueError('Empty snapshot')
    (out/'snapshot-manifest.json').write_text(json.dumps(dict(commit=REVISION,scope='Selected digital review inputs; not a complete TD build snapshot',files=rows),indent=2)+'\n')
    print(json.dumps(dict(commit=REVISION,files=len(rows),source=str(src)),indent=2))


if __name__=='__main__':main()
