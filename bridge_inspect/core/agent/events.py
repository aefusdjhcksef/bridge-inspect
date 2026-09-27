                

                                                      
              

                                                   
                                                 
                                                     
                                                               
                                                 
                                           
                                                                 
                
   

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

                                  
                                              
AGENTS: dict[str, tuple[str, str, str]] = {
    "system":      ("系统",     "任务编排与状态广播",       "#5C6E8A"),
    "orchestrator": ("桥智·总控", "理解意图、编排专家、汇总结论", "#22D3EE"),
    "mission":     ("巡检定线", "把自然语言请求解析成结构化巡检范围", "#3B82F6"),
    "vision":      ("视觉检测", "识别七类病害并审计采集质量",     "#F87171"),
    "quant":       ("分割量化", "像素级提取轮廓并换算实际尺寸",   "#A78BFA"),
    "trend":       ("趋势研判", "跨批次比对并按规范条文定级",     "#FBBF24"),
    "refly":       ("复飞决策", "反解复飞航点与云台姿态",         "#FB923C"),
    "report":      ("报告编制", "装配巡检报告并登记产物",         "#34D399"),
}

                           
KINDS = (
    "run_start",          
    "thought",                                   
    "delegate",                
    "tool_call",          
    "tool_result",        
    "decision",           
    "artifact",           
    "warning",             
    "error",            
    "run_end",            
)


def _jsonable(obj: Any) -> Any:
                                   

                                                    
                          
       
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_jsonable(v) for v in obj]
    item = getattr(obj, "item", None)                    
    if callable(item) and getattr(obj, "ndim", None) == 0:
        try:
            return item()
        except (ValueError, TypeError):
            pass
    shape = getattr(obj, "shape", None)                  
    if shape is not None:
        return f"<array{tuple(shape)}>"
    isoformat = getattr(obj, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(obj)


@dataclass
class AgentEvent:
                   

    seq: int = 0
    ts: float = 0.0
    t_rel: float = 0.0
    agent: str = "system"
    kind: str = "thought"
    title: str = ""
    detail: str = ""
    data: dict = field(default_factory=dict)
    duration_ms: int = 0
    level: str = "info"                                           
    parent: int | None = None                          
    planner: str = "rule"                                          
    call_id: str = ""                                               

    @property
    def agent_cn(self) -> str:
        return AGENTS.get(self.agent, (self.agent, "", ""))[0]

    @property
    def color(self) -> str:
        return AGENTS.get(self.agent, ("", "", "#5C6E8A"))[2]

    def to_dict(self) -> dict:
        d = {
            "seq": self.seq, "ts": self.ts, "t_rel": round(self.t_rel, 3),
            "agent": self.agent, "agent_cn": self.agent_cn, "color": self.color,
            "kind": self.kind, "title": self.title, "detail": self.detail,
            "data": _jsonable(self.data), "duration_ms": self.duration_ms,
            "level": self.level, "parent": self.parent,
            "planner": self.planner, "call_id": self.call_id,
        }
        return d

    def sse(self) -> str:
                                                          
                                 
        return "data: " + json.dumps(self.to_dict(), ensure_ascii=False) + "\n\n"


class AgentTracer:
                                                    

    def __init__(self, on_event: Callable[[AgentEvent], None] | None = None,
                 max_events: int = 400):
        self.events: list[AgentEvent] = []
        self._on_event = on_event
        self._max = max_events
        self._t0 = time.time()
        self._seq = 0
        self.planner = "rule"

                                                                           
    def emit(self, kind: str, title: str, agent: str = "system", *,
             detail: str = "", data: dict | None = None, level: str = "info",
             parent: int | None = None, duration_ms: int = 0,
             call_id: str = "") -> AgentEvent:
        self._seq += 1
        ev = AgentEvent(
            seq=self._seq, ts=time.time(), t_rel=time.time() - self._t0,
            agent=agent, kind=kind, title=title, detail=detail,
            data=data or {}, level=level, parent=parent,
            planner=self.planner, call_id=call_id, duration_ms=duration_ms,
        )
                                          
        if len(self.events) < self._max:
            self.events.append(ev)
            if self._on_event:
                self._on_event(ev)
        return ev

                                                                           
    def timer(self) -> "StepTimer":
        return StepTimer()

    def to_list(self) -> list[dict]:
        return [e.to_dict() for e in self.events]

    def dumps(self, **kw) -> str:
        return json.dumps(self.to_list(), ensure_ascii=False, **kw)

    def save_jsonl(self, path) -> None:
                                       
                      
        from pathlib import Path
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for e in self.events:
                f.write(json.dumps(e.to_dict(), ensure_ascii=False) + "\n")


class StepTimer:
                                                  

    def __init__(self):
        self.ms = 0

    def __enter__(self) -> "StepTimer":
        self._t = time.perf_counter()
        return self

    def __exit__(self, *exc) -> None:
        self.ms = int((time.perf_counter() - self._t) * 1000)
