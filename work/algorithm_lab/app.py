"""FastAPI backend server for FPGA Algorithm Lab."""
import os
import json
import hashlib
import time
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Dict, Any, List

import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Import plugins
from plugins.base import BaseAlgorithm
from plugins.grayscale import GrayscaleAlgorithm
from plugins.threshold import ThresholdAlgorithm
from plugins.sobel import SobelAlgorithm
from plugins.cartoon import CartoonAlgorithm
from plugins.fastestdet import FastestDetAlgorithm
from plugins.yolo_reference import YoloReferenceAlgorithm
from plugins.latency_osd import LatencyOsdAlgorithm

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
SAMPLES_DIR = BASE_DIR / "samples"
EXPORTS_DIR = BASE_DIR / "exports"
REGISTRY_PATH = BASE_DIR / "registry.json"
CACHE_DIR = BASE_DIR / "cache"
Y1_DIR = BASE_DIR.parents[0] / "y1_yolo"
Y1_LAB_DIR = Y1_DIR / "results" / "lab"
Y1_UPLOAD_DIR = Y1_LAB_DIR / "uploads"
Y2_DIR = BASE_DIR.parents[0] / "y2_micro"
Y2_LAB_DIR = Y2_DIR / "results" / "lab"

CACHE_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)
Y1_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
Y2_LAB_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="FPGA Algorithm Lab API")

# Register available algorithm plugins
PLUGIN_INSTANCES: Dict[str, BaseAlgorithm] = {
    "cartoon": CartoonAlgorithm(),
    "sobel": SobelAlgorithm(),
    "threshold": ThresholdAlgorithm(),
    "grayscale": GrayscaleAlgorithm(),
    "latency_osd": LatencyOsdAlgorithm(),
}
DETECTION_PLUGIN = FastestDetAlgorithm()
QUALITY_DETECTION_PLUGIN = YoloReferenceAlgorithm()
Y2_MODELS = {}


def y2_detect(image, size, confidence):
    checkpoint = Y2_DIR / "models" / f"microdet_{size}.pth"
    if not checkpoint.exists():
        raise HTTPException(status_code=503, detail=f"Y2 {size} model not trained yet")
    if size not in Y2_MODELS:
        import sys
        import torch
        sys.path.insert(0, str(Y2_DIR))
        from microdet import MicroDet
        model = MicroDet().eval()
        model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
        torch.set_num_threads(4)
        Y2_MODELS[size] = model
    from microdet import detect
    return detect(Y2_MODELS[size], image, size, confidence)


def y1_manifest():
    path = Y1_DIR / "datasets" / "test_manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def y2_test_manifest():
    path = Y2_DIR / "data" / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))["test"] if path.exists() else []


@app.get("/api/yolo/samples")
def yolo_samples():
    return [{"id": str(item["image_id"]), "label": f'Y1 诊断图 {item["image_id"]}',
             "classes": sorted({obj["class"] for obj in item["objects"]}),
             "split": "Y1 development diagnostics"} for item in y1_manifest()] + [
             {"id": str(item["image_id"]), "label": f'Y2 测试图 {item["image_id"]}',
              "classes": sorted({obj["class"] for obj in item["objects"]}),
              "split": "Y2 frozen public holdout"} for item in y2_test_manifest()]


@app.post("/api/yolo/upload")
async def yolo_upload(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".bmp", ".mp4", ".avi"}:
        raise HTTPException(status_code=400, detail="Unsupported image or video")
    content = await file.read()
    if not content or len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File must be 1 byte to 100 MB")
    upload_id = uuid.uuid4().hex
    (Y1_UPLOAD_DIR / f"{upload_id}{suffix}").write_bytes(content)
    return {"sample_id": upload_id, "filename": Path(file.filename or "").name}


class YoloProcessRequest(BaseModel):
    sample_id: str
    confidence: float = 0.25
    resolution: int | None = None
    model: str = "ultralytics_yolov8n"


def yolo_input_path(sample_id: str) -> Path:
    matches = [item for item in y1_manifest() if str(item["image_id"]) == sample_id]
    if matches:
        return Y1_DIR / matches[0]["file"]
    matches = [item for item in y2_test_manifest() if str(item["image_id"]) == sample_id]
    if matches:
        return Y2_DIR / matches[0]["file"]
    if len(sample_id) == 32 and all(ch in "0123456789abcdef" for ch in sample_id):
        for path in Y1_UPLOAD_DIR.glob(f"{sample_id}.*"):
            return path
    raise HTTPException(status_code=404, detail="Unknown Y1 sample")


YOLO8_MODEL = None
FASTESTV2_MODEL = None
FASTESTV2_CFG = None
FASTESTV2_NAMES = None


def get_yolov8():
    global YOLO8_MODEL
    if YOLO8_MODEL is None:
        from ultralytics import YOLO
        weights = BASE_DIR / "yolov8n.pt"
        if not weights.is_file():
            raise HTTPException(status_code=503, detail="Missing local YOLOv8n weights: work/algorithm_lab/yolov8n.pt")
        YOLO8_MODEL = YOLO(str(weights))
    return YOLO8_MODEL


def get_yolo_fastestv2():
    global FASTESTV2_MODEL, FASTESTV2_CFG, FASTESTV2_NAMES
    if FASTESTV2_MODEL is None:
        import sys
        import torch
        v2_dir = Y1_DIR / "Yolo-FastestV2"
        if str(v2_dir) not in sys.path:
            sys.path.insert(0, str(v2_dir))
        import model.detector
        import utils.utils
        FASTESTV2_CFG = utils.utils.load_datafile(str(v2_dir / "data" / "coco.data"))
        FASTESTV2_CFG["names"] = str(v2_dir / "data" / "coco.names")
        with open(FASTESTV2_CFG["names"], "r", encoding="utf-8") as f:
            FASTESTV2_NAMES = [line.strip() for line in f]
        det = model.detector.Detector(FASTESTV2_CFG["classes"], FASTESTV2_CFG["anchor_num"], False)
        weights_path = Y1_DIR / "yolo_fastestv2_coco.pth"
        det.load_state_dict(torch.load(weights_path, map_location="cpu", weights_only=True))
        det.eval()
        FASTESTV2_MODEL = det
    return FASTESTV2_MODEL, FASTESTV2_CFG, FASTESTV2_NAMES


def yolov8_detect(image_bgr, conf_thresh, imgsz=640):
    start = time.perf_counter()
    model = get_yolov8()
    results = model.predict(image_bgr, imgsz=imgsz, conf=conf_thresh, verbose=False)[0]
    elapsed = (time.perf_counter() - start) * 1000.0
    detections = []
    target_map = {39: "bottle", 41: "cup", 67: "cell phone"}
    for box in results.boxes:
        cls_id = int(box.cls[0])
        score = float(box.conf[0])
        if cls_id in target_map:
            xyxy = [round(float(x), 2) for x in box.xyxy[0].tolist()]
            detections.append({
                "class": target_map[cls_id],
                "confidence": round(score, 4),
                "box": xyxy
            })
    return detections, elapsed


def yolo_fastestv2_detect(image_bgr, conf_thresh):
    start = time.perf_counter()
    import sys
    import torch
    v2_dir = Y1_DIR / "Yolo-FastestV2"
    if str(v2_dir) not in sys.path:
        sys.path.insert(0, str(v2_dir))
    import utils.utils
    model, cfg, names = get_yolo_fastestv2()
    h, w = image_bgr.shape[:2]
    res_img = cv2.resize(image_bgr, (cfg["width"], cfg["height"]), interpolation=cv2.INTER_LINEAR)
    inp = res_img.reshape(1, cfg["height"], cfg["width"], 3).transpose(0, 3, 1, 2)
    inp = torch.from_numpy(inp).float() / 255.0
    with torch.inference_mode():
        preds = model(inp)
    out = utils.utils.handel_preds(preds, cfg, torch.device("cpu"))
    boxes = utils.utils.non_max_suppression(out, conf_thres=conf_thresh, iou_thres=0.4)[0]
    elapsed = (time.perf_counter() - start) * 1000.0
    scale_h, scale_w = h / cfg["height"], w / cfg["width"]
    target_3 = {"bottle", "cup", "cell phone"}
    detections = []
    for b in boxes:
        cls_name = names[int(b[5])]
        if cls_name in target_3:
            box = [round(float(b[0] * scale_w), 2), round(float(b[1] * scale_h), 2),
                   round(float(b[2] * scale_w), 2), round(float(b[3] * scale_h), 2)]
            detections.append({
                "class": cls_name,
                "confidence": round(float(b[4]), 4),
                "box": box
            })
    return detections, elapsed


@app.post("/api/yolo/process")
def yolo_process(req: YoloProcessRequest):
    allowed_models = ("fastestdet_y1", "microdet_y2", "ultralytics_yolov8n", "ultralytics_yolov8m", "yolo_fastestv2")
    if not 0.01 <= req.confidence <= 0.99 or req.model not in allowed_models:
        raise HTTPException(status_code=400, detail="Invalid confidence or resolution")
    defaults = {"ultralytics_yolov8m": 640, "ultralytics_yolov8n": 640, "fastestdet_y1": 352,
                "yolo_fastestv2": 352, "microdet_y2": 160}
    sizes = {"ultralytics_yolov8m": (640, 960), "ultralytics_yolov8n": (960, 640, 352, 160, 128, 96),
             "fastestdet_y1": (352, 160, 128, 96),
             "yolo_fastestv2": (352,), "microdet_y2": (160, 128, 96)}
    if req.resolution is None:
        req = req.model_copy(update={"resolution": defaults[req.model]})
    if req.resolution not in sizes[req.model]:
        raise HTTPException(status_code=400, detail=f"Unsupported resolution for {req.model}: {req.resolution}")
    import sys
    if str(Y1_DIR) not in sys.path:
        sys.path.insert(0, str(Y1_DIR))
    from fastestdet_runtime import draw
    if req.model == "ultralytics_yolov8m":
        detector = lambda frame: QUALITY_DETECTION_PLUGIN.detect_bgr(frame, params)
        out_root, asset_route = Y1_LAB_DIR, "/y1-assets"
    elif req.model == "ultralytics_yolov8n":
        detector = lambda frame: yolov8_detect(frame, req.confidence, req.resolution)
        out_root, asset_route = Y1_LAB_DIR, "/y1-assets"
    elif req.model == "yolo_fastestv2":
        detector = lambda frame: yolo_fastestv2_detect(frame, req.confidence)
        out_root, asset_route = Y1_LAB_DIR, "/y1-assets"
    elif req.model == "fastestdet_y1":
        DETECTION_PLUGIN.detector
        detector = lambda frame: DETECTION_PLUGIN.detect_bgr(frame, params)
        out_root, asset_route = Y1_LAB_DIR, "/y1-assets"
    else:
        import sys
        if str(Y2_DIR) not in sys.path:
            sys.path.insert(0, str(Y2_DIR))
        detector = lambda frame: y2_detect(frame, req.resolution, req.confidence)
        out_root, asset_route = Y2_LAB_DIR, "/y2-assets"
    source = yolo_input_path(req.sample_id)
    run_id = uuid.uuid4().hex
    out_dir = out_root / run_id
    out_dir.mkdir(parents=True)
    shutil.copyfile(source, out_dir / f"input{source.suffix.lower()}")
    params = {"confidence": req.confidence, "resolution": req.resolution, "model": req.model}
    if source.suffix.lower() in {".mp4", ".avi"}:
        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Failed to decode video")
        fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        writer = cv2.VideoWriter(str(out_dir / "annotated.mp4"),
                                 cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
        frames = []
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            detections, forward_ms = detector(frame)
            writer.write(draw(frame, detections))
            frames.append({"index": len(frames), "detections": detections,
                           "forward_ms": round(forward_ms, 3)})
        cap.release()
        writer.release()
        if not frames:
            raise HTTPException(status_code=400, detail="Video contains no frames")
        result = {"kind": "video", "frames": frames,
                  "annotated_url": f"{asset_route}/{run_id}/annotated.mp4"}
    else:
        bgr = cv2.imdecode(np.fromfile(str(source), dtype=np.uint8), cv2.IMREAD_COLOR)
        if bgr is None:
            raise HTTPException(status_code=400, detail="Failed to decode image")
        detections, forward_ms = detector(bgr)
        cv2.imwrite(str(out_dir / "annotated.jpg"), draw(bgr, detections))
        result = {"kind": "image", "detections": detections,
                  "forward_ms": round(forward_ms, 3),
                  "annotated_url": f"{asset_route}/{run_id}/annotated.jpg"}
    model_labels = {
        "ultralytics_yolov8m": "Ultralytics YOLOv8m COCO 80-class; PC visual reference only",
        "ultralytics_yolov8n": "Ultralytics YOLOv8n original COCO 80-class; output filtered to 3 classes",
        "fastestdet_y1": "FastestDet original COCO 80-class; output filtered to 3 classes",
        "yolo_fastestv2": "YOLO-FastestV2 original COCO 80-class; output filtered to 3 classes",
        "microdet_y2": f"Y2 MicroDet three-class trained at {req.resolution}; quality gate failed",
    }
    result.update({"run_id": run_id, "sample_id": req.sample_id, "params": params,
                   "model": model_labels[req.model],
                   "stage": "VISUAL_REVIEW_PENDING",
                   "export_url": f"/api/yolo/export/{run_id}"})
    (out_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
    return result


@app.get("/api/yolo/export/{run_id}")
def yolo_export(run_id: str):
    if len(run_id) != 32 or any(ch not in "0123456789abcdef" for ch in run_id):
        raise HTTPException(status_code=404, detail="Unknown run")
    out_dir = next((base / run_id for base in (Y1_LAB_DIR, Y2_LAB_DIR)
                    if (base / run_id / "result.json").exists()), None)
    if out_dir is None:
        raise HTTPException(status_code=404, detail="Unknown run")
    archive = out_dir / "experiment.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in out_dir.iterdir():
            if path != archive and path.is_file():
                z.write(path, path.name)
    label = json.loads((out_dir / "result.json").read_text(encoding="utf-8"))["params"]["model"]
    return FileResponse(archive, filename=f"{label}_{run_id}.zip")


def load_registry() -> List[dict]:
    if REGISTRY_PATH.exists():
        try:
            return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_registry(data: List[dict]):
    REGISTRY_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


@app.get("/")
def get_index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/algorithms")
def list_algorithms():
    registry = {item["algorithm_id"]: item for item in load_registry()}
    result = []
    for algo_id, instance in PLUGIN_INSTANCES.items():
        reg_info = registry.get(algo_id, {})
        result.append({
            "algorithm_id": algo_id,
            "display_name": instance.display_name,
            "category": instance.category,
            "description": instance.description,
            "source_reference": instance.source_reference,
            "license": instance.license,
            "status": reg_info.get("status", "ALGORITHM_RESEARCH"),
            "parameters": instance.get_parameter_specs(),
        })
    return result


@app.get("/api/samples")
def list_samples():
    samples = []
    # Project sample images in samples folder
    for path in sorted(SAMPLES_DIR.glob("*.*")):
        if path.suffix.lower() in [".png", ".jpg", ".jpeg", ".bmp", ".pgm"]:
            samples.append({
                "filename": path.name,
                "label": f"Sample: {path.name}",
                "path": str(path)
            })
    # Also link existing tuning comparison images if available
    tuning_dir = BASE_DIR.parents[0] / "output" / "tuning_comparison"
    if tuning_dir.exists():
        orig = tuning_dir / "original.png"
        if orig.exists() and not (SAMPLES_DIR / "original.png").exists():
            samples.insert(0, {
                "filename": "original.png",
                "label": "Benchmark 720p Original (tuning_comparison)",
                "path": str(orig)
            })
    return samples


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename
    target_path = SAMPLES_DIR / filename
    content = await file.read()
    target_path.write_bytes(content)
    return {"filename": filename, "status": "uploaded"}


class ProcessRequest(BaseModel):
    algorithm_id: str
    sample_filename: str
    parameters: Dict[str, Any]


def get_image_path(filename: str) -> Path:
    p = SAMPLES_DIR / filename
    if p.exists():
        return p
    # Fallback to tuning_comparison
    tuning_p = BASE_DIR.parents[0] / "output" / "tuning_comparison" / filename
    if tuning_p.exists():
        return tuning_p
    # Default fallback to first sample found
    samples = list(SAMPLES_DIR.glob("*.*"))
    if samples:
        return samples[0]
    raise HTTPException(status_code=404, detail="Sample image not found")


@app.post("/api/process")
def process_algorithm(req: ProcessRequest):
    if req.algorithm_id not in PLUGIN_INSTANCES:
        raise HTTPException(status_code=400, detail="Unknown algorithm")
    
    algo = PLUGIN_INSTANCES[req.algorithm_id]
    img_path = get_image_path(req.sample_filename)

    # Read image
    bgr = cv2.imdecode(np.fromfile(str(img_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise HTTPException(status_code=400, detail="Failed to decode image")
    
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w, c = rgb.shape

    # Process Visual Reference
    ref_rgb, ref_metrics = algo.process_visual_reference(rgb, req.parameters)

    # Process Hardware Equivalent
    hw_rgb, hw_metrics = algo.process_hardware_equivalent(rgb, req.parameters)

    # Compute difference heatmap
    diff_rgb = algo.compute_diff_heatmap(ref_rgb, hw_rgb)

    # Compute PSNR & MAE
    mse = np.mean((ref_rgb.astype(np.float64) - hw_rgb.astype(np.float64)) ** 2)
    psnr = 99.9 if mse < 1e-5 else round(10 * np.log10(255.0 ** 2 / mse), 2)
    mae = round(float(np.mean(np.abs(ref_rgb.astype(np.float64) - hw_rgb.astype(np.float64)))), 2)

    # Save to cache
    orig_cache = CACHE_DIR / "current_original.png"
    ref_cache = CACHE_DIR / "current_reference.png"
    hw_cache = CACHE_DIR / "current_hardware.png"
    diff_cache = CACHE_DIR / "current_diff.png"

    cv2.imwrite(str(orig_cache), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(ref_cache), cv2.cvtColor(ref_rgb, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(hw_cache), cv2.cvtColor(hw_rgb, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(diff_cache), cv2.cvtColor(diff_rgb, cv2.COLOR_RGB2BGR))

    return {
        "dimensions": f"{w}x{h}",
        "original_url": "/cache/current_original.png",
        "reference_url": "/cache/current_reference.png",
        "hardware_url": "/cache/current_hardware.png",
        "diff_url": "/cache/current_diff.png",
        "ref_metrics": ref_metrics,
        "hw_metrics": hw_metrics,
        "psnr": psnr,
        "mae": mae
    }


class CartoonCompareRequest(BaseModel):
    sample_filename: str
    parameters: Dict[str, Any] = {}


@app.post("/api/cartoon_compare")
def compare_cartoon(req: CartoonCompareRequest):
    """Render three software candidates from the same input and parameter set."""
    img_path = get_image_path(req.sample_filename)
    bgr = cv2.imdecode(np.fromfile(str(img_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise HTTPException(status_code=400, detail="Failed to decode image")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    algo = PLUGIN_INSTANCES["cartoon"]
    choices = [
        ("s3_luma", "保色亮度分层", "FPGA 候选：较适合；整数 Gaussian、Sobel、亮度偏移，需验证资源与时序"),
        ("s1_color", "RGB 色阶量化", "FPGA 候选：较适合；移位量化与流式 Sobel，颜色可能偏硬"),
        ("visual", "经典平滑描边", "FPGA 候选：暂不优先；双边滤波、自适应阈值硬件成本较高"),
    ]
    items = []
    for key, label, suitability in choices:
        params = dict(req.parameters)
        params["variant"] = key
        if key == "visual":
            out, metrics = algo.process_visual_reference(rgb, params)
        else:
            out, metrics = algo.process_hardware_equivalent(rgb, params)
        filename = f"cartoon_compare_{key}.png"
        cv2.imwrite(str(CACHE_DIR / filename), cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
        items.append({"id": key, "title": label, "suitability": suitability,
                      "url": f"/cache/{filename}", "metrics": metrics})
    return {"items": items, "sample": req.sample_filename,
            "note": "软件效果预览；FPGA 适配为架构判断，非本板资源或时序实测"}


@app.get("/api/gallery")
def get_gallery():
    gallery_items = []
    
    # Check work/output/cartoon_candidates
    candidates_dir = BASE_DIR.parents[0] / "output" / "cartoon_candidates"
    if candidates_dir.exists():
        for p in candidates_dir.glob("*.png"):
            gallery_items.append({
                "title": f"Candidate: {p.stem}",
                "url": f"/external_asset/cartoon_candidates/{p.name}"
            })
            
    # Check work/output/tuning_comparison
    tuning_dir = BASE_DIR.parents[0] / "output" / "tuning_comparison"
    if tuning_dir.exists():
        for p in tuning_dir.glob("*.png"):
            gallery_items.append({
                "title": f"Tuning: {p.stem}",
                "url": f"/external_asset/tuning_comparison/{p.name}"
            })

    return gallery_items


@app.get("/api/registry")
def get_registry():
    return load_registry()


class ApproveRequest(BaseModel):
    algorithm_id: str
    approved_version: str
    params: Dict[str, Any]


@app.post("/api/approve")
def approve_algorithm(req: ApproveRequest):
    registry = load_registry()
    updated = False
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    for item in registry:
        if item["algorithm_id"] == req.algorithm_id:
            item["status"] = "VISUAL_APPROVED"
            item["user_approved_version"] = req.approved_version
            item["frozen_params"] = req.params
            item.setdefault("history", []).append({
                "timestamp": now_str,
                "action": f"User visually approved version {req.approved_version}",
                "params": req.params
            })
            updated = True
            break
            
    if not updated:
        registry.append({
            "algorithm_id": req.algorithm_id,
            "display_name": req.algorithm_id,
            "status": "VISUAL_APPROVED",
            "user_approved_version": req.approved_version,
            "frozen_params": req.params,
            "history": [{"timestamp": now_str, "action": "Approved by user"}]
        })
        
    save_registry(registry)
    return {"status": "success", "approved_version": req.approved_version}


@app.post("/api/export")
def export_experiment(req: ProcessRequest):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    exp_dir = EXPORTS_DIR / f"exp_{req.algorithm_id}_{timestamp}"
    exp_dir.mkdir(parents=True, exist_ok=True)

    img_path = get_image_path(req.sample_filename)
    bgr = cv2.imdecode(np.fromfile(str(img_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    
    algo = PLUGIN_INSTANCES[req.algorithm_id]
    ref_rgb, ref_metrics = algo.process_visual_reference(rgb, req.parameters)
    hw_rgb, hw_metrics = algo.process_hardware_equivalent(rgb, req.parameters)

    # Save images
    cv2.imwrite(str(exp_dir / "input.png"), bgr)
    cv2.imwrite(str(exp_dir / "visual_reference.png"), cv2.cvtColor(ref_rgb, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(exp_dir / "hardware_equivalent.png"), cv2.cvtColor(hw_rgb, cv2.COLOR_RGB2BGR))

    # Save metadata JSON
    sample_hash = hashlib.sha256(bgr.tobytes()).hexdigest()[:16]
    exp_meta = {
        "algorithm_id": req.algorithm_id,
        "sample_filename": req.sample_filename,
        "sample_sha256": sample_hash,
        "parameters": req.parameters,
        "ref_metrics": ref_metrics,
        "hw_metrics": hw_metrics,
        "timestamp": timestamp,
        "note": "Software-first protocol experiment export"
    }
    (exp_dir / "experiment.json").write_text(json.dumps(exp_meta, indent=2), encoding="utf-8")

    return {"status": "success", "export_path": str(exp_dir)}


@app.post("/api/process_video")
def process_video(req: Dict[str, Any]):
    # Create a 30-frame animated test video using the current algorithm
    algo_id = req.get("algorithm_id", "cartoon")
    params = req.get("parameters", {})
    algo = PLUGIN_INSTANCES.get(algo_id, PLUGIN_INSTANCES["cartoon"])
    
    sample_path = get_image_path("sample_city.png")
    bgr = cv2.imdecode(np.fromfile(str(sample_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    h, w = bgr.shape[:2]
    
    # Scale down for fast web demo
    sw, sh = min(w, 640), min(h, 360)
    bgr = cv2.resize(bgr, (sw, sh))
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    video_out = CACHE_DIR / "animated_preview.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(str(video_out), fourcc, 15, (sw, sh))
    if not out.isOpened():
        # Fallback to mp4v
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(video_out), fourcc, 15, (sw, sh))

    for frame_idx in range(20):
        # Slightly modulate brightness or shift to simulate streaming camera
        shift = int(10 * np.sin(frame_idx * 0.3))
        shifted_rgb = np.clip(rgb.astype(np.int16) + shift, 0, 255).astype(np.uint8)
        hw_rgb, _ = algo.process_hardware_equivalent(shifted_rgb, params)
        out.write(cv2.cvtColor(hw_rgb, cv2.COLOR_RGB2BGR))

    out.release()
    return {"video_url": "/cache/animated_preview.mp4"}


# Serve static and cache files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/cache", StaticFiles(directory=CACHE_DIR), name="cache")
app.mount("/y1-assets", StaticFiles(directory=Y1_LAB_DIR), name="y1-assets")
app.mount("/y2-assets", StaticFiles(directory=Y2_LAB_DIR), name="y2-assets")

# Mount external output assets for candidate gallery
candidates_dir = BASE_DIR.parents[0] / "output" / "cartoon_candidates"
if candidates_dir.exists():
    app.mount("/external_asset/cartoon_candidates", StaticFiles(directory=candidates_dir), name="cartoon_candidates")

tuning_dir = BASE_DIR.parents[0] / "output" / "tuning_comparison"
if tuning_dir.exists():
    app.mount("/external_asset/tuning_comparison", StaticFiles(directory=tuning_dir), name="tuning_comparison")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8501, reload=True)
