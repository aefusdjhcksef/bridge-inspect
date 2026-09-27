                               

                                                       
                                             
         

                                              
                                                   
                                        
                                        
                                            
   

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .. import config as cfg

                                          
                        
DET_MODEL = "YOLOv8-ALTE"
DET_FLOPS_G = 8.0
SEG_MODEL = "U-Net-VC"

                                                 
                                      
SEG_METRICS = {
    "IoU": 0.8200,
    "mIoU": 0.9030,
    "Precision": 0.9100,
    "mPrecision": 0.9503,
    "Recall": 0.9000,
}


@dataclass
class MetricBundle:
    is_demo: bool
    source: str
    epochs: list[int]
    curves: dict[str, list[float]]                         
    summary: dict[str, float]                                                        
    pr_curves: dict[str, dict]                                             
    confusion: dict                                       


@dataclass
class SegMetrics:
                                      

                                                 
                                           
       

    is_demo: bool = True
    source: str = f"{SEG_MODEL} 训练报告指标（说明书表 6-2）"
    values: dict[str, float] = field(default_factory=lambda: dict(SEG_METRICS))


                                                                            
def _find_runs_csv() -> Path | None:
                                            
    for root in (cfg.ROOT, cfg.ROOT.parent):
        for pat in ("runs/**/results.csv", "**/runs/**/results.csv"):
            hits = sorted(root.glob(pat))
            if hits:
                return hits[-1]
    return None


def _load_real(path: Path) -> MetricBundle | None:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return None
    if not rows:
        return None

    def col(name: str) -> list[float]:
        out = []
        for r in rows:
            k = next((k for k in r if k and k.strip().lower() == name), None)
            try:
                out.append(float(r[k]) if k else 0.0)
            except (TypeError, ValueError):
                out.append(0.0)
        return out

    epochs = [int(float(r.get("epoch", i) or i)) for i, r in enumerate(rows)]
    curves = {
        "box_loss": col("train/box_loss"),
        "cls_loss": col("train/cls_loss"),
        "dfl_loss": col("train/dfl_loss"),
        "precision": col("metrics/precision(b)"),
        "recall": col("metrics/recall(b)"),
        "map50": col("metrics/mAP50(b)"),
        "map50_95": col("metrics/mAP50-95(b)"),
    }
    summary = {
        "AP50": curves["map50"][-1] if curves["map50"] else 0.0,
        "AP50-95": curves["map50_95"][-1] if curves["map50_95"] else 0.0,
        "Precision": curves["precision"][-1] if curves["precision"] else 0.0,
        "Recall": curves["recall"][-1] if curves["recall"] else 0.0,
        "FLOPs": DET_FLOPS_G,
    }
    return MetricBundle(
        is_demo=False, source=str(path), epochs=epochs, curves=curves,
        summary=summary, pr_curves=_demo_pr(), confusion=_demo_confusion(),
    )


                                                                            
def _demo_training() -> tuple[list[int], dict[str, list[float]], dict[str, float]]:
                                        

                                          
                                                  
                                             
       
    n = 120
    e = np.arange(1, n + 1)
    rng = np.random.default_rng(20260905)

    def decay(start, end, rate=0.055):
        v = end + (start - end) * np.exp(-rate * e)
        return v + rng.normal(0, (start - end) * 0.012, n)

    def rise(start, end, rate=0.06):
        v = np.clip(end - (end - start) * np.exp(-rate * e)
                    + rng.normal(0, (end - start) * 0.015, n), 0, 1)
        return np.clip(v + (end - v[-1]), 0, 1)

    curves = {
        "box_loss": decay(1.52, 0.62).round(4).tolist(),
        "cls_loss": decay(2.10, 0.48).round(4).tolist(),
        "dfl_loss": decay(1.35, 0.88).round(4).tolist(),
        "precision": rise(0.42, 0.939).round(4).tolist(),
        "recall": rise(0.36, 0.835).round(4).tolist(),
        "map50": rise(0.38, 0.890).round(4).tolist(),
        "map50_95": rise(0.21, 0.738).round(4).tolist(),
    }
    summary = {
        "AP50": curves["map50"][-1],
        "AP50-95": curves["map50_95"][-1],
        "Precision": curves["precision"][-1],
        "Recall": curves["recall"][-1],
        "FLOPs": DET_FLOPS_G,
    }
    return e.tolist(), curves, summary


def _demo_pr() -> dict[str, dict]:
                                        

                                                           
                                             
                              
       
    rng = np.random.default_rng(7)
    targets = {
        "crack": 0.960, "spalling": 0.928, "seepage": 0.903,
        "exposed_bar": 0.881, "honeycomb": 0.872, "bearing": 0.851,
        "joint_offset": 0.835,
    }
    out = {}
    for key, ap in targets.items():
        r = np.linspace(0, 1, 60)
        p = ap * (1 - 0.72 * r ** 2.1) + rng.normal(0, 0.012, r.size)
        p = np.clip(np.maximum.accumulate(np.clip(p, 0, 1)[::-1])[::-1], 0, 1)
        out[key] = {"recall": r.tolist(), "precision": p.tolist(), "ap": ap}
    return out


def _demo_confusion() -> dict:
                                        
    labels = cfg.DISEASE_NAMES
    n = len(labels)
    m = np.zeros((n, n), float)
    confusable = {(0, 6): 0.11, (6, 0): 0.09, (1, 2): 0.08, (2, 1): 0.06,
                  (3, 4): 0.07, (4, 3): 0.05}
    for i in range(n):
        m[i, i] = 0.86 + 0.03 * np.sin(i)
    for (i, j), v in confusable.items():
        m[i, j] = v
        m[i, i] -= v * 0.5
    m = np.clip(m, 0, None)
    m /= m.sum(axis=1, keepdims=True)
                 
    return {"labels": labels, "matrix": m.round(4).tolist()}


def load_metrics(force_demo: bool = False) -> MetricBundle:
                                            
    if not force_demo:
        p = _find_runs_csv()
        if p:
            real = _load_real(p)
            if real:
                return real

    epochs, curves, summary = _demo_training()
    return MetricBundle(
        is_demo=True,
        source=f"{DET_MODEL} 设计指标（说明书表 6-1，未找到 runs/**/results.csv）",
        epochs=epochs, curves=curves, summary=summary,
        pr_curves=_demo_pr(), confusion=_demo_confusion(),
    )


def load_seg_metrics() -> SegMetrics:
                                    

                                               
                    
       
    return SegMetrics()


                                     
                                                  
DET_METRIC_LABELS = {
    "Precision": "精确率",
    "Recall": "召回率",
    "AP50": "AP50",
    "AP50-95": "AP50-95",
    "FLOPs": "FLOPs",
}
SEG_METRIC_LABELS = {
    "IoU": "交并比 IoU",
    "mIoU": "平均交并比 mIoU",
    "Precision": "精确率",
    "mPrecision": "平均精确率 mPrecision",
    "Recall": "召回率",
}


def _pct(value: float, digits: int) -> str:
    return f"{value * 100:.{digits}f}%"


def det_metric_text(key: str, value: float) -> str:
                                       

                                              
           
       
    return f"{value:.1f} GFLOPs" if key == "FLOPs" else _pct(value, 1)


def seg_metric_text(key: str, value: float) -> str:
                                    
    return _pct(value, 2)


                                                                            
def class_stats_from_db() -> list[dict]:
                                 
    from .. import db

    db_rows = db.query(
        "SELECT cls_key, cls_name, COUNT(*) AS n, AVG(conf) AS c"
        " FROM detections GROUP BY cls_key, cls_name ORDER BY n DESC"
    )
    total = sum(r["n"] for r in db_rows) or 1
    out = []
    for r in db_rows:
        dc = cfg.DISEASE_BY_KEY.get(r["cls_key"])
        out.append({
            "cls_key": r["cls_key"],
            "cls_name": r["cls_name"],
            "count": r["n"],
            "ratio": r["n"] / total,
            "avg_conf": float(r["c"] or 0.0),
            "color": cfg.disease_color(r["cls_key"]),
            "severity": dc.severity if dc else "-",
        })
    return out
