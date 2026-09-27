             

                                              
                                                
                                          
           

                                 
   

from __future__ import annotations

from bridge_inspect import config as cfg
from bridge_inspect import db


def _dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


def _f(v, nd: int = 2) -> float:
                                                           
    try:
        return round(float(v or 0.0), nd)
    except (TypeError, ValueError):
        return 0.0


def anomaly_rows(threshold: float = 0.30) -> list[dict]:
                                            
    from bridge_inspect.core import llm
    try:
        return list(llm.detect_anomalies(growth_threshold=float(threshold)) or [])
    except Exception:                                                
        return []


def overview() -> dict:
                      

                                       
                                        
                         
       
    s = db.stat_summary()
    imgs = _dicts(db.list_images(limit=100000))
    segs = _dicts(db.query(
        "SELECT point_id, cls_key, cls_name, batch, area_cm2, max_width_mm"
        " FROM segments WHERE area_cm2>0"))
                                                
                                                       
                                             
    dets = _dicts(db.query("SELECT point_id, cls_key FROM detections"))

                
    batches: list[dict] = []
    for b in cfg.BATCHES:
        bi = [r for r in imgs if r["batch"] == b.id]
        bs = [r for r in segs if r["batch"] == b.id]
        batches.append({
            "id": b.id, "name": b.name, "date": b.date, "note": b.note,
            "images": len(bi), "segments": len(bs),
            "points": len({r["point_id"] for r in bi if r["point_id"]}),
            "area_cm2": round(sum(_f(r["area_cm2"], 3) for r in bs), 2),
            "avg_overlap": round(
                sum(_f(r["overlap"], 4) for r in bi) / len(bi), 4) if bi else 0.0,
        })

                  
                                                
                                                      
    classes: list[dict] = []
    for d in cfg.DISEASES:
        drows = [r for r in dets if r["cls_key"] == d.key]
        srows = [r for r in segs if r["cls_key"] == d.key]
        classes.append({
            "key": d.key, "name": d.name, "color": d.color,
            "severity": d.severity, "suggestion": d.suggestion,
            "limit_mm": d.width_limit_mm,
            "n": len(drows),
            "points": len({r["point_id"] for r in drows if r["point_id"]}),
            "area_cm2": round(sum(_f(r["area_cm2"], 3) for r in srows), 2),
            "max_width_mm": round(max((_f(r["max_width_mm"], 3) for r in srows),
                                      default=0.0), 3),
            "n_seg": len(srows),                      
        })

                
                                                 
                                    
    comp_points: dict[str, list[str]] = {}
    for p in sorted({r["point_id"] for r in imgs if r["point_id"]}):
        comp_points.setdefault(p[:1], []).append(p)
    components = [{
        "letter": k, "name": v,
        "n": len(comp_points.get(k, [])),
        "points": comp_points.get(k, []),
    } for k, v in cfg.COMPONENTS.items()]

    return {
        "stats": s,
        "batches": batches,
        "classes": classes,
        "components": components,
        "anomalies": anomaly_rows(),
        "tasks": _dicts(db.list_tasks(limit=8)),
        "outputs": _dicts(db.list_outputs(limit=8)),
        "with_images": sorted({r["point_id"] for r in imgs if r["point_id"]}),
        "all_points": cfg.ALL_POINTS,
    }


def waypoints(batch: str = "") -> dict:
                          

                                                     
                                          
                          
       
    have: dict[tuple[str, str], dict] = {}
    for r in db.list_images(limit=100000):
        if r["point_id"] and r["batch"]:
            have.setdefault((r["point_id"], r["batch"]), dict(r))

    from bridge_inspect.core import demo_data

    out: list[dict] = []
    for pid in cfg.ALL_POINTS:
        for b in cfg.BATCHES:
            if batch and b.id != batch:
                continue
            row = have.get((pid, b.id))
            if row:
                src = "db"
                rec = {k: row.get(k) for k in (
                    "waypoint", "rtk_lon", "rtk_lat", "rtk_alt", "rtk_status",
                    "gimbal_yaw", "gimbal_pitch", "gimbal_roll",
                    "shoot_distance", "overlap")}
                rec["filename"] = row.get("filename", "")
                rec["image_id"] = row.get("id")
            else:
                src = "plan"
                rec = demo_data.waypoint_meta(pid, b.id)
                rec["image_id"] = None
                rec["filename"] = ""
            dist = _f(rec.get("shoot_distance"), 3)
            out.append({
                "point_id": pid, "component": cfg.point_component(pid),
                "batch": b.id, "flown": bool(row), "source": src,
                "lon": _f(rec.get("rtk_lon"), 7),
                "lat": _f(rec.get("rtk_lat"), 7),
                "alt": _f(rec.get("rtk_alt"), 2),
                "rtk_status": rec.get("rtk_status") or "固定解",
                "gimbal_yaw": _f(rec.get("gimbal_yaw"), 2),
                "gimbal_pitch": _f(rec.get("gimbal_pitch"), 2),
                "gimbal_roll": _f(rec.get("gimbal_roll"), 2),
                "shoot_distance": dist,
                "overlap": _f(rec.get("overlap"), 4),
                "gsd_mm_per_px": round(cfg.gsd_mm_per_px(dist), 4),
                "waypoint": rec.get("waypoint") or f"WP-{pid}-{b.id}",
                "image_id": rec.get("image_id"),
                "filename": rec.get("filename") or "",
            })
    lons = [w["lon"] for w in out if w["lon"]]
    lats = [w["lat"] for w in out if w["lat"]]
    return {
        "waypoints": out,
        "bounds": {
            "lon_min": min(lons) if lons else 0.0, "lon_max": max(lons) if lons else 0.0,
            "lat_min": min(lats) if lats else 0.0, "lat_max": max(lats) if lats else 0.0,
        },
        "batches": [{"id": b.id, "name": b.name, "date": b.date} for b in cfg.BATCHES],
                                              
                                                    
                                  
        "bridge": {
            "len_m": cfg.BRIDGE_LEN_M,
            "width_m": cfg.BRIDGE_WIDTH_M,
            "pier_spacing_m": cfg.PIER_SPACING_M,
            "origin_lat": cfg.ORIGIN_LAT,
            "origin_lon": cfg.ORIGIN_LON,
        },
    }
