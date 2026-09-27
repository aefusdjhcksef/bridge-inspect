                          

                                              
                                                 
                                        

                            

                                                                
                                                
                          

                     
                                                                
                                         

                                                             
                                                               

                                                          
                                                            
                                           
                                    

                                         
                   
   

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from ... import config as cfg
from ... import db
from . import specs

                                    
                                   
SAFE_DISTANCE: dict[str, float] = {
    "A": 1.0,                  
    "B": 0.8,            
    "C": 0.7,                     
    "D": 0.8,         
    "E": 1.2,       
    "F": 1.5,                    
}

ZOOM_MAX = 5.0                             
                                             
                                          
TARGET_PX = 12
OVERLAP_HARD = cfg.OVERLAP_OK                                     
OVERLAP_SOFT = cfg.OVERLAP_WARN                 
EDGE_MARGIN = 0.02                        
LOW_CONF = 0.55                         
BOX_FRAME_RATIO = 0.90                    

                                          
              
                                            
                                   
                                
                                             
                                
                                                 
CODE_RANK = {"Q5": 0, "Q3": 1, "Q4": 2, "Q1": 3, "Q2": 4}


_BATCH_ORDER = {b.id: i for i, b in enumerate(cfg.BATCHES)}


def _severity(iss: "Issue") -> tuple[float, int]:
                               

                                           
                                                     
                                         
       
    d = iss.data
    if iss.code == "Q5":
        metric = float(d.get("ratio") or 0.0)
    elif iss.code == "Q1":
        metric = 1.0 - float(d.get("overlap") or 0.0)
    elif iss.code == "Q3":
        metric = 1.0 - float(d.get("margin") or 0.0)
    elif iss.code == "Q2":
        metric = 1.0 - float(d.get("top_conf") or 0.0)
    else:
        metric = 0.0
    return (metric, _BATCH_ORDER.get(iss.batch, -1))


@dataclass
class Issue:
                   
    code: str
    point_id: str
    batch: str
    cls_key: str = ""
    cls_name: str = ""
    level: str = "中"
    title: str = ""
    detail: str = ""
    image_id: int = 0
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReflyWaypoint:
                                             
    waypoint: str
    point_id: str
    batch: str
    rtk_lon: float
    rtk_lat: float
    rtk_alt: float
    rtk_status: str
    gimbal_yaw: float
    gimbal_pitch: float
    gimbal_roll: float
    shoot_distance: float
    zoom: float
    focal_eff_mm: float
    expected_gsd_mm_per_px: float
    expected_px_width: float
    expected_overlap: float
    target_class: str
    cls_name: str
    trigger_code: str
    trigger_desc: str
    priority: str
    source_image: str
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


                                                                            
      
                                                                            
def _margin_ratio(det_x1: int, det_x2: int, img_w: int) -> float:
                                      
    if img_w <= 0:
        return 1.0
    return min(det_x1, img_w - det_x2) / img_w


def audit_quality(points: list[str] | None = None,
                  batches: list[str] | None = None) -> list[Issue]:
                           

                                        
                                   
       
    pts = {p for p in (points or []) if p}
    bts = {b for b in (batches or []) if b}

                                                 
                                                 
                                    
    acc: dict[tuple, Issue] = {}

    def _push(iss: Issue) -> None:
        k = (iss.code, iss.point_id, iss.batch, iss.cls_key)
        cur = acc.get(k)
        if cur is None or _severity(iss) > _severity(cur):
            acc[k] = iss

    sql = ("SELECT i.* FROM images i WHERE i.point_id<>''")
    rows = [r for r in db.query(sql)
            if (not pts or r["point_id"] in pts) and (not bts or r["batch"] in bts)]

                                    
    hist: dict[str, set[str]] = {}
    for s in db.query("SELECT DISTINCT point_id, cls_key, batch FROM segments"):
        hist.setdefault(s["point_id"], set()).add(s["cls_key"])

    for img in rows:
        pid, bid = img["point_id"], img["batch"]
        segs = db.query("SELECT * FROM segments WHERE image_id=?", (img["id"],))
        dets = db.query("SELECT * FROM detections WHERE image_id=?", (img["id"],))

                  
        ov = float(img["overlap"] or 0.0)
        if ov < OVERLAP_HARD:
            _push(Issue(
                "Q1", pid, bid, level="高", image_id=img["id"],
                title=f"重合率 {ov:.0%} 低于合格线 {OVERLAP_HARD:.0%}",
                detail="同视场复拍的重合率不足，该点位历次影像不构成可比序列，"
                       "本批次数据无法用于趋势判断。",
                data={"overlap": ov, "threshold": OVERLAP_HARD}))
        elif ov < OVERLAP_SOFT:
            _push(Issue(
                "Q1", pid, bid, level="中", image_id=img["id"],
                                                         
                                                   
                title=f"重合率 {ov:.1%} 未达建议值 {OVERLAP_SOFT:.0%}"
                      f"（合格线 {OVERLAP_HARD:.0%}）",
                                                    
                                        
                detail="重合率在合格线之上、未达建议值，历次影像仍可比，"
                       "但复拍视场存在轻微偏移，建议下一批次校正站位。",
                data={"overlap": ov, "threshold": OVERLAP_SOFT}))

                  
        if dets:
            top = max(float(d["conf"]) for d in dets)
            if top < LOW_CONF:
                _push(Issue(
                    "Q2", pid, bid, cls_key=dets[0]["cls_key"],
                    cls_name=dets[0]["cls_name"], level="中", image_id=img["id"],
                    title=f"最高置信度仅 {top:.2f}",
                    detail="检出置信度偏低，通常由逆光或欠曝导致对比度不足引起；"
                           "建议复飞时提高曝光补偿并人工复核。",
                    data={"top_conf": top, "threshold": LOW_CONF}))

                      
        if dets and img["width"]:
            worst = min(dets, key=lambda d: _margin_ratio(d["x1"], d["x2"], img["width"]))
            m = _margin_ratio(worst["x1"], worst["x2"], img["width"])
            if m < EDGE_MARGIN:
                _push(Issue(
                    "Q3", pid, bid, cls_key=worst["cls_key"],
                    cls_name=worst["cls_name"], level="中", image_id=img["id"],
                    title=f"{worst['cls_name']}贴合画面边界（边距 {m:.1%}）",
                    detail="检测框触及画面边缘，病害两端可能被裁切，"
                           "面积与周长会被低估，需拉远视场重拍。",
                    data={"margin": m, "threshold": EDGE_MARGIN,
                          "box_px": int(worst["x2"]) - int(worst["x1"]),
                          "img_w": int(img["width"])}))

                                        
        have = {s["cls_key"] for s in segs}
        missing = (hist.get(pid, set()) - have) if segs else set()
        if segs and missing:
            for ck in sorted(missing):
                dc = cfg.DISEASE_BY_KEY.get(ck)
                _push(Issue(
                    "Q4", pid, bid, cls_key=ck,
                    cls_name=dc.name if dc else ck, level="高", image_id=img["id"],
                    title=f"{dc.name if dc else ck} 本批次未检出",
                    detail="该点位历史批次存在此类别病害，同视场复拍本不应消失，"
                           "疑似漏检或被遮挡，需复飞确认。",
                    data={"missing_cls": ck}))

                                       
        for s in segs:
            dc = cfg.DISEASE_BY_KEY.get(s["cls_key"])
            limit = dc.width_limit_mm if dc else None
            if limit is None:
                continue                                      
            dist = float(img["shoot_distance"] or 0.0)
            gsd = cfg.gsd_mm_per_px(dist)
            if gsd <= 0:
                continue
            unc = 2 * gsd                                     
            ratio = unc / limit                                 
            if ratio <= 1.0 / 3.0:
                continue
            w = float(s["max_width_mm"] or 0.0)
            px = w / gsd
            _push(Issue(
                "Q5", pid, bid, cls_key=s["cls_key"], cls_name=s["cls_name"],
                level="高", image_id=img["id"],
                title=(f"{s['cls_name']}量测不确定度 {unc:.2f} mm，"
                       f"达限值 {limit:g} mm 的 {ratio:.0%}"),
                detail=(f"拍摄距离 {dist:.2f} m 下 GSD 为 {gsd:.3f} mm/px，"
                        f"该{s['cls_name']}在画面上仅 {px:.1f} 像素宽。轮廓抖动 1 像素"
                        f"即引起 {unc:.2f} mm 的宽度偏差，已超过规范限值 {limit:g} mm 的"
                        f"三分之一，超限与否在统计上不可判定。"),
                data={"distance": dist, "gsd": gsd, "width_mm": w, "px": px,
                      "uncertainty_mm": unc, "limit_mm": limit, "ratio": ratio}))

    order = {"高": 0, "中": 1, "低": 2}
    return sorted(acc.values(),
                  key=lambda i: (order.get(i.level, 3), CODE_RANK.get(i.code, 9),
                                 i.point_id, i.batch))


                                                                            
      
                                                                            
def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
                                   
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def required_px(width_mm: float, limit_mm: float) -> int:
                         

                                        

                                           

                                                     
                                                        
                                       
       
    if width_mm <= 0 or limit_mm <= 0:
        return TARGET_PX
    return max(TARGET_PX, int(math.ceil(6.0 * width_mm / limit_mm)))


def solve_distance(width_mm: float, prefix: str,
                   target_px: int = TARGET_PX) -> dict:
                                         

                                            
                                      
                             
                  
       
    d_safe = SAFE_DISTANCE.get(prefix, 1.0)
    gsd_target = width_mm / max(1, target_px) if width_mm > 0 else 0.0
    if gsd_target <= 0:
        return {"distance": d_safe, "zoom": 1.0, "focal_eff": cfg.CAM_FOCAL_MM,
                "gsd": cfg.gsd_mm_per_px(d_safe), "zoom_limited": False,
                "target_px": target_px}

    d_by_dist = gsd_target * cfg.CAM_FOCAL_MM / cfg.CAM_PIXEL_UM
    if d_by_dist >= d_safe:
        return {"distance": round(d_by_dist, 2), "zoom": 1.0,
                "focal_eff": cfg.CAM_FOCAL_MM,
                "gsd": round(cfg.gsd_mm_per_px(d_by_dist), 4),
                "zoom_limited": False, "target_px": target_px}

    focal_req = cfg.CAM_PIXEL_UM * d_safe / gsd_target
    zoom = min(focal_req / cfg.CAM_FOCAL_MM, ZOOM_MAX)
    gsd = cfg.CAM_PIXEL_UM * d_safe / (cfg.CAM_FOCAL_MM * zoom)
    return {"distance": round(d_safe, 2), "zoom": round(zoom, 2),
            "focal_eff": round(cfg.CAM_FOCAL_MM * zoom, 1),
            "gsd": round(gsd, 4), "zoom_limited": zoom >= ZOOM_MAX,
            "target_px": target_px}


def _dominant_class(point_id: str, batch: str) -> str:
                        

                                           
                                          
             
       
    row = db.query_one(
        "SELECT s.cls_key AS k FROM segments s"
        " JOIN images i ON i.id = s.image_id"
        " WHERE i.point_id=? AND i.batch=?"
        " GROUP BY s.cls_key ORDER BY MAX(s.area_cm2) DESC LIMIT 1",
        (point_id, batch))
    return row["k"] if row and row["k"] else ""


def _max_width(point_id: str, batch: str, cls_key: str) -> float:
                                         
                                        
    if not cls_key:
        return 0.0
    row = db.query_one(
        "SELECT MAX(s.max_width_mm) AS w FROM segments s"
        " JOIN images i ON i.id = s.image_id"
        " WHERE i.point_id=? AND i.batch=? AND s.cls_key=?",
        (point_id, batch, cls_key))
    return float(row["w"] or 0.0) if row and row["w"] is not None else 0.0


def _baseline_station(point_id: str) -> dict | None:
                                     

                                  
                        
       
    first = cfg.BATCHES[0].id if cfg.BATCHES else "P1"
    return db.query_one(
        "SELECT rtk_lon, rtk_lat, rtk_alt, gimbal_yaw, gimbal_pitch, gimbal_roll,"
        " shoot_distance FROM images WHERE point_id=? AND batch=?"
        " ORDER BY id LIMIT 1", (point_id, first))


def solve_waypoint(issue: Issue, target_px: int = TARGET_PX) -> ReflyWaypoint | None:
                        
    img = db.query_one("SELECT * FROM images WHERE id=?", (issue.image_id,))
    if not img:
        return None
    pid = issue.point_id
    prefix = pid[:1].upper()
    d0 = float(img["shoot_distance"] or 0.0)
    base = _baseline_station(pid)

    dist, zoom, focal_eff = d0, 1.0, cfg.CAM_FOCAL_MM
    note = ""

    if issue.code == "Q5":
        w = float(issue.data.get("width_mm") or 0.0)
        lim = float(issue.data.get("limit_mm") or 0.0)
                                                  
                                                
                            
        tgt = target_px if target_px != TARGET_PX else required_px(w, lim)
        sol = solve_distance(w, prefix, tgt)
        dist, zoom, focal_eff = sol["distance"], sol["zoom"], sol["focal_eff"]
        after = (2 * sol["gsd"] / lim) if lim > 0 else 0.0
        note = (f"目标像素宽 {tgt} px，不确定度自 {issue.data['ratio']:.0%} "
                f"降至 {after:.0%}")
        if sol["zoom_limited"]:
            note += "；变焦已到上限，实际不确定度仍高于 1/3 判据"

    elif issue.code == "Q3":
                             
        box_px = float(issue.data.get("box_px") or 0.0)
        img_w = float(issue.data.get("img_w") or 0.0)
        if box_px > 0 and img_w > 0:
            dist = d0 * box_px / (BOX_FRAME_RATIO * img_w)
            dist = max(dist, SAFE_DISTANCE.get(prefix, 1.0))
            note = f"视场由 {d0:.2f} m 拉远至 {dist:.2f} m，使目标完整入画"
        else:
            dist = d0 * 1.15
            note = "视场适度拉远，确保目标两端完整入画"

    elif issue.code == "Q1":
                             
        dist = float(base["shoot_distance"]) if base else d0
        if base:
            note = "站位回退至 P1 基准航点，恢复同视场复拍条件"
        else:
            note = "缺基准站位记录，按标称距离重拍"

    elif issue.code == "Q2":
        note = "几何参数不变，曝光补偿 +0.7 EV 后重拍，并标记人工复核"

    elif issue.code == "Q4":
        note = "按历史批次的站位与云台姿态补拍，确认病害是否真实消失"

    dist = round(max(dist, 0.2), 2)
    gsd = cfg.gsd_mm_per_px(dist) / max(zoom, 1e-6)
                                        
    cls_key = issue.cls_key or _dominant_class(pid, issue.batch)
    cls_name = issue.cls_name or (cfg.DISEASE_BY_KEY[cls_key].name
                                  if cls_key in cfg.DISEASE_BY_KEY else "")
    w_mm = float(issue.data.get("width_mm") or 0.0)
    if w_mm <= 0:
        w_mm = _max_width(pid, issue.batch, cls_key)
    px = (w_mm / gsd) if (gsd > 0 and w_mm > 0) else 0.0

                                
    lon = float(base["rtk_lon"]) if base else float(img["rtk_lon"] or 0.0)
    lat = float(base["rtk_lat"]) if base else float(img["rtk_lat"] or 0.0)
    alt = float(base["rtk_alt"]) if base else float(img["rtk_alt"] or 0.0)
    yaw = float(base["gimbal_yaw"]) if base else float(img["gimbal_yaw"] or 0.0)
    pitch = float(base["gimbal_pitch"]) if base else float(img["gimbal_pitch"] or 0.0)
    roll = float(base["gimbal_roll"]) if base else float(img["gimbal_roll"] or 0.0)

    return ReflyWaypoint(
        waypoint=f"WP-{pid}-{issue.batch}-REF",
        point_id=pid, batch=issue.batch,
        rtk_lon=round(lon, 7), rtk_lat=round(lat, 7), rtk_alt=round(alt, 2),
        rtk_status="固定解",
        gimbal_yaw=round(yaw, 2), gimbal_pitch=round(pitch, 2),
        gimbal_roll=round(roll, 2),
        shoot_distance=dist, zoom=round(zoom, 2), focal_eff_mm=focal_eff,
        expected_gsd_mm_per_px=round(gsd, 4),
        expected_px_width=round(px, 1),
                                
        expected_overlap=0.92,
        target_class=cls_key, cls_name=cls_name,
        trigger_code=issue.code, trigger_desc=issue.title,
        priority=issue.level, source_image=img["filename"], note=note,
    )


                                                                            
    
                                                                            
def plan(points: list[str] | None = None, batches: list[str] | None = None,
         target_px: int = TARGET_PX
         ) -> tuple[list[Issue], list[ReflyWaypoint]]:
                                   

                                   
                      
       
    issues = audit_quality(points, batches)
    best: dict[str, Issue] = {}
    order = {"高": 0, "中": 1, "低": 2}
    for i in issues:
        cur = best.get(i.point_id)
                                        
        key = (order.get(i.level, 9), CODE_RANK.get(i.code, 9),
               -_BATCH_ORDER.get(i.batch, -1))
        cur_key = (order.get(cur.level, 9), CODE_RANK.get(cur.code, 9),
                   -_BATCH_ORDER.get(cur.batch, -1)) if cur else None
        if cur is None or key < cur_key:
            best[i.point_id] = i

    wps: list[ReflyWaypoint] = []
    for pid in sorted(best):
        w = solve_waypoint(best[pid], target_px)
        if w:
            wps.append(w)
    return issues, wps


FIELDS = list(ReflyWaypoint.__dataclass_fields__.keys())


def write_mission(waypoints: list[ReflyWaypoint],
                  out_dir: Path | None = None,
                  stamp: str | None = None) -> tuple[Path, Path]:
                                

                                      
                       
       
    from ... import config as _cfg
    d = Path(out_dir) if out_dir else (_cfg.OUT_DIR / "refly")
    d.mkdir(parents=True, exist_ok=True)
    st = stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    batch = waypoints[0].batch if waypoints else "P1"
    csv_path = d / f"ReflyMission_{batch}_{st}.csv"
    json_path = d / f"ReflyMission_{batch}_{st}.json"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for wp in waypoints:
            w.writerow(wp.to_dict())

    json_path.write_text(json.dumps({
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "batch": batch,
        "count": len(waypoints),
        "waypoints": [wp.to_dict() for wp in waypoints],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_path, json_path


                                             
                                 
                                 
_CODE_KW: dict[str, list[str]] = {
    "Q5": ["分辨率", "量测", "精度"],                           
    "Q1": ["重合率", "复拍", "同视场"],                      
    "Q3": ["记录", "基准", "比对"],                                
    "Q4": ["记录", "基准", "比对"],             
    "Q2": ["记录"],
}


def citations_for(issues: list[Issue]) -> list[dict]:
                                    

                                          
                                         
                                       
                                    
       
    out: list[dict] = []
    seen: set[str] = set()
    for i in issues:
        cls = i.cls_key or ""
        top = specs.search([cls] if cls else [], [],
                           top_k=2, extra_kw=_CODE_KW.get(i.code, []),
                           strict_component=False)
        for c in top:
            if c.cid not in seen:
                seen.add(c.cid)
                out.append(c.to_dict())
    return out
