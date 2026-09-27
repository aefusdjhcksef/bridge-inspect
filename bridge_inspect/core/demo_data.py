             

                                         
                                          
      

                                          
                                                         
                             

                                           
                                        
                                         
   

from __future__ import annotations

import hashlib

import cv2
import numpy as np

from .. import config as cfg
from .. import db
from . import imgutil
from .backend import Detection, DemoDetector
from .segment import DemoSegmenter, segment_fields

IMG_W, IMG_H = 1280, 900

                                          
DEMO_POINTS: list[tuple[str, float, str, float]] = [
    ("A01", 1.8, "crack",        0.85),
    ("A03", 2.0, "spalling",     0.30),
    ("B02", 1.5, "crack",        1.00),
    ("B05", 1.6, "seepage",      0.55),
    ("C01", 1.2, "exposed_bar",  0.75),
    ("C03", 1.4, "joint_offset", 0.12),
    ("D02", 2.5, "crack",        0.92),
    ("D05", 2.4, "honeycomb",    0.42),
]

                                      
DAMAGE_BY_BATCH = {"P1": 0.35, "P2": 0.62, "P3": 1.00}


def _damage_of(point_id: str, batch_id: str) -> float:
                     

                                           
                                        
                                           
                                    

                                              
                            
       
    rate = next((r for pid, _, _, r in DEMO_POINTS if pid == point_id), 0.6)
                                                  
    return 1.0 - rate * (1.0 - DAMAGE_BY_BATCH[batch_id])


                               
                                           
DARK_SPALLING = 58.0
DARK_SEEPAGE = 20.0
DARK_HONEYCOMB = 52.0
DARK_CRACK = 46.0
DARK_JOINT = 62.0

                                
_JOINT_INSET = 24


def _seed(*parts) -> int:
                                              
                   
    key = "|".join(str(p) for p in parts).encode("utf-8")
    return int.from_bytes(hashlib.md5(key).digest()[:4], "big")


                                                                            
         
                                                                            
def _concrete_base(rng: np.random.Generator, tone: int = 150) -> np.ndarray:
                               
    base = np.full((IMG_H, IMG_W), float(tone), np.float32)
    small = rng.normal(0, 13, (IMG_H // 64 + 2, IMG_W // 64 + 2)).astype(np.float32)
    base += cv2.resize(small, (IMG_W, IMG_H), interpolation=cv2.INTER_CUBIC)
    base += rng.normal(0, 5.0, (IMG_H, IMG_W)).astype(np.float32)
    return np.clip(base, 0, 255)


def _add_structure(img: np.ndarray, rng: np.random.Generator, prefix: str) -> None:
                                      
    if prefix == "A":                                     
        for _ in range(int(rng.integers(2, 5))):
            x = int(rng.integers(60, IMG_W - 60))
            cv2.line(img, (x, 0), (x + int(rng.integers(-14, 14)), IMG_H),
                     float(rng.uniform(0, 10)), int(rng.integers(1, 3)))
        img[:70, :] -= 24
        img[-55:, :] -= 30
    elif prefix == "B":                            
        for _ in range(int(rng.integers(2, 5))):
            y = int(rng.integers(80, IMG_H - 80))
            cv2.line(img, (0, y), (IMG_W, y + int(rng.integers(-12, 12))),
                     float(rng.uniform(0, 10)), int(rng.integers(1, 3)))
        img[:, :85] -= 38
        img[:, -85:] -= 38
    elif prefix == "C":                                   
        mid = IMG_H // 2
        img[mid - 130:mid - 30] += 16
        img[mid - 30:mid + 30] -= 26
        img[mid + 30:mid + 140] += 9
        cv2.line(img, (0, mid - 30), (IMG_W, mid - 28), -34, 3)
    elif prefix == "D":                          
        for _ in range(int(rng.integers(2, 5))):
            y = int(rng.integers(90, IMG_H - 90))
            cv2.line(img, (0, y), (IMG_W, y + int(rng.integers(-10, 10))),
                     float(rng.uniform(0, 10)), int(rng.integers(1, 3)))
        img[:100, :] -= 22
    else:
        for _ in range(int(rng.integers(2, 5))):
            x = int(rng.integers(60, IMG_W - 60))
            cv2.line(img, (x, 0), (x, IMG_H), float(rng.uniform(0, 10)), 2)

         
    for _ in range(int(rng.integers(2, 5))):
        cx, cy = int(rng.integers(50, IMG_W - 50)), int(rng.integers(50, IMG_H - 50))
        cv2.circle(img, (cx, cy), int(rng.integers(5, 8)),
                   float(rng.uniform(0, 14)), -1)


                                                                            
       
                                                                            
                                 
_CRACK_LEN_MIN, _CRACK_LEN_SPAN = 200.0, 620.0
_CRACK_LEN_MAX = _CRACK_LEN_MIN + _CRACK_LEN_SPAN
_CRACK_STEP_PX = 24.0                   
_CRACK_EDGE_PX = 6                           


def _crack_walk(rng: np.random.Generator, x: float, y: float,
                base_ang: float, steps: int) -> list[tuple[float, float]]:
                                                 

                                                
                                       
       
    dev = 0.0
    pts = [(x, y)]
    for _ in range(steps):
        dev = float(np.clip(dev + rng.normal(0, 0.22), -0.5, 0.5))
        ang = base_ang + dev
        x += float(np.cos(ang) * _CRACK_STEP_PX)
        y += float(np.sin(ang) * _CRACK_STEP_PX)
        pts.append((x, y))
    return pts


def _draw_crack(img: np.ndarray, rng: np.random.Generator, dmg: float,
                mask: np.ndarray | None = None, label: int = 1) -> None:
              

                                            
                                      

                                                 
                                                  
                                                  
                                           
       
    base_ang = np.pi / 2 + float(rng.uniform(-0.55, 0.55))
    x0 = float(rng.integers(160, IMG_W - 320))
    y0 = float(rng.integers(160, IMG_H - 320))

                                              
                                              
    pts_max = _crack_walk(rng, x0, y0, base_ang,
                          max(6, int(_CRACK_LEN_MAX / _CRACK_STEP_PX)))
    xs = [p[0] for p in pts_max]
    ys = [p[1] for p in pts_max]
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
                                             
    slack_x = max(0.0, (IMG_W - bw) / 2.0 - _CRACK_EDGE_PX)
    slack_y = max(0.0, (IMG_H - bh) / 2.0 - _CRACK_EDGE_PX)
    dx = (IMG_W - bw) / 2.0 - min(xs) + float(rng.uniform(-slack_x, slack_x))
    dy = (IMG_H - bh) / 2.0 - min(ys) + float(rng.uniform(-slack_y, slack_y))

    length = _CRACK_LEN_MIN + _CRACK_LEN_SPAN * dmg
    width = max(2, int(round(1.5 + 2.5 * dmg)))
    steps = max(6, int(length / _CRACK_STEP_PX))
                                             
    pts = [(px + dx, py + dy) for px, py in pts_max[:steps + 1]]

                                    
    segs: list[tuple[tuple[int, int], tuple[int, int], int]] = []
    for i in range(len(pts) - 1):
        w = max(1, int(width * (1 - 0.7 * i / len(pts))))
        segs.append(((int(pts[i][0]), int(pts[i][1])),
                     (int(pts[i + 1][0]), int(pts[i + 1][1])), w))

                     
    for _ in range(int(rng.integers(1, 3 + int(dmg * 3)))):
        i = int(rng.integers(1, max(2, len(pts) - 2)))
        bx, by = pts[i]
        ba = base_ang + float(rng.choice([-1, 1])) * float(rng.uniform(0.5, 0.9))
        for _ in range(int(rng.integers(3, 7))):
            nx = float(np.clip(bx + np.cos(ba) * 20, 3, IMG_W - 4))
            ny = float(np.clip(by + np.sin(ba) * 20, 3, IMG_H - 4))
            segs.append(((int(bx), int(by)), (int(nx), int(ny)), 1))
            bx, by = nx, ny
            ba += float(rng.normal(0, 0.25))

    for p0, p1, w in segs:
        cv2.line(img, p0, p1, -DARK_CRACK, w)
        if mask is not None:
            cv2.line(mask, p0, p1, int(label), w)


def _draw_joint(img: np.ndarray, rng: np.random.Generator, dmg: float,
                mask: np.ndarray | None = None, label: int = 1) -> None:
                                

                                          
                                
       
    y = int(rng.integers(IMG_H // 3, IMG_H * 2 // 3))
    half = int(26 + 12 * dmg)
                                         
                                                   
                                
    x0, x1 = _JOINT_INSET, IMG_W - _JOINT_INSET
    step_x = int(rng.integers(IMG_W // 3, IMG_W * 2 // 3))
    step = int(10 + 16 * dmg)

    rects = [(x0, y - half, step_x, y + half),
             (step_x, y - half + step, x1, y + half + step)]
    for xa, ya, xb, yb in rects:
        cv2.rectangle(img, (xa, ya), (xb, yb), -DARK_JOINT, -1)
        if mask is not None:
            cv2.rectangle(mask, (xa, ya), (xb, yb), int(label), -1)


def _blob_poly(rng: np.random.Generator, cx: int, cy: int, r: int) -> np.ndarray:
                                    
    pts = []
    for k in range(16):
        a = 2 * np.pi * k / 16
        rr = r * float(rng.uniform(0.68, 1.22))
        pts.append([int(cx + np.cos(a) * rr), int(cy + np.sin(a) * rr)])
    return np.array(pts, np.int32)


def _draw_spalling(img: np.ndarray, rng: np.random.Generator, dmg: float,
                   mask: np.ndarray | None = None, label: int = 1) -> None:
                                
    cx = int(rng.integers(260, IMG_W - 260))
    cy = int(rng.integers(220, IMG_H - 220))
    r = int(58 + 72 * dmg)
    poly = _blob_poly(rng, cx, cy, r)
    region = np.zeros(img.shape[:2], np.uint8)
    cv2.fillPoly(region, [poly], 255)
    noise = cv2.GaussianBlur(rng.normal(0, 15, region.shape).astype(np.float32),
                             (0, 0), 2)
    img[region > 0] += noise[region > 0] - DARK_SPALLING
    if mask is not None:
        cv2.fillPoly(mask, [poly], int(label))


def _draw_seepage(img: np.ndarray, rng: np.random.Generator, dmg: float,
                  mask: np.ndarray | None = None, label: int = 1) -> None:
                                  
    cx = int(rng.integers(300, IMG_W - 300))
    cy = int(rng.integers(260, IMG_H - 260))
    r = int(95 + 125 * dmg)
    poly = _blob_poly(rng, cx, cy, r)
    region = np.zeros(img.shape[:2], np.uint8)
    cv2.fillPoly(region, [poly], 255)
    soft = cv2.GaussianBlur(region.astype(np.float32) / 255.0, (0, 0), r * 0.28)
    img -= soft * DARK_SEEPAGE
    if mask is not None:
        cv2.fillPoly(mask, [poly], int(label))


def _draw_honeycomb(img: np.ndarray, rng: np.random.Generator, dmg: float,
                    mask: np.ndarray | None = None, label: int = 1) -> None:
                                      
    cx = int(rng.integers(300, IMG_W - 300))
    cy = int(rng.integers(250, IMG_H - 250))
    r = int(75 + 90 * dmg)
    poly = _blob_poly(rng, cx, cy, r)
    region = np.zeros(img.shape[:2], np.uint8)
    cv2.fillPoly(region, [poly], 255)
    img[region > 0] -= DARK_HONEYCOMB
    if mask is not None:
        cv2.fillPoly(mask, [poly], int(label))

                          
    n = int(28 + 70 * dmg)
    for _ in range(n):
        a = float(rng.uniform(0, 2 * np.pi))
        d = float(rng.uniform(0, r * 0.86))
        hx = int(cx + np.cos(a) * d)
        hy = int(cy + np.sin(a) * d)
        hr = int(rng.integers(4, 11))
        if region[max(0, hy - hr - 2):hy + hr + 3,
                  max(0, hx - hr - 2):hx + hr + 3].any():
            cv2.circle(img, (hx, hy), hr, float(rng.uniform(38, 58)), -1)


def _draw_exposed_bar(img: np.ndarray, rng: np.random.Generator, dmg: float,
                      mask: np.ndarray | None = None, label: int = 1) -> None:
                                     
    cx = int(rng.integers(300, IMG_W - 300))
    cy = int(rng.integers(240, IMG_H - 240))
    r = int(60 + 70 * dmg)

             
    poly = _blob_poly(rng, cx, cy, r)
    region = np.zeros(img.shape[:2], np.uint8)
    cv2.fillPoly(region, [poly], 255)
    img[region > 0] -= 46
    if mask is not None:
        cv2.fillPoly(mask, [poly], int(label))

                    
    angle = float(rng.uniform(0, np.pi))
    dx, dy = np.cos(angle), np.sin(angle)
    n_bars = int(2 + 2 * dmg)
    for k in range(n_bars):
        off = (k - (n_bars - 1) / 2) * 24
        px, py = cx - dy * off, cy + dx * off
        x0 = int(px - dx * r * 1.1)
        y0 = int(py - dy * r * 1.1)
        x1 = int(px + dx * r * 1.1)
        y1 = int(py + dy * r * 1.1)
        cv2.line(img, (x0, y0), (x1, y1), float(rng.uniform(42, 62)), 7)


_DRAWERS = {
    "crack": _draw_crack,
    "joint_offset": _draw_joint,
    "spalling": _draw_spalling,
    "seepage": _draw_seepage,
    "honeycomb": _draw_honeycomb,
    "exposed_bar": _draw_exposed_bar,
}


                                                                            
                                         
                                           
                                  
_EXTRA_MAX = {"joint_offset": 0}


def _extra_count(point_id: str, cls_key: str) -> int:
                     

                                             
                               
       
    cap = _EXTRA_MAX.get(cls_key, 2)
    return 0 if cap == 0 else int(_seed("sub_n", point_id) % (cap + 1))


def _add_secondary(img: np.ndarray, gt_mask: np.ndarray, point_id: str,
                   cls_key: str, dmg: float) -> None:
                               

                                              
                                          
       
    drawer = _DRAWERS.get(cls_key, _draw_crack)
    for k in range(1, _extra_count(point_id, cls_key) + 1):
        srng = np.random.default_rng(_seed("sub", point_id, k))
        scratch = img.copy()
        smask = np.zeros((IMG_H, IMG_W), np.uint8)
        drawer(scratch, srng, dmg * 0.5, smask, 1)
                                    
        free = (smask > 0) & (gt_mask == 0)
        if int(np.count_nonzero(free)) < 24:
            continue
        img[free] = scratch[free]
        gt_mask[free] = k + 1


def synthesize(point_id: str, batch_id: str, cls_key: str
               ) -> tuple[np.ndarray, list[dict], np.ndarray]:
                                      

                                                      
                                                      
       
                
                                              
                                           
                                            
                                              
                                           
    rng = np.random.default_rng(_seed("img", point_id, batch_id))
    geo = np.random.default_rng(_seed("geo", point_id))
    dmg = _damage_of(point_id, batch_id)
    prefix = point_id[:1]

    tone = {"A": 148, "B": 124, "C": 158, "D": 140}.get(prefix, 145)
    img = _concrete_base(rng, tone)
    _add_structure(img, rng, prefix)

    gt_mask = np.zeros((IMG_H, IMG_W), np.uint8)
                                             
                                           
    _add_secondary(img, gt_mask, point_id, cls_key, dmg)
    _DRAWERS.get(cls_key, _draw_crack)(img, geo, dmg, gt_mask, 1)

    img = cv2.GaussianBlur(img, (0, 0), 0.7)
    bgr = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    tint = np.array([int(rng.integers(2, 8)), int(rng.integers(1, 4)), 0], np.int16)
    bgr = np.clip(bgr.astype(np.int16) + tint, 0, 255).astype(np.uint8)

    instances: list[dict] = []
    n_lab = int(gt_mask.max())
    for i in range(1, n_lab + 1):
        ys, xs = np.nonzero(gt_mask == i)
        if xs.size < 24:
            continue
        instances.append({
            "cls_key": cls_key,
            "box": (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1),
            "px": int(xs.size),
        })
    return bgr, instances, gt_mask


def synth_image(point_id: str, batch_id: str, cls_key: str) -> np.ndarray:
                                
    return synthesize(point_id, batch_id, cls_key)[0]


                                                                            
          
 
                                          
                                         
                         
                                                                            
GT_SUFFIX = ".gt.npz"
_GT_INDEX: dict[str, str] | None = None


def image_sig(bgr: np.ndarray) -> str:
                                                
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(g, (64, 64), interpolation=cv2.INTER_AREA)
    return hashlib.md5(small.tobytes()).hexdigest()


def _gt_path(image_path) -> object:
    from pathlib import Path

    return Path(image_path).with_suffix(GT_SUFFIX)


def save_gt(image_path, instances: list[dict], gt_mask: np.ndarray) -> None:
                         
    if not instances:
        return
    keys = np.array([it["cls_key"] for it in instances])
    boxes = np.array([it["box"] for it in instances], np.int32)
    np.savez_compressed(
        _gt_path(image_path),
        sig=np.array(image_sig(imgutil.imread(image_path))),
        keys=keys, boxes=boxes, mask=gt_mask,
    )


def _build_gt_index() -> dict[str, str]:
    global _GT_INDEX
    if _GT_INDEX is not None:
        return _GT_INDEX
    idx: dict[str, str] = {}
    for p in cfg.IMG_DIR.glob("*" + GT_SUFFIX):
        try:
            with np.load(p) as z:
                idx[str(z["sig"])] = str(p)
        except (OSError, ValueError, KeyError):
            continue
    _GT_INDEX = idx
    return idx


def drop_gt_cache() -> None:
                       
    global _GT_INDEX
    _GT_INDEX = None


def gt_lookup(bgr: np.ndarray) -> dict | None:
                                  
    p = _build_gt_index().get(image_sig(bgr))
    if not p:
        return None
    try:
        with np.load(p) as z:
            return {"keys": [str(k) for k in z["keys"]],
                    "boxes": z["boxes"], "mask": z["mask"]}
    except (OSError, ValueError, KeyError):
        return None


                                                                            
       
                                                                            
def _nominal_distance(point_id: str) -> float:
                                          
    for pid, dist, *_ in DEMO_POINTS:
        if pid == point_id:
            return dist
                                
    return {"A": 1.8, "B": 1.6, "C": 1.3, "D": 2.4}.get(point_id[:1], 2.0)


def waypoint_meta(point_id: str, batch_id: str,
                  distance: float | None = None, order: int = 1) -> dict:
                                           
    return _waypoint_meta(point_id, batch_id,
                          distance if distance else _nominal_distance(point_id),
                          order)


def _waypoint_meta(point_id: str, batch_id: str, distance: float,
                   order: int) -> dict:
                                                   
    rng = np.random.default_rng(_seed("wp", point_id, batch_id))
    prefix = point_id[:1]

                                        
                                                   
                                  
    station_m, offset_m = cfg.waypoint_plan(point_id)
    base_lon = cfg.ORIGIN_LON + station_m / cfg.m_per_deg_lon(cfg.ORIGIN_LAT)
    base_lat = cfg.ORIGIN_LAT + offset_m / cfg.M_PER_DEG_LAT
                                 
    pitch = {"A": 0.0, "B": -32.0, "C": -45.0, "D": 0.0}.get(prefix, 0.0)
    yaw = {"A": 0.0, "B": 0.0, "C": 90.0, "D": 0.0}.get(prefix, 0.0)

    return {
        "point_id": point_id,
        "waypoint": f"WP-{point_id}-{batch_id}",
        "batch": batch_id,
        "rtk_lon": round(base_lon + float(rng.normal(0, 2e-7)), 7),
        "rtk_lat": round(base_lat + float(rng.normal(0, 2e-7)), 7),
        "rtk_alt": round(24.0 + float(rng.normal(0, 0.12)), 2),
        "rtk_status": "固定解" if rng.random() > 0.12 else "浮点解",
        "gimbal_yaw": round(yaw + float(rng.normal(0, 1.2)), 2),
        "gimbal_pitch": round(pitch + float(rng.normal(0, 1.0)), 2),
        "gimbal_roll": round(float(rng.normal(0, 0.8)), 2),
                                                  
                                                        
                                             
                                                  
        "shoot_distance": round(distance, 2),
                                   
        "overlap": round(float(np.clip(rng.normal(0.91, 0.05), 0.62, 0.99)), 3),
        "captured_at": (f"{cfg.BATCH_BY_ID[batch_id].date} "
                        f"{8 + order:02d}:{int(rng.integers(0, 60)):02d}:00"),
    }


                                                                            
    
                                                                            
_DEMO_IMG = "waypoint LIKE 'WP-%'"


def purge_demo_rows() -> None:
                                 

                                                         
                                                      
                                                 
                                          
       
    for t in ("detections", "segments"):
                                                
                                                   
                              
        db.execute(f"DELETE FROM {t} WHERE image_id IS NULL"
                   f" OR image_id NOT IN (SELECT id FROM images)")
        db.execute(f"DELETE FROM {t} WHERE image_id IN"
                   f" (SELECT id FROM images WHERE {_DEMO_IMG})")
    db.execute(f"DELETE FROM images WHERE {_DEMO_IMG}")
    db.execute("DELETE FROM tasks WHERE name LIKE '%全桥巡检' AND owner='admin'")
    for p in cfg.IMG_DIR.glob("*" + GT_SUFFIX):
        try:
            p.unlink()
        except OSError:
            pass
    drop_gt_cache()


def ensure_demo_dataset(force: bool = False, progress=None) -> dict:
                                           
    already = db.query_one(
        "SELECT COUNT(*) AS n FROM images WHERE waypoint LIKE 'WP-%'")
    if already and already["n"] > 0 and not force:
        return {"skipped": True, "images": already["n"]}

    if force:
        purge_demo_rows()

    detector = DemoDetector()
    segmenter = DemoSegmenter()
    stats = {"images": 0, "detections": 0, "segments": 0}

    total = len(DEMO_POINTS) * len(cfg.BATCHES)
    step = 0
    for batch in cfg.BATCHES:
                                         
                                              
        task_id = None

        for order, (point_id, distance, cls_key, _rate) in enumerate(DEMO_POINTS, 1):
            step += 1
            if progress:
                progress(step, total, f"{point_id} · {batch.name}")

                                                
                                             
            meta = _waypoint_meta(point_id, batch.id, distance, order)
            bgr, instances, gt_mask = synthesize(point_id, batch.id, cls_key)

            fname = f"{batch.id}_{point_id}_{meta['waypoint']}.jpg"
            path = cfg.IMG_DIR / fname
            if force or not path.exists():
                drop_gt_cache()
                imgutil.imwrite(path, bgr)
                save_gt(path, instances, gt_mask)
                                                     
                                            
                bgr = imgutil.imread(path)

            existing = db.image_by_path(str(path))
            if existing and not force:
                continue
            if existing:
                                                   
                db.execute("DELETE FROM detections WHERE image_id=?", (existing["id"],))
                db.execute("DELETE FROM segments WHERE image_id=?", (existing["id"],))
                db.execute("DELETE FROM images WHERE id=?", (existing["id"],))

            h, w = bgr.shape[:2]
            image_id = db.add_image(
                task_id=task_id, path=str(path), filename=fname, width=w, height=h,
                size_kb=round(path.stat().st_size / 1024, 1) if path.exists() else 0,
                source="SD卡导入", **meta,
            )
            stats["images"] += 1

                                      
            dets: list[Detection] = detector.predict(bgr)
            rows = [{
                "image_id": image_id, "task_id": task_id, "point_id": point_id,
                "cls_key": d.cls_key, "cls_name": d.cls_name, "conf": d.conf,
                "x1": d.x1, "y1": d.y1, "x2": d.x2, "y2": d.y2,
                "gt_idx": d.gt_idx,
            } for d in dets]
            db.add_detections(rows)
            stats["detections"] += len(rows)

                                                   
                                                
                                               
                          
            has_gt = gt_lookup(bgr) is not None
            for d in dets:
                if has_gt and d.gt_idx <= 0:
                    continue
                res = segmenter.segment(bgr, d, meta["shoot_distance"])
                if res is None or res.px_area <= 0:
                    continue
                db.add_segment(
                    image_id=image_id, task_id=task_id, point_id=point_id,
                    batch=batch.id, captured_at=meta["captured_at"],
                    **segment_fields(res),
                )
                stats["segments"] += 1

    stats["skipped"] = False
    return stats


def regenerate_all(progress=None) -> dict:
                                      
    return ensure_demo_dataset(force=True, progress=progress)
