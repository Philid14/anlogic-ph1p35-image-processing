"""Lossless optical transport. Screen photos are decoded bits, never RGB samples.

MSB-first, non-reflected CRC32 polynomial 04C11DB7, init FFFFFFFF, no final XOR.
Each page: 8 header words, 247 payload words, header CRC at word255.
Header word7 protects all payload including zero padding; word255 protects header.
"""
from pathlib import Path
import argparse,json,hashlib,sys
import numpy as np
from PIL import Image

POLY=0x04c11db7;PAYLOAD=247;MAGIC=0x54525031

def crc(data):
    c=0xffffffff
    for b in data:
        for k in range(7,-1,-1):c=((c<<1)&0xffffffff)^(POLY if ((c>>31)^((int(b)>>k)&1)) else 0)
    return c

def words_bytes(words):return np.asarray(words,dtype='>u4').tobytes()

def encode(words,first_frame):
    words=np.asarray(words,dtype=np.uint32);pages=[];n=(len(words)+PAYLOAD-1)//PAYLOAD
    for page in range(n):
        payload=np.zeros(PAYLOAD,dtype=np.uint32);part=words[page*PAYLOAD:(page+1)*PAYLOAD];payload[:len(part)]=part
        h=[MAGIC,0x10000,len(words),first_frame,page,n,len(part),crc(words_bytes(payload))]
        pages.append(words_bytes(h)+words_bytes(payload)+crc(words_bytes(h)).to_bytes(4,'big'))
    return pages

def check_page(blob):
    if len(blob)!=1024:raise ValueError('page length')
    w=np.frombuffer(blob,dtype='>u4').astype(np.uint32)
    if w[0]!=MAGIC or w[1]!=0x10000:raise ValueError('magic/schema')
    total,session,index,n,valid=map(int,w[2:7])
    if not(0<total<=32768 and n==(total+PAYLOAD-1)//PAYLOAD and 0<=index<n and valid==min(PAYLOAD,total-index*PAYLOAD)):raise ValueError('page bounds')
    if crc(blob[:32])!=int(w[255]) or crc(blob[32:1020])!=int(w[7]):raise ValueError('CRC')
    if np.any(w[8+valid:255]):raise ValueError('padding')
    return (total,session,n),index,w[8:8+valid].copy()

def render(blob):
    bits=np.unpackbits(np.frombuffer(blob,dtype=np.uint8)).reshape(64,128)
    image=np.zeros((720,1280,3),np.uint8)
    image[160:688,120:1160]=255
    image[168:680,128:1152]=np.repeat(np.repeat(bits,8,0),8,1)[:,:,None]*255
    return image

def decode_image(rgb):
    # Optional dependency isolated to optical/video input. No unvalidated OCR.
    import cv2
    rgb=np.asarray(rgb);gray=rgb.min(axis=2).astype(np.uint8)
    found=[]
    for threshold in (80,120,160,200):
        contours,_=cv2.findContours((gray>threshold).astype(np.uint8)*255,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area=cv2.contourArea(c)
            if area<rgb.shape[0]*rgb.shape[1]*.08:continue
            q=cv2.approxPolyDP(c,.018*cv2.arcLength(c,True),True)
            if len(q)!=4 or not cv2.isContourConvex(q):continue
            p=q[:,0,:].astype(np.float32);s=p.sum(1);d=p[:,0]-p[:,1]
            quad=np.array([p[s.argmin()],p[d.argmax()],p[s.argmax()],p[d.argmin()]],np.float32)
            target=np.array([[0,0],[1039,0],[1039,527],[0,527]],np.float32)
            warp=cv2.warpPerspective(gray,cv2.getPerspectiveTransform(quad,target),(1040,528))
            # Median centers reduce blur, ringing and single-pixel noise.
            tiles=warp[8:520,8:1032].reshape(64,8,128,8)
            cells=np.median(tiles[:,2:6,:,2:6],axis=(1,3))
            # Calibrate white from the KNOWN frame, not payload percentiles:
            # the padded final page may contain <10% white data cells.
            lo=float(np.percentile(cells,1));hi=float(np.median(warp[2:6,10:1030]))
            if hi-lo<35:continue
            blob=np.packbits(cells.ravel()>(lo+hi)/2).tobytes()
            try:check_page(blob)
            except ValueError:continue
            if blob not in found:found.append(blob)
        if found:break
    return found

def assemble(blobs):
    identity=None;pages={}
    for blob in blobs:
        ident,page,payload=check_page(blob)
        if identity is None:identity=ident
        if ident!=identity:raise ValueError('mixed burst identity; use separate recordings/directories')
        if page in pages and not np.array_equal(pages[page],payload):raise ValueError('conflicting duplicate page')
        pages[page]=payload
    if identity is None:raise ValueError('no CRC-valid page')
    missing=sorted(set(range(identity[2]))-pages.keys())
    if missing:raise ValueError(f'missing pages {missing}')
    return np.concatenate([pages[i] for i in range(identity[2])])

def unpack_capture(words):
    w=np.asarray(words,dtype=np.uint32)
    # Firmware global header has fixed size16 at stream end.
    g=w[-16:];assert int(g[0])==0x54524f31 and int(g[1])==0x10000,'capture schema'
    width,height=int(g[3])>>16,int(g[3])&65535;frames=int(g[5]);beats=int(g[6]);depth=beats*frames
    assert width%4==0 and beats==width*height//4 and int(g[8])==depth*3
    assert tuple(map(int,g[9:13]))==(depth*3,frames*16,depth*3+frames*16,len(w))
    assert len(w)==depth*3+frames*16+16
    meta=w[depth*3:depth*3+frames*16].reshape(frames,16)
    pre=np.empty((depth,4,3),np.uint8)
    for i in range(depth):
        value=int(w[i])|(int(w[depth+i])<<32)|(int(w[2*depth+i])<<64)
        pre[i]=np.frombuffer(value.to_bytes(12,'big'),np.uint8).reshape(4,3)
    pre=pre.reshape(frames,height,width,3);post=pre.astype(np.uint32)
    for f in range(frames):
        assert crc(pre[f].tobytes())==int(meta[f,8]),f'pre CRC frame{f}'
        for c,gain in ((0,int(meta[f,1])),(2,int(meta[f,2]))):post[f,:,:,c]=np.minimum(255,(post[f,:,:,c]*gain)>>16)
        assert crc(post[f].astype(np.uint8).tobytes())==int(meta[f,9]),f'post reconstruction CRC frame{f}'
    expected=int(g[13])*int(g[14])//4
    assert crc(pre.tobytes())==int(g[15]),'burst content CRC'
    flags=(meta[:,7]>>17)&31
    valid=(meta[:,10]==expected)&(meta[:,11]==(int(g[14])<<16 | int(g[13])//4))&(meta[:,12]==0)&(meta[:,13]==beats<<16)&(meta[:,14]==expected*3//4)&((flags&16)==0)&((flags&12)==12)
    if not np.all(valid):raise ValueError(f'invalid video frames {np.flatnonzero(~valid).tolist()}; do not run temporal ranking')
    if not np.array_equal(meta[:,0],np.arange(int(g[2]),int(g[2])+frames,dtype=np.uint32)):raise ValueError('non-consecutive capture SOFs')
    if np.any((flags&3)!=(flags[0]&3)):raise ValueError('new FIFO sticky event during burst; diagnose stream first')
    return pre,post.astype(np.uint8),meta,g

def main():
    ap=argparse.ArgumentParser();ap.add_argument('input',type=Path);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--stride',type=int,default=3);a=ap.parse_args()
    assert a.stride>0;a.output.mkdir(parents=True,exist_ok=True);saved=a.output/'pages';saved.mkdir(exist_ok=True)
    import cv2
    if a.input.is_dir():sources=sorted(a.input.glob('*'));frames=(np.asarray(Image.open(f).convert('RGB')) for f in sources if f.suffix.lower() in ('.png','.jpg','.jpeg'))
    else:
        cap=cv2.VideoCapture(str(a.input))
        if not cap.isOpened():raise ValueError('cannot open video')
        def video_frames():
            n=0
            while True:
                ok,bgr=cap.read()
                if not ok:break
                if n%a.stride==0:yield cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
                n+=1
            cap.release()
        frames=video_frames()
    count=0
    for rgb in frames:
        for blob in decode_image(rgb):
            ident,index,_=check_page(blob);name=saved/f'{ident[1]:08x}_{index:04d}.bin'
            if name.exists() and name.read_bytes()!=blob:raise ValueError('conflicting page or mixed recording')
            if not name.exists():name.write_bytes(blob);count+=1;print('CRC-valid page',index,'/',ident[2],flush=True)
    blobs=[p.read_bytes() for p in sorted(saved.glob('*.bin'))];words=assemble(blobs);pre,post,meta,g=unpack_capture(words)
    np.savez_compressed(a.output/'capture.npz',pre=pre,post=post,meta=meta,global_header=g)
    info=dict(status='decoded CRC-validated; video quantity checked',pages=len(blobs),new_pages=count,frames=len(pre),roi=list(pre.shape[1:3]),word_sha256=hashlib.sha256(words_bytes(words)).hexdigest())
    (a.output/'capture.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info,indent=2))

if __name__=='__main__':main()
