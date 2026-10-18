"""Independent transport gates; synthetic data here is not board evidence."""
from pathlib import Path
import sys,io,json
import numpy as np
from PIL import Image
import temporal_transport as t

def main():
    import cv2
    rng=np.random.default_rng(20261018);words=rng.integers(0,2**32,24720,dtype=np.uint32)
    blobs=t.encode(words,0x78543210)
    assert np.array_equal(t.assemble(blobs[::-1]+blobs[:5]),words)
    failures=0
    for offset in (0,7,31,32,47,511,1019,1020,1023):
        b=bytearray(blobs[0]);b[offset]^=1
        try:t.check_page(bytes(b))
        except ValueError:failures+=1
        else:raise AssertionError('corruption accepted')
    for bad in (blobs[:-1],[blobs[0]]+[t.encode(words^1,1)[1]]):
        try:t.assemble(bad)
        except ValueError:failures+=1
        else:raise AssertionError('incomplete/mixed burst accepted')
    image=t.render(blobs[12]);results={}
    cases={'exact':image}
    # Photograph-like perspective, brightness/gamma, mild blur, noise, JPEG.
    src=np.float32([[0,0],[1279,0],[1279,719],[0,719]])
    dst=np.float32([[118,83],[1450,25],[1370,900],[35,825]])
    warp=cv2.warpPerspective(image,cv2.getPerspectiveTransform(src,dst),(1536,960))
    warp=np.uint8(np.clip((warp.astype(float)/255)**1.35*207+12+rng.normal(0,2,warp.shape),0,255))
    warp=cv2.GaussianBlur(warp,(3,3),.6)
    buf=io.BytesIO();Image.fromarray(warp).save(buf,format='JPEG',quality=80)
    cases['perspective_gamma_noise_jpeg']=np.asarray(Image.open(io.BytesIO(buf.getvalue())))
    cases['downscale_720p']=np.asarray(Image.fromarray(image).resize((1024,576),Image.Resampling.LANCZOS))
    for name,rgb in cases.items():
        assert t.decode_image(rgb)==[blobs[12]],name;results[name]='bit exact, both CRCs passed'
    # Overlay a bit change: the decoder must not return the corrupted page.
    bad=image.copy();bad[170:176,130:136]=255-bad[170:176,130:136]
    assert not t.decode_image(bad)
    out=Path(__file__).resolve().parents[1]/'docs/edge_temporal_evidence';out.mkdir(exist_ok=True)
    (out/'transport_tests.json').write_text(json.dumps(dict(pages=len(blobs),negative_cases=failures+1,optical=results,real_phone_test=False),indent=2)+'\n')
    Image.fromarray(cases['perspective_gamma_noise_jpeg']).save(out/'synthetic_transport_preview.jpg',quality=90)
    print('PASS optical bit exact cases',results,'corruption/incomplete/mixed rejected',failures+1)

if __name__=='__main__':main()
