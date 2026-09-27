                 

                                                   
                                                           
                                          

                                                 
                                        
                                           

                                                             
                                                   
   

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

SPEC_PATH = Path(__file__).resolve().parent.parent / "core" / "icons.json"

VB = 24.0                                                            
DEFAULT_SW = 1.6                                 

                                        
_NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
_CMD = re.compile(r"[MmLlHhVvCcAaZz]")
_ARGC = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "A": 7, "Z": 0}


                                                                            
    
                                                                            
@lru_cache(maxsize=1)
def load() -> dict:
                                               
    try:
        data = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    icons = data.get("icons") or {}
    if not isinstance(icons, dict):
        return {}
    icons["__aliases__"] = data.get("aliases") or {}
    return icons


def names() -> list[str]:
    return [k for k in load() if k != "__aliases__"]


def _resolve(name: str) -> str:
                                                         
    return (load().get("__aliases__") or {}).get(name, name)


def _shapes(name: str) -> list[dict]:
    return (load().get(_resolve(name)) or {}).get("shapes") or []


def about(name: str) -> str:
                                        
    return (load().get(_resolve(name)) or {}).get("about") or ""


                                                                            
      
                                                                            
def _tokens(d: str) -> list:
                                         

                                                              
                         
       
    out, i, n = [], 0, len(d)
    while i < n:
        c = d[i]
        if c in " ,\t\r\n":
            i += 1
            continue
        m = _CMD.match(d, i)
        if m:
            out.append(m.group(0))
            i = m.end()
            continue
        m = _NUM.match(d, i)
        if not m:
                                                 
                                                
            i += 1
            continue
        out.append(float(m.group(0)))
        i = m.end()
    return out


def _arc_to(path: QPainterPath, x1: float, y1: float, rx: float, ry: float,
            phi_deg: float, large: bool, sweep: bool, x2: float,
            y2: float) -> None:
                                      

                                                    
                                         
       
    if x1 == x2 and y1 == y2:
        return
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0:
        path.lineTo(x2, y2)
        return

    phi = math.radians(phi_deg)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2.0, (y1 - y2) / 2.0
    x1p = cp * dx + sp * dy
    y1p = -sp * dx + cp * dy

    lam = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if lam > 1.0:
        s = math.sqrt(lam)
        rx, ry = rx * s, ry * s

    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    k = math.sqrt(max(0.0, num / den)) if den else 0.0
    if large == sweep:
        k = -k
    cxp = k * rx * y1p / ry
    cyp = -k * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2.0
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2.0

    def ang(ux: float, uy: float, vx: float, vy: float) -> float:
        dot = ux * vx + uy * vy
        nrm = math.hypot(ux, uy) * math.hypot(vx, vy)
        if nrm == 0:
            return 0.0
        a = math.acos(max(-1.0, min(1.0, dot / nrm)))
        return -a if ux * vy - uy * vx < 0 else a

    ux, uy = (x1p - cxp) / rx, (y1p - cyp) / ry
    vx, vy = (-x1p - cxp) / rx, (-y1p - cyp) / ry
    t0 = ang(1.0, 0.0, ux, uy)
    dt = ang(ux, uy, vx, vy)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi

    if abs(rx - ry) > 1e-9 or abs(phi_deg) > 1e-9:
                                          
        for i in range(1, 25):
            t = t0 + dt * i / 24.0
            ex = cx + rx * math.cos(t) * cp - ry * math.sin(t) * sp
            ey = cy + rx * math.cos(t) * sp + ry * math.sin(t) * cp
            path.lineTo(ex, ey)
        return

                                                  
                           
    rect = QRectF(cx - rx, cy - ry, 2 * rx, 2 * ry)
    path.arcTo(rect, -math.degrees(t0), -math.degrees(dt))


def _build(d: str) -> QPainterPath:
                                  
    path = QPainterPath()
    toks = _tokens(d)
    i, n = 0, len(toks)
    cmd = None
    x = y = sx = sy = 0.0                     
    while i < n:
        if isinstance(toks[i], str):
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                path.closeSubpath()
                x, y = sx, sy
                continue
        if cmd is None:
            break
        up = cmd.upper()
        rel = cmd.islower()
        need = _ARGC.get(up)
        if need is None or i + need > n:
            break
        a = [float(v) for v in toks[i:i + need]]
        i += need

        if up == "M":
            x, y = (x + a[0], y + a[1]) if rel else (a[0], a[1])
            path.moveTo(x, y)
            sx, sy = x, y
            cmd = "l" if rel else "L"                       
        elif up == "L":
            x, y = (x + a[0], y + a[1]) if rel else (a[0], a[1])
            path.lineTo(x, y)
        elif up == "H":
            x = x + a[0] if rel else a[0]
            path.lineTo(x, y)
        elif up == "V":
            y = y + a[0] if rel else a[0]
            path.lineTo(x, y)
        elif up == "C":
            p1 = (x + a[0], y + a[1]) if rel else (a[0], a[1])
            p2 = (x + a[2], y + a[3]) if rel else (a[2], a[3])
            p3 = (x + a[4], y + a[5]) if rel else (a[4], a[5])
            path.cubicTo(QPointF(*p1), QPointF(*p2), QPointF(*p3))
            x, y = p3
        elif up == "A":
            ex, ey = (x + a[5], y + a[6]) if rel else (a[5], a[6])
            _arc_to(path, x, y, a[0], a[1], a[2], a[3] != 0, a[4] != 0, ex, ey)
            x, y = ex, ey
    return path


@lru_cache(maxsize=64)
def path_of(name: str) -> QPainterPath:
                                       

                                               
       
    out = QPainterPath()
    for s in _shapes(name):
        if s.get("t") == "path":
            out.addPath(_build(s.get("d") or ""))
        elif s.get("t") == "circle":
            out.addEllipse(QPointF(s["cx"], s["cy"]), s["r"], s["r"])
        elif s.get("t") == "rect":
            r = QRectF(s["x"], s["y"], s["w"], s["h"])
            if s.get("rx"):
                out.addRoundedRect(r, s["rx"], s["rx"])
            else:
                out.addRect(r)
    return out


                                                                            
    
                                                                            
def paint(p: QPainter, name: str, rect: QRectF, color: QColor,
          sw: float = DEFAULT_SW, opacity: float = 1.0) -> None:
                        

                                    
                 
       
    shapes = _shapes(name)
    if not shapes or rect.width() <= 1 or rect.height() <= 1:
        return
    s = min(rect.width(), rect.height()) / VB
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.translate(rect.center().x() - VB * s / 2.0, rect.center().y() - VB * s / 2.0)
    p.scale(s, s)

    for sh in shapes:
        p.save()
        p.setOpacity(opacity * float(sh.get("o", 1.0)))
        stroke = None if sh.get("k") == "none" else color
        pen = QPen(stroke if stroke is not None else Qt.GlobalColor.transparent,
                   sw)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        if sh.get("dash"):
                                                              
                                                     
                                           
            pen.setDashPattern([float(v) / sw for v in sh["dash"].split()])
        p.setPen(pen if stroke is not None else Qt.PenStyle.NoPen)
        p.setBrush(color if sh.get("f") else Qt.BrushStyle.NoBrush)

        t = sh.get("t")
        if t == "path":
            p.drawPath(_build(sh.get("d") or ""))
        elif t == "circle":
            p.drawEllipse(QPointF(sh["cx"], sh["cy"]), sh["r"], sh["r"])
        elif t == "rect":
            r = QRectF(sh["x"], sh["y"], sh["w"], sh["h"])
            if sh.get("rx"):
                p.drawRoundedRect(r, sh["rx"], sh["rx"])
            else:
                p.drawRect(r)
        p.restore()
    p.restore()


def pixmap(name: str, size: int, color: QColor, sw: float = DEFAULT_SW,
           ratio: float = 2.0) -> QPixmap:
                                               
    pm = QPixmap(int(size * ratio), int(size * ratio))
    pm.setDevicePixelRatio(ratio)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    paint(p, name, QRectF(0, 0, size, size), color, sw)
    p.end()
    return pm


def qicon(name: str, size: int, color: QColor, sw: float = DEFAULT_SW) -> QIcon:
    return QIcon(pixmap(name, size, color, sw))
