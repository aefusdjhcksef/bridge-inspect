                                       

            

                                           
                                              
               

                         
                                                  
                           
                                                               
                     

                                            

                       

                                             
                                         
                                    
   

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ... import config as cfg

                                              
                                            
                                           
WANT_ORDER = ("import", "overview", "detect", "quantify", "trend",
              "anomaly", "grade", "reflight", "report")

WANT_CN = {
    "import": "图像导入", "overview": "数据总览", "detect": "病害检测",
    "quantify": "分割量化", "trend": "趋势研判", "anomaly": "异常筛查",
    "grade": "按条文定级", "reflight": "复飞决策", "report": "报告编制",
}

                                            
_WANT_KW: dict[str, tuple[str, ...]] = {
                                          
                                    
    "import": ("导入", "入库", "存储卡", "sd卡", "SD卡", "读进来", "导进来",
               "新拍的", "扫描文件夹", "图片怎么进来", "落库"),
    "overview": ("概览", "总览", "概况", "规模", "有哪些", "多少", "数据情况", "库里"),
    "detect": ("检测", "识别", "检出", "有没有病害", "找出", "发现", "看看图"),
    "quantify": ("量化", "分割", "测量", "量一下", "尺寸", "面积", "宽度", "轮廓"),
    "trend": ("趋势", "发展", "变化", "对比", "比较", "历次", "跨批次", "几期", "演变",
              "情况", "怎么样"),
    "anomaly": ("异常", "最快", "最严重", "优先", "重点", "突出问题", "哪几处", "隐患"),
    "grade": ("定级", "等级", "处置", "建议", "规范", "依据", "条文", "怎么处理", "措施"),
                                               
                                         
    "reflight": ("复飞", "重拍", "补拍", "复拍", "采集质量", "清晰度", "分辨率",
                 "模糊", "重合率", "拍得清", "拍不清", "看不清", "不清楚", "拍不"),
    "report": ("报告", "汇总", "总结", "文档", "说明书", "出一份", "生成报告"),
}

                                      
                                            
_AUTO_INSPECT_KW = ("自动巡检", "一键巡检", "完整巡检", "全流程巡检", "自动分析")

                                                          
                                                       
                                               
                    
_NOT_ALNUM = r"(?<![0-9A-Za-z])"
_NOT_DIGIT = r"(?![0-9])"
_POINT_RE = re.compile(_NOT_ALNUM + r"([A-Fa-f]\d{2})" + _NOT_DIGIT)
_BATCH_RE = re.compile(_NOT_ALNUM + r"(P[1-9])" + _NOT_DIGIT, re.I)
                                             
_COMP_RE = re.compile(_NOT_ALNUM + r"([A-Fa-f])\s*(?:区|构件|号构件|类构件)")
_ALL_BATCH_KW = ("三个批次", "3个批次", "三期", "全部批次", "所有批次", "每个批次",
                 "各批次", "历次批次", "三个周期")

                                     
                                              
                                       
_COMP_WORDS: tuple[tuple[str, str], ...] = (
    ("桥墩", "A"), ("墩柱", "A"), ("墩身", "A"),
    ("梁底", "B"), ("底板", "B"),
    ("支座", "C"),
    ("腹板", "D"), ("梁侧", "D"), ("侧腹板", "D"),
    ("桥台", "E"), ("台身", "E"), ("台帽", "E"),
    ("伸缩缝", "F"), ("伸缩装置", "F"),
)

                                               
                                      
_CLASS_WORDS: dict[str, tuple[str, ...]] = {
    "crack": ("裂缝", "裂纹", "开裂"),
    "spalling": ("剥落", "掉块", "脱落", "空鼓"),
    "exposed_bar": ("露筋", "钢筋外露", "锈胀"),
    "seepage": ("渗水", "泛碱", "漏水", "湿渍"),
    "honeycomb": ("蜂窝", "麻面"),
    "bearing": ("支座", "滑移", "脱空"),
    "joint_offset": ("错台", "伸缩缝", "接缝"),
}


@dataclass
class Slot:
                       
    task: str = ""
    points: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    batches: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    wants: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"task": self.task, "points": self.points, "classes": self.classes,
                "batches": self.batches, "components": self.components,
                "wants": self.wants,
                "want_cn": [WANT_CN.get(w, w) for w in self.wants]}

    def describe(self) -> str:
                                                        
        bits: list[str] = []
        bits.append(f"{len(self.points)} 个点位"
                    + (f"（{'、'.join(self.points[:6])}"
                       + ("…" if len(self.points) > 6 else "") + "）"
                       if self.points else ""))
        if self.classes:
            bits.append("病害类别 " + "、".join(
                cfg.DISEASE_BY_KEY[c].name for c in self.classes
                if c in cfg.DISEASE_BY_KEY))
        bits.append(f"{len(self.batches)} 个批次"
                    + (f"（{'、'.join(self.batches)}）" if self.batches else ""))
        plan = "、".join(WANT_CN.get(w, w) for w in self.wants)
        return f"{'，'.join(bits)}；执行 " + (plan or "常规分析")


def parse_slots(task: str) -> Slot:
                                           
    t = (task or "").strip()
    s = Slot(task=t)

              
    seen: set[str] = set()
    for m in _POINT_RE.finditer(t):
        p = m.group(1).upper()
        if p not in seen:
            seen.add(p)
            s.points.append(p)

                
    for key, words in _CLASS_WORDS.items():
        if any(w in t for w in words) and key not in s.classes:
            s.classes.append(key)

              
    for m in _BATCH_RE.finditer(t):
        b = m.group(1).upper()
        if b in cfg.BATCH_BY_ID and b not in s.batches:
            s.batches.append(b)
    if not s.batches and any(k in t for k in _ALL_BATCH_KW):
        s.batches = [b.id for b in cfg.BATCHES]
    s.batches.sort()

              
    for m in _COMP_RE.finditer(t):
        c = m.group(1).upper()
        if c not in s.components:
            s.components.append(c)
                                          
    for word, letter in _COMP_WORDS:
        if word in t and letter not in s.components:
            s.components.append(letter)
    s.components.sort()

              
    for want, words in _WANT_KW.items():
        if any(w in t for w in words):
            s.wants.append(want)

    if any(k in t for k in _AUTO_INSPECT_KW):
        s.wants = list(WANT_ORDER)

                                             
                     
    if s.components and not s.points:
        s.points = [p for p in cfg.ALL_POINTS if p[:1] in s.components]
    elif s.components and s.points:
                                                   
        s.points = [p for p in s.points if p[:1] in s.components] or s.points

                                    
    if not s.wants:
        s.wants = ["trend"]
                                
    if s.classes and "trend" not in s.wants and "grade" not in s.wants:
        s.wants.append("grade")

                                               
                                               
               
    if "grade" in s.wants and "trend" not in s.wants:
        s.wants.append("trend")
                                           
                                                  
                    
    if "report" in s.wants:
        for w in ("import", "overview", "trend", "anomaly", "grade"):
            if w not in s.wants:
                s.wants.append(w)
                                 
    if "detect" in s.wants and "quantify" not in s.wants:
        s.wants.append("quantify")

    s.wants = [w for w in WANT_ORDER if w in s.wants]
    return s


                                                                            
       
                                                                            
@dataclass
class Plan:
    slots: Slot
    source: str = "rule"                                      
    note: str = ""                            
    error: str = ""

    def to_dict(self) -> dict:
        return {"slots": self.slots.to_dict(), "source": self.source,
                "note": self.note, "error": self.error}


class RulePlanner:
                                              

    name = "rule"

    def available(self) -> bool:
        return True

    def plan(self, task: str) -> Plan:
        s = parse_slots(task)
        return Plan(slots=s, source="rule",
                    note="按关键词与正则拆解巡检范围（本地规则引擎，未调用大模型）")


                                                                            
        
                                                                            
PLANNER_SYSTEM = """你是「桥智」巡检系统的任务总控智能体，负责把用户的自然语言请求\
拆解成对工具的调用序列，全程使用简体中文。

系统下有六位专业智能体，各管一摊：
- 巡检定线：解析巡检范围，把新拍的影像读入库，查点位清单与航点档案
- 视觉检测：对影像做七类病害识别（裂缝/剥落掉块/露筋/渗水泛碱/蜂窝麻面/支座滑移/伸缩缝错台）
- 分割量化：像素级分割并换算实际尺寸与量测不确定度
- 趋势研判：跨批次比对、按规范条文定级
- 复飞决策：审计采集质量并反解复飞航点
- 报告编制：装配完整巡检报告

工作要求：
1. 先摸清数据边界（db_overview），再针对具体点位取数，不要凭空假设点位编号。
   若用户提到新拍的影像、存储卡、入库，先调 import_images 把它们读进来。
2. 数值一律由工具产出，你不要自己计算或编造任何数字。
3. 用户点名了点位就针对这些点位；只说构件范围（如"C 区支座"）就先查该范围内的点位。
4. 用户要求出报告时，先把检测、趋势、异常、定级都跑过再编报告，否则报告里是空的。
5. 结论要引用工具返回的条文出处。

你可以直接调用工具。若不便调用工具，也可以只输出一个 JSON 计划，格式为：
{"thoughts": "你的分析思路", "steps": [{"tool": "工具名", "args": {...}}]}
不要输出任何其他内容。"""


class LLMPlanner:
                                                    

    name = "llm"

    def __init__(self, settings: dict | None = None):
        from .. import llm
        self.settings = settings if settings is not None else cfg.load_settings()
        self._llm = llm
        self.model = self.settings.get("llm_model") or "qwen-plus"

    def available(self) -> bool:
                                                     
                                                  
        return cfg.llm_ready(self.settings)

    def tools(self) -> list[dict]:
        from . import tools as T
        return T.openai_tools()

    def turn(self, messages: list[dict], timeout: int = 60) -> dict:
                                           
        return self._llm.chat_raw(messages, tools=self.tools(),
                                  settings=self.settings, timeout=timeout)

    def seed(self, task: str, slots: Slot) -> list[dict]:
                         

                                               
                                       
           
        hint = (f"\n\n【本地预解析】{slots.describe()}\n"
                f"请在此基础上判断该调用哪些工具；若预解析有误，以你的判断为准。")
        return [{"role": "system", "content": PLANNER_SYSTEM},
                {"role": "user", "content": task + hint}]

    @staticmethod
    def parse_text_plan(text: str) -> dict | None:
                             

                                                            
                                              
           
        if not text:
            return None
        raw = text.strip()
        if "```" in raw:                                           
            for block in raw.split("```")[1::2]:
                raw = block.strip()
                if raw.lower().startswith("json"):
                    raw = raw[4:].strip()
                break
        for opener, closer in (("{", "}"), ("[", "]")):
            i, j = raw.find(opener), raw.rfind(closer)
            if i < 0 or j <= i:
                continue
            try:
                obj = json.loads(raw[i:j + 1])
            except (ValueError, TypeError):
                continue
            if isinstance(obj, dict) and isinstance(obj.get("steps"), list):
                return obj
            if isinstance(obj, list) and obj and isinstance(obj[0], dict):
                return {"steps": obj}
        return None


def make_planner(settings: dict | None = None):
                           

                                               
                             
       
    p = LLMPlanner(settings)
    return p if p.available() else RulePlanner()


def planner_mode(settings: dict | None = None) -> str:
    return "llm" if LLMPlanner(settings).available() else "rule"
