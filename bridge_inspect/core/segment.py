           

                                          
                                      
                                       
                                           
                    

                                                       
                          
   

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .. import config as cfg
from .backend import Detection

ROI_MARGIN = 0.15                                       


def length_from_area_perimeter(area_px: float, perim_px: float) -> float:
                           

                                                
                                                   
                                           
                                        

                                        

                                                                
                                                 
                       

                                            
                                      
       
    if area_px <= 0:
        return 0.0
    disc = perim_px * perim_px - 16.0 * area_px
    return (perim_px + float(np.sqrt(disc))) / 4.0 if disc > 0 else perim_px / 4.0


def segmentable(cls_key: str) -> bool:
                                                    
    return cls_key in cfg.SEGMENT_CLASSES


def expand_roi(xyxy: tuple[float, float, float, float],
               w: int, h: int, margin: float = ROI_MARGIN) -> tuple[int, int, int, int]:
                                            
    x1, y1, x2, y2 = (float(v) for v in xyxy)
    bw, bh = x2 - x1, y2 - y1
    x1, x2 = x1 - bw * margin, x2 + bw * margin
    y1, y2 = y1 - bh * margin, y2 + bh * margin
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(w, int(np.ceil(x2))), min(h, int(np.ceil(y2)))
    return x1, y1, max(x2, x1 + 4), max(y2, y1 + 4)


@dataclass
class SegmentResult:
                         
    cls_key: str
    cls_name: str
    mask: np.ndarray                             
    px_area: int
    area_cm2: float
    perimeter_px: float
    max_width_mm: float
    conf: float
    gsd_mm_per_px: float
    length_mm: float = 0.0                        
    avg_width_mm: float = 0.0                      
    area_ratio: float = 0.0                      
    crack_count: int = 0                       

    @property
    def max_width_px(self) -> float:
        return self.max_width_mm / self.gsd_mm_per_px if self.gsd_mm_per_px else 0.0


def segment_fields(res: SegmentResult) -> dict:
                                            

                                          
                                          
                                           
                                                   
       
    return {
        "cls_key": res.cls_key, "cls_name": res.cls_name,
        "px_area": res.px_area, "area_cm2": res.area_cm2,
        "perimeter_px": res.perimeter_px, "max_width_mm": res.max_width_mm,
        "length_mm": res.length_mm, "avg_width_mm": res.avg_width_mm,
        "area_ratio": res.area_ratio, "crack_count": res.crack_count,
        "conf": res.conf,
    }


def quantify(mask: np.ndarray, distance_m: float, conf: float,
             cls_key: str) -> SegmentResult:
                                         

                                                         
                                         
                                              
       
    dc = cfg.DISEASE_BY_KEY.get(cls_key, cfg.DISEASES[0])
    gsd = cfg.gsd_mm_per_px(distance_m) if distance_m > 0 else 0.0

    m = (mask > 0).astype(np.uint8)
    px_area = int(m.sum())
    mh, mw = m.shape[:2]

    contours, _ = cv2.findContours(m * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    perimeter = float(sum(cv2.arcLength(c, True) for c in contours)) if contours else 0.0

    max_w_px = length_px = 0.0
    n_crack = 0
    if px_area > 0:
                                            
        max_w_px = float(cv2.distanceTransform(m, cv2.DIST_L2, 5).max()) * 2.0
                                                           
        length_px = length_from_area_perimeter(px_area, perimeter)
        n_crack = max(0, cv2.connectedComponents(m, 8)[0] - 1)

    px2mm = gsd
    return SegmentResult(
        cls_key=cls_key,
        cls_name=dc.name,
        mask=m * 255,
        px_area=px_area,
        area_cm2=round(px_area * (px2mm ** 2) / 100.0, 2) if px2mm else 0.0,
        perimeter_px=round(perimeter, 1),
        max_width_mm=round(max_w_px * px2mm, 2) if px2mm else 0.0,
        conf=conf,
        gsd_mm_per_px=round(gsd, 4),
        length_mm=round(length_px * px2mm, 2) if px2mm else 0.0,
                                          
                         
        avg_width_mm=(round(px_area * (px2mm ** 2) / (length_px * px2mm), 2)
                      if px2mm and length_px > 0 else 0.0),
        area_ratio=round(px_area / float(mw * mh), 6) if mw and mh else 0.0,
        crack_count=n_crack,
    )


                                                                            
class SegmentBackend(ABC):
                 

    name = "未知分割后端"
    mode = "demo"
    detail = ""

    @abstractmethod
    def segment(self, bgr: np.ndarray, det: Detection,
                distance_m: float) -> SegmentResult | None:
        pass                

    def describe(self) -> str:
        return f"{self.name} · {'演示模式' if self.mode == 'demo' else '模型推理'}{self.detail}"


class DemoSegmenter(SegmentBackend):
              

                                            
                                    
       

    name = "内置演示分割"
    mode = "demo"
    detail = "（未加载权重，结果为阈值分割，非模型推理）"

    def segment(self, bgr: np.ndarray, det: Detection,
                distance_m: float) -> SegmentResult | None:
        if bgr is None or bgr.size == 0:
            return None

                                            
                                               
        if not segmentable(det.cls_key):
            return None

                                            
                                       
        if det.gt_idx > 0:
            gt = self._gt_mask(bgr, det.gt_idx)
            if gt is not None:
                return quantify(gt, distance_m, det.conf, det.cls_key)

        h, w = bgr.shape[:2]
                                            
        x1, y1, x2, y2 = expand_roi(det.xyxy, w, h)
        roi = bgr[y1:y2, x1:x2]
        if roi.size == 0:
            return None

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        eq = clahe.apply(gray)

        block = max(15, (min(roi.shape[:2]) // 2) * 2 + 1)
        binimg = cv2.adaptiveThreshold(eq, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                       cv2.THRESH_BINARY_INV, block, 9)

                                          
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        binimg = cv2.morphologyEx(binimg, cv2.MORPH_CLOSE, k, iterations=2)

        n, labels, stats, _ = cv2.connectedComponentsWithStats(binimg, 8)
        if n <= 1:
            return None

                                            
        best_idx, best_score = -1, -1.0
        for i in range(1, n):
            area = int(stats[i, cv2.CC_STAT_AREA])
            if area < 12:
                continue
            bw = int(stats[i, cv2.CC_STAT_WIDTH])
            bh = int(stats[i, cv2.CC_STAT_HEIGHT])
            score = max(bw, bh) / max(1, min(bw, bh)) * np.sqrt(area)
            if score > best_score:
                best_idx, best_score = i, score
        if best_idx < 0:
            return None

        full = np.zeros((h, w), np.uint8)
        full[y1:y2, x1:x2] = np.where(labels == best_idx, 255, 0).astype(np.uint8)

        return quantify(full, distance_m, det.conf, det.cls_key)

    @staticmethod
    def _gt_mask(bgr: np.ndarray, label: int) -> np.ndarray | None:
                                                    
        from . import demo_data

        gt = demo_data.gt_lookup(bgr)
        if not gt:
            return None
        m = gt["mask"]
        if label > int(m.max()):
            return None
        return np.where(m == label, 255, 0).astype(np.uint8)


class RealSegmenter(SegmentBackend):
                      

                                                             
                                                
                                                
           
       

    mode = "model"

    def __init__(self, weights: str, device: str = "auto", img_size: int = 960):
        self.weights = weights
        self.device = device
        self.img_size = img_size
        self.name = Path(weights).stem
        self.detail = f"（Ultralytics-Seg · {Path(weights).name}）"
        from ultralytics import YOLO

        self._model = YOLO(weights)

    def _device(self) -> str:
        if self.device != "auto":
            return self.device
        try:
            import torch

            return "cuda:0" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def segment(self, bgr: np.ndarray, det: Detection,
                distance_m: float) -> SegmentResult | None:
                                
        if not segmentable(det.cls_key):
            return None
        res = self._model.predict(bgr, imgsz=self.img_size, verbose=False,
                                  device=self._device())[0]
        if res.masks is None or res.boxes is None:
            return None

        from .backend import normalize_class

        names = getattr(res, "names", {}) or {}
        best, best_iou = None, 0.0
        for i, b in enumerate(res.boxes):
            bx1, by1, bx2, by2 = (float(v) for v in b.xyxy[0].tolist())
            iou = _iou(det.xyxy, (bx1, by1, bx2, by2))
            if iou > best_iou:
                best_iou, best = iou, i
        if best is None or best_iou < 0.1:
            return None

        m = res.masks.data[best].cpu().numpy()
        h, w = bgr.shape[:2]
        m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
        mask = (m > 0.5).astype(np.uint8) * 255

        raw = str(names.get(int(res.boxes[best].cls[0]), det.cls_key))
        key = normalize_class(raw)
        conf = float(res.boxes[best].conf[0])
        return quantify(mask, distance_m, conf, key)


class CrackUNetSegmenter(SegmentBackend):
                                                                      

    mode = "model"

    def __init__(self, weights: str, device: str = "auto", **_kw):
        self.weights = weights
        self.name = "crack-seg U-Net v3"
        self.detail = f"（公开裂缝分割权重 · {Path(weights).name}）"
        from .crack_unet import get_runtime
        self._runtime = get_runtime(weights, device)

    def segment(self, bgr: np.ndarray, det: Detection,
                distance_m: float) -> SegmentResult | None:
        if not segmentable(det.cls_key):
            return None
        mask, prob = self._runtime.predict(bgr)
                                                                            
                                                                          
                                                                           
                                                                     
        h, w = mask.shape[:2]
        x1, y1, x2, y2 = expand_roi(det.xyxy, w, h)
        instance = np.zeros_like(mask)
        instance[y1:y2, x1:x2] = mask[y1:y2, x1:x2]
        if not np.any(instance):
            return None
        confidence = float(prob[instance > 0].mean())
        return quantify(instance, distance_m, round(min(confidence, 0.99), 2), "crack")


def _iou(a: tuple, b: tuple) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    ua = ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)
    return inter / ua if ua > 0 else 0.0


                                                                            
def make_segmenter(settings: dict | None = None) -> SegmentBackend:
                                    
    s = settings or cfg.load_settings()
    from .backend import resolve_weights

    path = resolve_weights("segment_weights", seg=True)
    if path:
        try:
            if Path(path).suffix.lower() == ".pth":
                return CrackUNetSegmenter(path, device=s.get("device", "auto"))
            return RealSegmenter(path, device=s.get("device", "auto"),
                                 img_size=int(s.get("img_size", 960)))
        except Exception as exc:
            demo = DemoSegmenter()
            demo.detail = f"（权重加载失败：{exc}，已回退演示分割）"
            return demo
    return DemoSegmenter()
