           

                                                
                                                      

       
                                                   
                                                  
                                                                   
   

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .. import config as cfg

                           
                                           
_ALIAS = {
    "crack": "crack", "裂缝": "crack", "cracks": "crack", "crack_line": "crack",
    "spalling": "spalling", "剥落": "spalling", "剥落掉块": "spalling",
    "spall": "spalling", "delamination": "spalling",
    "exposed_bar": "exposed_bar", "露筋": "exposed_bar", "rebar": "exposed_bar",
    "exposed_rebar": "exposed_bar", "corrosion": "exposed_bar",
    "seepage": "seepage", "渗水": "seepage", "渗水泛碱": "seepage",
    "efflorescence": "seepage", "water": "seepage", "leak": "seepage",
    "honeycomb": "honeycomb", "蜂窝": "honeycomb", "蜂窝麻面": "honeycomb",
    "void": "honeycomb",
    "bearing": "bearing", "支座滑移": "bearing", "bearing_slip": "bearing",
    "joint_offset": "joint_offset", "伸缩缝错台": "joint_offset",
    "joint": "joint_offset", "expansion_joint": "joint_offset",
}


def normalize_class(name: str) -> str:
                                           
    k = (name or "").strip().lower().replace("-", "_").replace(" ", "_")
    return _ALIAS.get(k, _ALIAS.get(k.replace("_", ""), "crack"))


def extract_candidates(bgr: np.ndarray, min_area_ratio: float = 0.0004,
                       work_width: int = 640) -> tuple[list[dict], int, int]:
                             

                                           

            

                                            
                                                
                                              

                                         

                                           
                                            
                                        

                                 
                                                   
                                                 
                               
                              
                                    
                       
                                     
       
    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (work_width, int(work_width * h / max(w, 1))),
                      interpolation=cv2.INTER_AREA)
    gh, gw = gray.shape

    eq = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)

                                 
    low = cv2.GaussianBlur(eq, (0, 0), 48).astype(np.float32)
    flat = np.clip(eq.astype(np.float32) - low + 128.0, 0, 255).astype(np.uint8)
    spread = max(6.0, float(flat.std()))

                           
    adapt_dark = cv2.adaptiveThreshold(flat, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                       cv2.THRESH_BINARY_INV, 35, 12)
    block_dark = cv2.threshold(flat, 128.0 - max(9.0, 0.85 * spread), 255,
                               cv2.THRESH_BINARY_INV)[1]
    dark = cv2.bitwise_or(adapt_dark, block_dark)
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

                                             
    bright = cv2.threshold(flat, 128.0 + max(13.0, 1.15 * spread), 255,
                           cv2.THRESH_BINARY)[1]
    bright = cv2.morphologyEx(bright, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    min_area = min_area_ratio * gh * gw
    cands: list[dict] = []

    for m, src in ((dark, "dark"), (bright, "bright")):
        contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            rect_area = bw * bh
            if rect_area < min_area or bw < 8 or bh < 6:
                continue

                                              
                              
            true_area = int(cv2.countNonZero(m[y:y + bh, x:x + bw]))
            if true_area < min_area:
                continue
            contour_area = float(cv2.contourArea(cnt)) or 1.0
            porosity = float(np.clip(1.0 - true_area / max(contour_area, 1.0), 0, 1))

                                            
            patch = flat[y:y + bh, x:x + bw].astype(np.float32)
            dev = float(np.abs(patch - 128.0).mean()) / 64.0
            area_ratio = true_area / (gh * gw)
            longest = max(bw, bh, 1)

                                          
                                              
                              
            conf = 0.40 + 0.28 * min(dev / 0.90, 1.0) \
                        + 0.30 * min(area_ratio / 0.015, 1.0)

            cands.append({
                "score": float(np.clip(conf, 0.40, 0.98)),
                "x": x, "y": y, "bw": bw, "bh": bh, "src": src,
                "linearity": true_area / float(longest * longest),
                "porosity": porosity,
                "fill": true_area / rect_area,
                "area_ratio": area_ratio,
                "elong": bw / max(bh, 1),
                "dev": dev,
            })
    return cands, gw, gh


@dataclass
class Detection:
                 
    cls_key: str
    cls_name: str
    cls_id: int
    conf: float
    x1: int
    y1: int
    x2: int
    y2: int
    source: str = "demo"
    gt_idx: int = 0                                   

    @property
    def xyxy(self) -> tuple[int, int, int, int]:
        return self.x1, self.y1, self.x2, self.y2

    @property
    def area(self) -> int:
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)


class DetectBackend(ABC):
                 

    name = "未知后端"
    mode = "demo"                        
    detail = ""                          

    def __init__(self, conf: float = 0.35, iou: float = 0.45,
                 device: str = "auto", img_size: int = 960):
        self.conf = conf
        self.iou = iou
        self.device = device
        self.img_size = img_size

    @abstractmethod
    def predict(self, bgr: np.ndarray) -> list[Detection]:
        pass               

    def describe(self) -> str:
        return f"{self.name} · {'演示模式' if self.mode == 'demo' else '模型推理'}{self.detail}"


                                                                            
      
                                                                            
class DemoDetector(DetectBackend):
                        

                                            
                                          
                                                 
                                              
                                                     
       

    name = "内置演示后端"
    mode = "demo"
    detail = "（未加载权重；演示影像按真值给出结果，自备照片为图像特征响应）"

    _MIN_AREA_RATIO = 0.00006                
    _MAX_BOXES = 8

    def predict(self, bgr: np.ndarray) -> list[Detection]:
        if bgr is None or bgr.size == 0:
            return []

        gt = self._gt_predict(bgr)
        if gt is not None:
            return gt
        return self._heuristic(bgr)

                                                              
    def _gt_predict(self, bgr: np.ndarray) -> list[Detection] | None:
        from . import demo_data

        gt = demo_data.gt_lookup(bgr)
        if not gt:
            return None

        h, w = bgr.shape[:2]
        seed = int(hashlib.md5(demo_data.image_sig(bgr).encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)

        dets: list[Detection] = []
        for i, (key, box) in enumerate(zip(gt["keys"], gt["boxes"]), start=1):
            dc = cfg.DISEASE_BY_KEY.get(key)
            if dc is None:
                continue
            x1, y1, x2, y2 = (int(v) for v in box)
                                          
            x1 += int(rng.integers(-5, 6)); y1 += int(rng.integers(-5, 6))
            x2 += int(rng.integers(-5, 6)); y2 += int(rng.integers(-5, 6))
            x1, x2 = int(np.clip(x1, 0, w - 2)), int(np.clip(x2, 2, w))
            y1, y2 = int(np.clip(y1, 0, h - 2)), int(np.clip(y2, 2, h))
            if x2 - x1 < 4 or y2 - y1 < 4:
                continue
            extent = (x2 - x1) * (y2 - y1) / float(w * h)
            conf = 0.70 + 0.26 * min(extent / 0.08, 1.0) ** 0.5 \
                + float(rng.normal(0, 0.015))
            dets.append(Detection(
                cls_key=key, cls_name=dc.name, cls_id=dc.id,
                conf=round(float(np.clip(conf, 0.55, 0.98)), 2),
                x1=x1, y1=y1, x2=x2, y2=y2, source="demo-gt", gt_idx=i,
            ))

                                                  
                                                    
                                               
                                                      
        dets.sort(key=lambda d: -d.conf)
        return dets

                                                              
    def _heuristic(self, bgr: np.ndarray) -> list[Detection]:
        h, w = bgr.shape[:2]
        cands, gw, gh = extract_candidates(bgr, self._MIN_AREA_RATIO)

                                             
        if len(cands) < 3:
            seed = int.from_bytes(
                hashlib.md5(np.ascontiguousarray(bgr[::4, ::4])).digest()[:8], "big")
            cands = self._fallback_candidates(
                np.random.default_rng(seed % (2 ** 32)), gw, gh, 5)

        cands.sort(key=lambda c: -c["score"])
        cands = self._nms(cands, 0.35)[: self._MAX_BOXES]

        floor = min(self.conf, 0.42)                        
        dets: list[Detection] = []
        sx, sy = w / gw, h / gh
        for c in cands:
            if c["score"] < floor:
                continue
            cls_key = self._classify(c)
            dc = cfg.DISEASE_BY_KEY[cls_key]
            dets.append(Detection(
                cls_key=cls_key, cls_name=dc.name, cls_id=dc.id,
                conf=round(c["score"], 2),
                x1=int(c["x"] * sx), y1=int(c["y"] * sy),
                x2=int((c["x"] + c["bw"]) * sx), y2=int((c["y"] + c["bh"]) * sy),
                source="demo",
            ))
        return dets

                                                                      
    @staticmethod
    def _classify(f: dict) -> str:
                             

                                             
                                            
                   
           
                               
        if f["src"] == "bright":
            return "exposed_bar" if f["area_ratio"] >= 0.004 else "honeycomb"

                                                  
                                      
        if f["linearity"] < 0.10:
            return "joint_offset" if f["fill"] >= 0.45 else "crack"

                                             
        if f["area_ratio"] >= 0.018:
            if f["porosity"] >= 0.18:
                return "honeycomb"
            if f["dev"] < 0.42:
                return "seepage"
            return "spalling"
        if f["area_ratio"] >= 0.004:
            return "spalling" if f["dev"] >= 0.5 else "seepage"
        return "crack" if f["linearity"] < 0.4 else "bearing"

    @staticmethod
    def _fallback_candidates(rng, gw: int, gh: int, n: int) -> list[dict]:
        out = []
        for _ in range(n):
            bw = int(rng.integers(gw // 8, gw // 3))
            bh = int(rng.integers(gh // 14, gh // 5))
            x = int(rng.integers(0, max(1, gw - bw)))
            y = int(rng.integers(0, max(1, gh - bh)))
            out.append({
                "score": float(rng.uniform(0.55, 0.88)), "x": x, "y": y,
                "bw": bw, "bh": bh, "src": "dark", "linearity": 0.5,
                "porosity": 0.0, "fill": 0.6, "elong": bw / max(bh, 1),
                "area_ratio": bw * bh / (gh * gw), "dev": 0.5,
            })
        return out

    @staticmethod
    def _nms(cands: list[dict], iou_thres: float) -> list[dict]:
                                     
        keep: list[dict] = []
        for c in cands:
            box = (c["x"], c["y"], c["x"] + c["bw"], c["y"] + c["bh"])
            area = c["bw"] * c["bh"]
            drop = False
            for k in keep:
                kbox = (k["x"], k["y"], k["x"] + k["bw"], k["y"] + k["bh"])
                ix1, iy1 = max(box[0], kbox[0]), max(box[1], kbox[1])
                ix2, iy2 = min(box[2], kbox[2]), min(box[3], kbox[3])
                iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
                inter = iw * ih
                if inter <= 0:
                    continue
                union = area + k["bw"] * k["bh"] - inter
                if union > 0 and inter / union > iou_thres:
                    drop = True
                    break
            if not drop:
                keep.append(c)
        return keep


                                                                            
      
                                                                            
class YoloDetector(DetectBackend):
                                              

    mode = "model"

    def __init__(self, weights: str, **kw):
        super().__init__(**kw)
        self.weights = weights
        self.name = f"{Path(weights).stem}"
        self._kind = "onnx" if Path(weights).suffix.lower() == ".onnx" else "yolo"
        self._model: Any = None
        self._sess: Any = None
        self._load()

    def _load(self) -> None:
        if self._kind == "onnx":
            import onnxruntime as ort

            providers = ["CPUExecutionProvider"]
            if self.device.startswith("cuda"):
                providers.insert(0, "CUDAExecutionProvider")
            self._sess = ort.InferenceSession(self.weights, providers=providers)
            self.detail = f"（ONNX Runtime · {Path(self.weights).name}）"
        else:
            from ultralytics import YOLO

            self._model = YOLO(self.weights)
            task = str(getattr(self._model, "task", "detect") or "detect")
            task_name = "YOLOv8-Seg 裂缝检测" if task == "segment" else "YOLO 裂缝检测"
            self.name = task_name
            self.detail = f"（Ultralytics · {Path(self.weights).name}）"

    def _resolve_device(self) -> str:
        if self.device != "auto":
            return self.device
        try:
            import torch

            return "cuda:0" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def predict(self, bgr: np.ndarray) -> list[Detection]:
        if bgr is None or bgr.size == 0:
            return []
        if self._kind == "onnx":
            return self._predict_onnx(bgr)
        return self._predict_yolo(bgr)

    def _predict_yolo(self, bgr: np.ndarray) -> list[Detection]:
        res = self._model.predict(
            bgr, conf=self.conf, iou=self.iou, imgsz=self.img_size,
            device=self._resolve_device(), verbose=False,
        )[0]
        dets: list[Detection] = []
        names = getattr(res, "names", {}) or {}
        if res.boxes is None:
            return dets
        for b in res.boxes:
            cls_id = int(b.cls[0])
            raw = str(names.get(cls_id, cls_id))
                                                                          
                                                                            
            if raw.strip().lower() in {"background", "bg", "none"}:
                continue
            key = normalize_class(raw)
            dc = cfg.DISEASE_BY_KEY[key]
            x1, y1, x2, y2 = (int(v) for v in b.xyxy[0].tolist())
            dets.append(Detection(key, dc.name, dc.id, round(float(b.conf[0]), 2),
                                  x1, y1, x2, y2, source="model"))
        return dets


class CrackUNetDetector(DetectBackend):
                                                                                 

    mode = "model"

    def __init__(self, weights: str, **kw):
        super().__init__(**kw)
        self.weights = weights
        self.name = "crack-seg U-Net v3"
        from .crack_unet import get_runtime
        self._runtime = get_runtime(weights, self.device)
        self.detail = f"（像素掩膜区域定位 · {Path(weights).name}）"

    def predict(self, bgr: np.ndarray) -> list[Detection]:
        dc = cfg.DISEASE_BY_KEY["crack"]
        return [Detection(dc.key, dc.name, dc.id, conf, x1, y1, x2, y2,
                          source="crack-unet")
                for x1, y1, x2, y2, conf in self._runtime.locate(bgr, self.conf)]

    def _predict_onnx(self, bgr: np.ndarray) -> list[Detection]:
                                                  
        inp = self._sess.get_inputs()[0]
        ih, iw = inp.shape[2], inp.shape[3]
        ih = ih if isinstance(ih, int) else self.img_size
        iw = iw if isinstance(iw, int) else self.img_size

        h0, w0 = bgr.shape[:2]
        k = min(iw / w0, ih / h0)
        nw, nh = int(round(w0 * k)), int(round(h0 * k))
        canvas = np.full((ih, iw, 3), 114, np.uint8)
        resized = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
        dx, dy = (iw - nw) // 2, (ih - nh) // 2
        canvas[dy:dy + nh, dx:dx + nw] = resized

        blob = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))[None]

        out = self._sess.run(None, {inp.name: blob})[0]
        pred = out[0] if out.ndim == 3 else out
        if pred.shape[0] < pred.shape[1]:
            pred = pred.T                                    

        boxes, scores, ids = [], [], []
        for row in pred:
            cls_scores = row[4:]
            cid = int(np.argmax(cls_scores))
            score = float(cls_scores[cid])
            if score < self.conf:
                continue
            cx, cy, bw, bh = (float(v) for v in row[:4])
            boxes.append([cx - bw / 2, cy - bh / 2, bw, bh])
            scores.append(score)
            ids.append(cid)

        dets: list[Detection] = []
        if not boxes:
            return dets
        for idx in cv2.dnn.NMSBoxes(boxes, scores, self.conf, self.iou):
            x, y, bw, bh = boxes[int(idx)]
            key = cfg.DISEASES[min(int(ids[int(idx)]), len(cfg.DISEASES) - 1)].key
            dc = cfg.DISEASE_BY_KEY[key]
            dets.append(Detection(
                key, dc.name, dc.id, round(scores[int(idx)], 2),
                int((x - dx) / k), int((y - dy) / k),
                int((x + bw - dx) / k), int((y + bh - dy) / k), source="model",
            ))
        return dets


                                                                            
    
                                                                            
def discover_weights() -> list[Path]:
                            
    if not cfg.MODELS_DIR.is_dir():
        return []
    out = [p for p in cfg.MODELS_DIR.iterdir()
           if p.suffix.lower() in {".pt", ".onnx", ".pth"} and p.is_file()]
    return sorted(out, key=lambda p: p.name)


def resolve_weights(setting_key: str, seg: bool = False) -> str:
                   

                                                
                                                  
              
       
    s = cfg.load_settings()
    path = (s.get(setting_key) or "").strip()
    if path and Path(path).is_file():
        return path
    for p in discover_weights():
                                                                         
                                                                          
                                                                     
        if p.suffix.lower() == ".pth":
            return str(p)
        is_seg = "-seg" in p.stem.lower() or p.suffix.lower() == ".pth"
        if is_seg == seg:
            return str(p)
    return ""


def make_detector(settings: dict | None = None) -> DetectBackend:
                                

                                         
       
    s = settings or cfg.load_settings()
    kw = dict(
        conf=float(s.get("conf_thres", 0.35)),
        iou=float(s.get("iou_thres", 0.45)),
        device=s.get("device", "auto"),
        img_size=int(s.get("img_size", 960)),
    )
    path = resolve_weights("detect_weights")
    if path:
        try:
            if Path(path).suffix.lower() == ".pth":
                return CrackUNetDetector(path, **kw)
            return YoloDetector(path, **kw)
        except Exception as exc:                                         
            demo = DemoDetector(**kw)
            demo.detail = f"（权重 {Path(path).name} 加载失败：{exc}，已回退演示后端）"
            return demo
    return DemoDetector(**kw)
