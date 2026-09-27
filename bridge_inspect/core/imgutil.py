                                 

                                                   
                                       
   

from __future__ import annotations

import functools
from pathlib import Path

import cv2
import numpy as np

                     
                                        
                                          
                                
_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\simsun.ttc",        
    r"C:\Windows\Fonts\msyh.ttc",            
    r"C:\Windows\Fonts\msyhl.ttc",
    r"C:\Windows\Fonts\simhei.ttf",        
)


@functools.lru_cache(maxsize=16)
def cjk_font(size: int):
                                         
    from PIL import ImageFont

    for p in _FONT_CANDIDATES:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def imread(path: str | Path) -> np.ndarray | None:
                              
    try:
        buf = np.fromfile(str(path), dtype=np.uint8)
        if buf.size == 0:
            return None
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)
    except (OSError, ValueError):
        return None


def imwrite(path: str | Path, bgr: np.ndarray) -> bool:
                       
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower() or ".png"
    ok, buf = cv2.imencode(ext, bgr)
    if not ok:
        return False
    buf.tofile(str(path))
    return True


def imread_gray(path: str | Path) -> np.ndarray | None:
    img = imread(path)
    return None if img is None else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


                                                                            
       
                                                                            
def fit_size(w: int, h: int, max_w: int, max_h: int) -> tuple[int, int]:
                                  
    if w <= 0 or h <= 0 or max_w <= 0 or max_h <= 0:
        return max(w, 1), max(h, 1)
    k = min(max_w / w, max_h / h)
    return max(int(w * k), 1), max(int(h * k), 1)


def clamp_box(x1: int, y1: int, x2: int, y2: int, w: int, h: int) -> tuple[int, int, int, int]:
    return (max(0, min(int(x1), w - 1)), max(0, min(int(y1), h - 1)),
            max(0, min(int(x2), w - 1)), max(0, min(int(y2), h - 1)))


def hex_to_bgr(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b, g, r)


                                                                            
       
                                                                            
def bgr_to_qimage(bgr: np.ndarray):
                                                  
    from PyQt6.QtGui import QImage

    if bgr is None:
        return QImage()
    if bgr.ndim == 2:
        bgr = cv2.cvtColor(bgr, cv2.COLOR_GRAY2BGR)
    rgb = np.ascontiguousarray(bgr[:, :, ::-1])
    h, w, _ = rgb.shape
    return QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()


def bgr_to_qpixmap(bgr: np.ndarray):
    from PyQt6.QtGui import QPixmap

    return QPixmap.fromImage(bgr_to_qimage(bgr))


                                                                            
      
                                                                            
def draw_detections(
    bgr: np.ndarray,
    dets: list,
    thickness: int = 2,
    show_label: bool = True,
) -> np.ndarray:
                     

                                                                             
       
    from PIL import Image, ImageDraw

    if bgr is None:
        return bgr
    out = bgr.copy()
    h, w = out.shape[:2]
    if not dets:
        return out

    pil = Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil)

    from ..config import disease_color

    box_w = max(2, thickness + 1)
    for d in dets:
        x1, y1, x2, y2 = clamp_box(d.x1, d.y1, d.x2, d.y2, w, h)
        color = disease_color(getattr(d, "cls_key", ""))
        rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))

                                   
        for i in range(box_w):
            draw.rectangle([x1 - i, y1 - i, x2 + i, y2 + i], outline=rgb)

        if not show_label:
            continue
        text = f"{d.cls_name} {d.conf:.2f}"
        font = cjk_font(max(13, int(min(w, h) * 0.022)))
        tb = draw.textbbox((0, 0), text, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        pad = 4
        ly = y1 - th - 2 * pad
        if ly < 0:
            ly = min(y2 + 1, h - th - 2 * pad)
        lx = min(x1, w - tw - 2 * pad)

        draw.rectangle([lx, ly, lx + tw + 2 * pad, ly + th + 2 * pad], fill=rgb)
                             
        lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        fg = (12, 20, 32) if lum > 150 else (255, 255, 255)
        draw.text((lx + pad - tb[0], ly + pad - tb[1]), text, font=font, fill=fg)

    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def draw_mask_overlay(bgr: np.ndarray, mask: np.ndarray, color_hex: str = "#22D3EE",
                      alpha: float = 0.45) -> np.ndarray:
                                
    if bgr is None or mask is None:
        return bgr
    if mask.shape[:2] != bgr.shape[:2]:
        mask = cv2.resize(mask, (bgr.shape[1], bgr.shape[0]),
                          interpolation=cv2.INTER_NEAREST)
    out = bgr.copy()
    m = (mask > 0)
    layer = np.zeros_like(out)
    layer[:] = hex_to_bgr(color_hex)
    out[m] = (out[m] * (1 - alpha) + layer[m] * alpha).astype(np.uint8)

    contours, _ = cv2.findContours((m.astype(np.uint8)) * 255,
                                   cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(out, contours, -1, hex_to_bgr(color_hex), 2)
    return out


def make_thumbnail(bgr: np.ndarray, size: tuple[int, int]) -> np.ndarray:
                           
    if bgr is None:
        return np.full((size[1], size[0], 3), 22, np.uint8)
    th, tw = size[1], size[0]
    h, w = bgr.shape[:2]
    k = min(tw / w, th / h)
    nw, nh = max(1, int(w * k)), max(1, int(h * k))
    resized = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.full((th, tw, 3), 22, np.uint8)
    x, y = (tw - nw) // 2, (th - nh) // 2
    canvas[y:y + nh, x:x + nw] = resized
    return canvas


def image_info(path: str | Path) -> tuple[int, int, float]:
                                        
    p = Path(path)
    try:
        kb = p.stat().st_size / 1024.0
    except OSError:
        kb = 0.0
    img = imread(p)
    if img is None:
        return 0, 0, kb
    h, w = img.shape[:2]
    return w, h, kb


SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def dialog_filter() -> str:
                                                   

                                                     
                                              
                                

                                         
                   
       
    return "影像文件 (%s)" % " ".join(f"*{e}" for e in sorted(SUPPORTED_EXT))


def is_supported(path: str | Path) -> bool:
                      

                                                                 
                                                       
                                
       
    return Path(path).suffix.lower() in SUPPORTED_EXT


def list_images_in(folder: str | Path) -> list[Path]:
    p = Path(folder)
    if not p.is_dir():
        return []
    return sorted(x for x in p.iterdir()
                  if x.is_file() and x.suffix.lower() in SUPPORTED_EXT)
