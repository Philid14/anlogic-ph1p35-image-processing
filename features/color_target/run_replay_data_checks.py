"""Data-contract regression, all fixtures are synthetic and temporary."""
import copy
import json
import tempfile
from pathlib import Path
from model.replay_data import read_ppm, write_ppm, load_manifest, metrics, summarize, sha256


def main():
    checks=0
    with tempfile.TemporaryDirectory(prefix="ct_data_") as td:
        root=Path(td); raw=bytes([10,32,35, 255,0,0, 0,0,0, 35,10,32])
        write_ppm(root/"frame.ppm",4,1,raw)
        assert read_ppm(root/"frame.ppm")[2]==raw; checks+=1
        (root/"crlf.ppm").write_bytes(b"P6\r\n# comment\r\n4 1\r\n255\r\n"+raw)
        assert read_ppm(root/"crlf.ppm")[2]==raw; checks+=1
        frame={"path":"frame.ppm","session":3,"frame":0,"annotation":None,
               "sha256":sha256((root/"frame.ppm").read_bytes())}
        clip={"clip_id":"one","group_id":"scene","split":"validation","source_kind":"synthetic",
              "width":4,"height":1,"frames":[frame]}
        base={"schema":1,"clips":[clip]}
        def load(data):
            (root/"manifest.json").write_text(json.dumps(data),encoding="utf-8")
            return load_manifest(root/"manifest.json")
        load(copy.deepcopy(base)); checks+=1
        def reject(data, label):
            nonlocal checks
            try: load(data)
            except (ValueError,KeyError): checks+=1
            else: raise AssertionError("Accepted bad manifest: "+label)
        for label,key,value in [("hash","sha256","0"*64),("escape","path","../frame.ppm"),
                                ("boolean ID","frame",True),("absent bbox","annotation",{"present":False,"bbox":[0,0,0,0]}),
                                ("bbox range","annotation",{"present":True,"bbox":[0,0,4,0]})]:
            data=copy.deepcopy(base); data["clips"][0]["frames"][0][key]=value; reject(data,label)
        data=copy.deepcopy(base); other=copy.deepcopy(clip); other.update(clip_id="two",split="heldout")
        data["clips"].append(other); reject(data,"scene split leakage")
        other["group_id"]="different"; reject(data,"pixel split leakage")
        data=copy.deepcopy(base); data["clips"][0]["frames"].append(copy.deepcopy(frame)); reject(data,"duplicate ID")
        data=copy.deepcopy(base); data["clips"][0]["source_kind"]="camera"
        data["clips"][0]["frames"][0]["test_fault"]="abort_idle"; reject(data,"camera fault injection")
        predicted={"valid":1,"present":1,"xmin":0,"ymin":0,"xmax":1,"ymax":0,"cx":0,"cy":0}
        assert metrics(None,predicted,4,1) is None; checks+=1
        assert metrics({"present":True,"bbox":[0,0,1,0]},predicted,4,1)["iou"]==1; checks+=1
        absent=metrics({"present":False,"bbox":None},predicted,4,1)
        assert absent["false_positive"]==1 and absent["iou"] is None; checks+=1
        missed=metrics({"present":True,"bbox":[0,0,1,0]},{"valid":1,"present":0},4,1)
        assert missed["miss"]==1 and missed["center_l1"]==5; checks+=1
        report=summarize([{"annotation":None,"metric":None},
                          {"annotation":{"present":True},"metric":None},
                          {"annotation":{"present":True},"metric":missed}])
        assert (report["unknown"],report["excluded_known_frames"],report["evaluated_frames"])==(1,1,1)
        assert report["center_l1_p95"]==5; checks+=1
    print(f"PASS replay data contract checks={checks}; synthetic temporary fixtures only")


if __name__=="__main__": main()
