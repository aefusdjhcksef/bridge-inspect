                                         

                                                  
      

                                                          
                                         
          
                                                  
                                           

                                              
   

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .. import config as cfg
from .. import db
from . import demo_data, imgutil

                                                          
POINT_RE = re.compile(r"([A-Fa-f]\d{2})")
                                               
                                                   
                                   
BATCH_RE = re.compile(r"\b(P[1-9])\b", re.I)

      
ADDED = "added"
EXISTS = "exists"
UNSUPPORTED = "unsupported"
UNDECODABLE = "undecodable"


@dataclass
class IngestRow:
                    
    path: str
    filename: str
    status: str
    point_id: str = ""
    batch: str = ""
    width: int = 0
    height: int = 0
    size_kb: float = 0.0
    overlap: float = 0.0
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "path": self.path, "filename": self.filename, "status": self.status,
            "point_id": self.point_id, "batch": self.batch,
            "width": self.width, "height": self.height,
            "size_kb": self.size_kb, "overlap": self.overlap,
            "message": self.message,
        }


@dataclass
class IngestResult:
    rows: list[IngestRow] = field(default_factory=list)

    @property
    def added(self) -> list[IngestRow]:
        return [r for r in self.rows if r.status == ADDED]

    @property
    def skipped(self) -> list[IngestRow]:
        return [r for r in self.rows if r.status == EXISTS]

    @property
    def failed(self) -> list[IngestRow]:
        return [r for r in self.rows
                if r.status in (UNSUPPORTED, UNDECODABLE)]

    @property
    def first_added_id(self) -> int | None:
                                            
        for r in self.added:
            row = db.query_one("SELECT id FROM images WHERE path=?", (r.path,))
            if row:
                return int(row["id"])
        return None

    def summary(self) -> str:
        parts = []
        if self.added:
            parts.append(f"新增 {len(self.added)} 张")
        if self.skipped:
            parts.append(f"已在库 {len(self.skipped)} 张")
        if self.failed:
            parts.append(f"未能导入 {len(self.failed)} 张")
        return "，".join(parts) or "没有可导入的影像"

    def to_dict(self) -> dict:
        return {"rows": [r.to_dict() for r in self.rows],
                "added": len(self.added), "skipped": len(self.skipped),
                "failed": len(self.failed), "summary": self.summary()}


def parse_name(stem: str) -> tuple[str, str]:
                                              
    m = POINT_RE.search(stem)
    point_id = m.group(1).upper() if m else ""
    mb = BATCH_RE.search(stem)
    batch = mb.group(1).upper() if mb else ""
    return point_id, batch


def ingest(paths, default_batch: str | None = None) -> IngestResult:
                                   

                                           
                                        
       
    default_batch = default_batch or cfg.BATCHES[0].id
    out = IngestResult()
    idx = 0
    for raw in paths or []:
        p = Path(raw)
        if not imgutil.is_supported(str(p)):
            out.rows.append(IngestRow(str(p), p.name, UNSUPPORTED,
                                      message="不是支持的影像格式"))
            continue
        idx += 1
        bgr = imgutil.imread(p)
        if bgr is None:
            out.rows.append(IngestRow(str(p), p.name, UNDECODABLE,
                                      message="无法解码"))
            continue

        point_id, batch = parse_name(p.stem)
        if not point_id:
            point_id = f"X{idx:02d}"
        if batch not in cfg.BATCH_BY_ID:
            batch = default_batch

        meta = demo_data.waypoint_meta(point_id, batch)
        h, w = bgr.shape[:2]
        size_kb = round(p.stat().st_size / 1024, 1)
        row = IngestRow(str(p), p.name, ADDED, point_id=point_id, batch=batch,
                        width=w, height=h, size_kb=size_kb,
                        overlap=float(meta.get("overlap") or 0.0))

        if db.image_by_path(str(p)):
            row.status = EXISTS
            row.message = "已在库中，跳过重复入库"
            out.rows.append(row)
            continue

        db.add_image(task_id=None, path=str(p), filename=p.name,
                     width=w, height=h, size_kb=size_kb,
                     source="SD卡导入", **meta)
        out.rows.append(row)
    return out


def ingest_one(path: str) -> tuple[int | None, str, str]:
                          

                                                            
         

                                              
                                              
                                            
                                   

                                              
                                                        
                                                   
                   

                                                    
                                  
       
    src = Path(path)
    if not imgutil.is_supported(str(src)):
        return None, str(src), "不是支持的影像格式"

    dest = cfg.IMG_DIR / src.name
    try:
        same = dest.exists() and src.resolve() == dest.resolve()
    except OSError:                                            
        same = False
    if not same:
        cfg.IMG_DIR.mkdir(parents=True, exist_ok=True)
        n = 1
        while dest.exists():
            dest = cfg.IMG_DIR / f"{src.stem}_{n}{src.suffix}"
            n += 1
        try:
            shutil.copy2(src, dest)
        except OSError as e:
            return None, str(src), f"复制到 data/images/ 失败：{e}"

    res = ingest([str(dest)])
    row = res.rows[0] if res.rows else None
    if row is None or row.status in (UNSUPPORTED, UNDECODABLE):
        return None, str(dest), (row.message if row else "入库失败")
    got = db.image_by_path(str(dest))
    if got is None:                                            
        return None, str(dest), "入库后查不到记录"
                                                  
                                    
    note = (f"已入库：点位 {got['point_id'] or '—'} · 批次 {got['batch'] or '—'}"
            if row.status == ADDED else f"该影像已在库中（{got['point_id']}）")
    return int(got["id"]), str(dest), note
