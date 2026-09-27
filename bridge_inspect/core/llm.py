                      

                                                
                                     

          
                                    
                                                 
                                          

                            
   

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from .. import config as cfg
from .. import db

SYSTEM_PROMPT = (
    "你是铁路桥梁养护领域的技术人员，擅长依据巡检量化数据分析病害发展趋势并给出养护建议。"
    "请严格依据用户提供的量化数据作答，不要编造未提供的数值。"
    "回答使用简体中文，先给结论，再给依据，最后按"
    "【观察 / 维修 / 加固】三档给出处置建议。总长度控制在 400 字以内。"
)


@dataclass
class LLMResult:
    text: str
    offline: bool = False
    error: str = ""
    model: str = ""


                                                                            
       
                                                                            
def build_context(point_ids: list[str] | None = None) -> str:
                                   
    rows = db.timeseries_overview()
    if point_ids:
        want = set(point_ids)
        rows = [r for r in rows if r["point_id"] in want]

    if not rows:
        return "当前数据库中没有可用的病害量化记录。"

    lines = ["点位,构件,病害类别,批次,样本数,平均面积(cm2),最大宽度(mm)"]
    for r in rows:
        lines.append(
            f"{r['point_id']},{cfg.point_component(r['point_id'])},{r['cls_name']},"
            f"{r['batch']},{r['n']},{r['area']:.2f},{(r['width'] or 0):.2f}"
        )
    s = db.stat_summary()
    head = (
        f"数据说明：共 {s['points']} 个点位、{s['segments']} 条量化记录，"
        f"覆盖 {len(cfg.BATCHES)} 个巡检批次"
        f"（{'、'.join(b.name + ' ' + b.date for b in cfg.BATCHES)}）。"
    )
    return head + "\n" + "\n".join(lines)


def _fmt_summary() -> str:
    return build_context()


                                                                            
        
                                                                            
def _endpoint(settings: dict) -> str:
    base = (settings.get("llm_base_url") or "").strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


def _default_model(settings: dict) -> str:
                                               
    provider = cfg.normalize_llm_provider(settings.get("llm_provider"))
    return cfg.LLM_PROVIDER_PRESETS[provider]["model"]


def chat(question: str, settings: dict | None = None,
         context: str | None = None, timeout: int = 45) -> LLMResult:
                               
    s = settings or cfg.load_settings()
    ctx = context if context is not None else _fmt_summary()
    model = s.get("llm_model", "")

    if not s.get("llm_enabled") or not s.get("llm_api_key"):
        return LLMResult(text=offline_answer(question, ctx), offline=True,
                         error="未启用大模型 API（未配置密钥），已使用本地规则研判",
                         model="local-rule")

    url = _endpoint(s)
    if not url:
        return LLMResult(text=offline_answer(question, ctx), offline=True,
                         error="未填写 API 地址，已使用本地规则研判", model="local-rule")

    payload = {
        "model": model or _default_model(s),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"【巡检量化数据】\n{ctx}\n\n【问题】\n{question}"},
        ],
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {s.get('llm_api_key')}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"].strip()
        return LLMResult(text=text, offline=False, model=model)
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError, OSError) as exc:
        return LLMResult(text=offline_answer(question, ctx), offline=True,
                         error=f"API 调用失败：{exc}，已使用本地规则研判",
                         model="local-rule")


def is_dashscope(settings: dict) -> bool:
                      

                                                  
                                                     
                               
       
    s = settings or {}
    if "dashscope" in (s.get("llm_base_url") or "").lower():
        return True
    return cfg.normalize_llm_provider(s.get("llm_provider")) == "dashscope"


def chat_raw(messages: list[dict], tools: list[dict] | None = None,
             settings: dict | None = None, timeout: int = 60,
             temperature: float = 0.1) -> dict:
                                              

                                                
                                                     
                                            

                                                                 
                                                 

                                                  
         
       
    s = settings or cfg.load_settings()
    model = s.get("llm_model") or _default_model(s)
    url = _endpoint(s)
    if not url:
        return {"ok": False, "message": {}, "error": "未填写 API 地址", "model": model}
    if not s.get("llm_api_key"):
        return {"ok": False, "message": {}, "error": "未配置 API Key", "model": model}

    payload: dict = {
        "model": model,
        "messages": messages,
                              
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools
                                                            
                                               
        payload["tool_choice"] = "auto"
    if is_dashscope(s):
                                                  
        payload["enable_thinking"] = False

    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {s.get('llm_api_key')}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        msg = data["choices"][0]["message"]
        return {"ok": True, "message": msg, "error": "", "model": model}
    except urllib.error.HTTPError as exc:
                                           
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except OSError:
            pass
        return {"ok": False, "message": {}, "model": model,
                "error": f"HTTP {exc.code} {detail}"}
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError, OSError) as exc:
        return {"ok": False, "message": {}, "error": str(exc), "model": model}


def test_connection(settings: dict) -> tuple[bool, str]:
                       
    if not settings.get("llm_api_key"):
        return False, "请先填写 API Key"
    probe = dict(settings)
    probe["llm_enabled"] = True
    res = chat("请回复：连接正常", probe, context="（连接测试，无需分析数据）", timeout=20)
    if res.offline:
        return False, res.error or "连接失败"
    return True, f"连接正常，模型：{res.model}"


                                                                            
        
                                                                            
def _trend_of(point_id: str, cls_key: str) -> dict | None:
                      

                                          
                                        
       
    rows = db.timeseries(point_id, cls_key)
    if not rows:
        return None

    per_batch: dict[str, dict] = {}
    for r in rows:
        b = r["batch"] or "—"
        slot = per_batch.setdefault(b, {"area": [], "width": 0.0, "name": r["cls_name"]})
        slot["area"].append(float(r["area_cm2"]))
        slot["width"] = max(slot["width"], float(r["max_width_mm"] or 0.0))

    order = [b.id for b in cfg.BATCHES]
    seq = [(b, per_batch[b]) for b in order if b in per_batch]
    for b in per_batch:                                 
        if b not in order:
            seq.append((b, per_batch[b]))
    if len(seq) < 2:
        return None

    def batch_area(slot: dict) -> float:
        vals = slot["area"]
                                          
                         
        return max(vals) if vals else 0.0

    b0, s0 = seq[0]
    b1, s1 = seq[-1]
    area0, area1 = batch_area(s0), batch_area(s1)
    if area0 <= 0:
        return None

    return {
        "point": point_id,
        "cls": cls_key,
        "cls_name": s1["name"],
        "batch0": b0,
        "batch1": b1,
        "n": len(rows),
        "n_batch": len(seq),
        "area0": area0,
        "area1": area1,
        "growth": (area1 - area0) / area0,
        "width": s1["width"],
        "component": cfg.point_component(point_id),
    }


def detect_anomalies(growth_threshold: float = 0.30) -> list[dict]:
                                   

                                                  
                 
       
    pairs = {(r["point_id"], r["cls_key"]) for r in db.timeseries_overview()}
    out = []
    for point_id, cls_key in sorted(pairs):
        t = _trend_of(point_id, cls_key)
        if t and t["growth"] >= growth_threshold:
            t["level"] = "显著发展" if t["growth"] >= 0.6 else "缓慢发展"
            out.append(t)
    out.sort(key=lambda x: -x["growth"])
    return out


def _grade(growth: float, width_mm: float, severity: str,
           cls_key: str = "") -> tuple[str, str]:
                             

                                                       
                                                
                             

                                          
                                           
                                               
                            
       
    dc = cfg.DISEASE_BY_KEY.get(cls_key)
    limit = dc.width_limit_mm if dc else None
    over_width = limit is not None and width_mm >= limit
                               
    near_width = limit is not None and width_mm >= limit * 0.8
    unit = "错台量" if cls_key == "joint_offset" else "宽度"

    if over_width or growth >= 0.6 or (severity == "高" and growth >= 0.35):
        why = (f"{unit} {width_mm:.2f} mm 已超规范限值 {limit:g} mm，"
               f"建议安排专项检测并编制加固方案") if over_width else \
              ("病害发展较快，建议安排专项检测并编制加固方案")
        return "加固", why
    if growth >= 0.25 or near_width:
        why = (f"{unit} {width_mm:.2f} mm 已接近规范限值 {limit:g} mm，"
               f"建议在下个巡检周期前安排维修处理") if near_width and growth < 0.25 else \
              ("病害持续发展，建议在下个巡检周期前安排维修处理")
        return "维修", why
    return "观察", "病害发展平缓，维持现有巡检周期继续观察"


def offline_answer(question: str, context: str = "") -> str:
                                      
    import re

    q = (question or "").strip()
    overview = db.timeseries_overview()

                                 
    targets: list[dict] = []
    for h in re.findall(r"[A-Fa-f]\d{2}", q):
        pid = h.upper()
        if any(t["point"] == pid for t in targets):
            continue
        for r in overview:
            if r["point_id"] == pid:
                targets.append({"point": pid, "cls": r["cls_key"]})
                break

    lines: list[str] = []
    if targets:
        for t in targets:
            tr = _trend_of(t["point"], t["cls"])
            if not tr:
                lines.append(f"· {t['point']}（{cfg.point_component(t['point'])}）："
                             f"暂无可用于趋势对比的多批次记录。")
                continue
            grade, advice = _grade(tr["growth"], tr["width"],
                                   cfg.DISEASE_BY_KEY[tr["cls"]].severity,
                                   tr["cls"])
            lines.append(
                f"· {tr['point']}（{tr['component']}）{tr['cls_name']}："
                f"面积由 {tr['area0']:.1f} cm² 发展至 {tr['area1']:.1f} cm²，"
                f"累计增幅 {tr['growth'] * 100:+.1f}%，"
                f"最新最大宽度 {tr['width']:.2f} mm。"
                f"处置建议：{grade}——{advice}。"
            )
    else:
        anom = detect_anomalies()
        lines.append("未在问题中识别到具体点位，以下为全桥汇总：")
        if anom:
            for a in anom[:8]:
                lines.append(
                    f"· {a['point']}（{a['component']}）{a['cls_name']}："
                    f"累计增幅 {a['growth'] * 100:+.1f}%，判为{a['level']}。"
                )
        else:
            lines.append("· 当前各点位病害量化指标变化均未超过异常阈值。")

    s = db.stat_summary()
    head = (f"【离线规则研判】本次分析基于数据库内 {s['segments']} 条量化记录、"
            f"{s['points']} 个点位，未调用大模型 API。")
    tail = ("说明：以上结论由本地阈值规则自动生成。配置大模型 API 后可获得结合"
            "构件类型与历史趋势的综合研判文本。")
    return head + "\n" + "\n".join(lines) + "\n\n" + tail
