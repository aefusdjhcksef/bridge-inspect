                                          

                                        
                     
   

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

                                                                            
    
                                                                            
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
IMG_DIR = DATA_DIR / "images"                      
OUT_DIR = DATA_DIR / "outputs"                          
MODELS_DIR = ROOT / "models"                                            
DB_PATH = DATA_DIR / "bridge_inspect.db"
SETTINGS_PATH = DATA_DIR / "settings.json"
CORE_DIR = ROOT / "bridge_inspect" / "core"
HERO_SVG = CORE_DIR / "login_hero.svg"                   

for _d in (DATA_DIR, IMG_DIR, OUT_DIR, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

APP_NAME = "桥梁智巡"
APP_NAME_EN = "BRIDGE INSPECTION SUITE"
APP_TITLE = "面向铁路桥梁的同视场无人机病害巡检分析系统"
APP_VERSION = "v1.0"

                                                                            
      
                                                                            
                                                            
                                         
                                       
REPORT_NO_PREFIX = "BIS"                                                
REPORT_ORG = "桥梁智巡巡检数据分析中心"                                              
                                         
        
REPORT_CHECKER = ""
REPORT_APPROVER = ""

                                                                            
        
                                              
                                     
                                                                            


@dataclass(frozen=True)
class DiseaseClass:
    id: int
    key: str
    name: str
    color: str
    severity: str                              
    suggestion: str                     
                                         
                                                  
                                                   
                                        
    width_limit_mm: float | None = None


DISEASES: tuple[DiseaseClass, ...] = (
    DiseaseClass(0, "crack",        "裂缝",       "#F87171", "高", "观测裂缝宽度与长度发展，超限时灌注封闭", 0.30),
    DiseaseClass(1, "spalling",     "剥落掉块",   "#FBBF24", "高", "凿除松散层后修补，防止钢筋进一步外露"),
    DiseaseClass(2, "exposed_bar",  "露筋",       "#A78BFA", "高", "除锈阻锈处理后高强砂浆修复保护层"),
    DiseaseClass(3, "seepage",      "渗水泛碱",   "#38BDF8", "中", "排查防水层与排水通道，清理析出物"),
    DiseaseClass(4, "honeycomb",    "蜂窝麻面",   "#34D399", "低", "表面封闭处理，观察是否伴随渗水"),
    DiseaseClass(5, "bearing",      "支座滑移",   "#FB923C", "高", "复测支座位移量，必要时顶升复位"),
    DiseaseClass(6, "joint_offset", "伸缩缝错台", "#F472B6", "中", "清理缝内杂物，复核错台量并调整", 5.0),
)

DISEASE_BY_KEY = {d.key: d for d in DISEASES}
DISEASE_BY_ID = {d.id: d for d in DISEASES}
DISEASE_NAMES = [d.name for d in DISEASES]
COLOR_BY_KEY = {d.key: d.color for d in DISEASES}


def disease_color(key: str) -> str:
                                  
    return COLOR_BY_KEY.get(key, "#8FA3C0")


                                                                            
         
                                     
                                                                            
COMPONENTS: dict[str, str] = {
    "A": "桥墩",
    "B": "梁底",
    "C": "支座",
    "D": "梁侧腹板",
    "E": "桥台",
    "F": "伸缩缝",
}

POINT_PREFIX_ORDER = ("A", "B", "C", "D", "E", "F")


def make_point_id(prefix: str, index: int) -> str:
                                     
    return f"{prefix}{index:02d}"


def point_component(point_id: str) -> str:
                                      
    return COMPONENTS.get(point_id[:1].upper(), "其他构件") if point_id else "未指定"


ALL_POINTS: list[str] = [
    make_point_id(p, i) for p in POINT_PREFIX_ORDER for i in range(1, 9)
]

                                                                            
      
                                        
                                          
                            
                                                                            
BRIDGE_LEN_M = 120.0                       
BRIDGE_WIDTH_M = 12.0            
PIER_SPACING_M = 20.0           

                                     
                                        
                                           
ORIGIN_LAT = 32.0512400
ORIGIN_LON = 118.7426100

M_PER_DEG_LAT = 110540.0


def m_per_deg_lon(lat: float) -> float:
                       

                                              
                            
       
    return 111320.0 * math.cos(math.radians(lat))


                            
                                      
                                                      
WAYPOINT_PLAN_M: dict[str, tuple[float, float]] = {
               
    "A01": (20.0, 0.0), "A03": (60.0, 0.0),
                     
    "B02": (30.0, 0.0), "B05": (90.0, 0.0),
                                            
    "C01": (20.0, 3.6), "C03": (60.0, -3.6),
                         
    "D02": (30.0, 6.0), "D05": (90.0, 6.0),
}

                                         
                                       
COMPONENT_OFFSET_M: dict[str, float] = {
    "A": 0.0,               
    "B": 0.0,              
    "C": 3.6,            
    "D": 6.0,               
    "E": 0.0,           
    "F": 0.0,                  
}


                                    
                                 
                                   
COMPONENT_SPAN_M: dict[str, tuple[float, float]] = {
    "A": (PIER_SPACING_M, BRIDGE_LEN_M - PIER_SPACING_M),
    "B": (PIER_SPACING_M / 2, BRIDGE_LEN_M - PIER_SPACING_M / 2),
    "C": (PIER_SPACING_M, BRIDGE_LEN_M - PIER_SPACING_M),
    "D": (PIER_SPACING_M / 2, BRIDGE_LEN_M - PIER_SPACING_M / 2),
    "E": (0.0, 0.0),                             
    "F": (PIER_SPACING_M, BRIDGE_LEN_M - PIER_SPACING_M),
}


def waypoint_plan(point_id: str) -> tuple[float, float]:
                                      

                                         
                                             
                                
       
    if point_id in WAYPOINT_PLAN_M:
        return WAYPOINT_PLAN_M[point_id]
    prefix = point_id[:1].upper()
    try:
        idx = max(1, min(8, int(point_id[1:])))
    except ValueError:
        idx = 1
    if prefix == "F":
                                               
                                                     
                                
                                               
        return (PIER_SPACING_M * ((idx - 1) % 4 + 1), 1.8 if idx <= 4 else -1.8)
    lo, hi = COMPONENT_SPAN_M.get(prefix, (0.0, BRIDGE_LEN_M))
    if hi <= lo:
                                           
                                                  
                                              
        return (0.0 if idx <= 4 else BRIDGE_LEN_M,
                1.8 if idx % 2 else -1.8)
    station = lo + (idx - 1) / 7.0 * (hi - lo)
    return (station, COMPONENT_OFFSET_M.get(prefix, 0.0))

                                                                            
      
                                                                            


@dataclass(frozen=True)
class Batch:
    id: str
    name: str
    date: str
    note: str


BATCHES: tuple[Batch, ...] = (
    Batch("P1", "第 1 次飞行", "2026-03-12", "初始基准期，建立全桥基准影像库"),
    Batch("P2", "第 2 次飞行", "2026-06-18", "汛期前复检，重点复核支座与梁底"),
    Batch("P3", "第 3 次飞行", "2026-09-05", "汛期后复检，关注渗水与裂缝发展"),
)

BATCH_BY_ID = {b.id: b for b in BATCHES}
BATCH_NAMES = [b.name for b in BATCHES]

                                                                            
           
                                                                            
OVERLAP_OK = 0.85                                            
OVERLAP_WARN = 0.92                         

                                                  
                                                  
                                                  
                                  
CAM_FOCAL_MM = 24.0
CAM_PIXEL_UM = 2.4
CAM_SENSOR_MP = 20.0

                                             
                                  
SEGMENT_CLASSES = ("crack",)


def gsd_mm_per_px(distance_m: float, focal_mm: float = CAM_FOCAL_MM,
                  pixel_um: float = CAM_PIXEL_UM, theta_deg: float = 0.0) -> float:
                               

                                             
                                                        
       
    if distance_m <= 0 or focal_mm <= 0:
        return 0.0
    base = pixel_um * distance_m / focal_mm
    if theta_deg:
        c = math.cos(math.radians(max(-89.0, min(89.0, theta_deg))))
        if c > 1e-6:
            base /= c
    return base


DEFAULT_SETTINGS: dict = {
    "detect_weights": "",                                   
    "segment_weights": "",                 
    "conf_thres": 0.35,
    "iou_thres": 0.45,
    "device": "auto",                                   
    "img_size": 960,
    "output_dir": str(OUT_DIR),
    "llm_provider": "openai",
    "llm_base_url": "https://api.openai.com/v1",
    "llm_api_key": "",
    "llm_model": "gpt-4o-mini",
    "llm_enabled": False,
    "last_username": "",
    "last_image_dir": "",                         
    "report_org": "",                                  
}

                                                  
                              
LLM_PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "openai": {
        "label": "OpenAI 兼容接口",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "deepseek": {
        "label": "DeepSeek（OpenAI 兼容）",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
    "dashscope": {
        "label": "阿里云百炼 DashScope",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
}


def normalize_llm_provider(value: str | None) -> str:
                                
    raw = (value or "").strip().lower()
    if raw in LLM_PROVIDER_PRESETS:
        return raw
    if "deepseek" in raw or "深度求索" in raw:
        return "deepseek"
    if "dashscope" in raw or "通义" in raw or "百炼" in raw:
        return "dashscope"
    return "openai"


def llm_provider_label(settings: dict | None = None) -> str:
    s = settings if settings is not None else load_settings()
    provider = normalize_llm_provider(s.get("llm_provider"))
    return LLM_PROVIDER_PRESETS[provider]["label"]


def load_settings() -> dict:
                                      
    cfg = dict(DEFAULT_SETTINGS)
    try:
        if SETTINGS_PATH.exists():
            cfg.update(json.loads(SETTINGS_PATH.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return cfg


def llm_ready(settings: dict | None = None) -> bool:
                        

                                                           
                                                                        
                                                  
                 

                                                      
       
    s = settings if settings is not None else load_settings()
    return bool(s.get("llm_enabled") and s.get("llm_api_key")
                and (s.get("llm_base_url") or "").strip())


def save_settings(cfg: dict) -> None:
    merged = dict(DEFAULT_SETTINGS)
    merged.update(cfg or {})
    tmp = SETTINGS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(SETTINGS_PATH)


