                                   

             

                                                                      
                                                 
                                                                 
                                                         
          

               

                                           
                                                                  
                                                
               

                  

                                             
                                               
                                           
   

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator

from ... import config as cfg
from ... import db
from . import tools as T
from .events import AGENTS, AgentEvent, AgentTracer
from .planner import LLMPlanner, Slot, make_planner, parse_slots

                                     
                               
MAX_ROUNDS = 8
                                      
                   
MAX_POINTS_PER_STEP = 12


@dataclass
class AgentRun:
    task: str = ""
    planner: str = "rule"
    answer: str = ""
    events: list[AgentEvent] = field(default_factory=list)
    artifacts: list[dict] = field(default_factory=list)
    ok: bool = True
    error: str = ""
    elapsed_ms: int = 0
    degraded: bool = False                           
    degrade_reason: str = ""

    def to_dict(self) -> dict:
        return {"task": self.task, "planner": self.planner, "answer": self.answer,
                "events": [e.to_dict() for e in self.events],
                "artifacts": self.artifacts, "ok": self.ok, "error": self.error,
                "elapsed_ms": self.elapsed_ms, "degraded": self.degraded,
                "degrade_reason": self.degrade_reason}


def _call_id(n: int) -> str:
    return f"c{n:03d}"


class Orchestrator:
                            

    def __init__(self, settings: dict | None = None, on_event=None,
                 max_rounds: int = MAX_ROUNDS, image_ids: list[int] | None = None):
        self.settings = settings if settings is not None else cfg.load_settings()
        self.tracer = AgentTracer(on_event)
        self.planner = make_planner(self.settings)
        self.tracer.planner = self.planner.name
        self.max_rounds = max_rounds
        self._n = 0
        self._task = ""
        self.artifacts: list[dict] = []
        self.answer = ""
        self.degraded = False
        self.degrade_reason = ""
        self.elapsed_ms = 0
                                               
                                         
        self.image_ids = list(dict.fromkeys(
            int(i) for i in (image_ids or []) if str(i).isdigit() and int(i) > 0))
        self._task_images: list[dict] = []
        self.task_dir: Path | None = None
                                         
                                                
        self._last: dict[str, T.ToolResult] = {}
        self._results: list[tuple[str, T.ToolResult]] = []

                                                                        
            
                                                                        
    def _e(self, kind: str, title: str, agent: str = "system", **kw) -> AgentEvent:
        return self.tracer.emit(kind, title, agent, **kw)

    def _delegate(self, agent: str, why: str, parent: int | None) -> AgentEvent:
        cn = {"mission": "巡检定线", "vision": "视觉检测", "quant": "分割量化",
              "trend": "趋势研判", "refly": "复飞决策",
              "report": "报告编制"}.get(agent, agent)
        return self._e("delegate", f"委派给「{cn}」", "orchestrator",
                       detail=why, data={"target": agent}, parent=parent)

    def _tool(self, name: str, args: dict, agent: str,
              parent: int | None) -> Iterator[AgentEvent]:
                               
        self._n += 1
        cid = _call_id(self._n)
        spec = T.TOOLS.get(name)
        cn = spec.cn if spec else name
                                                      
                                        
        def _fmt(v):
            if isinstance(v, float):
                return f"{v:.3g}"
            s = str(v)
            return s if len(s) <= 24 else s[:24] + "…"
        arg_txt = "、".join(f"{k}={_fmt(v)}" for k, v in args.items()
                           if v not in ("", None, [], {})) or "无参数"
        yield self._e("tool_call", f"{cn}（{arg_txt}）", agent,
                      detail=(spec.desc if spec else ""), data={"tool": name, **args},
                      call_id=cid, parent=parent)
        if name == "make_report":
                                                
                                                         
                                                         
                                         
            args = {**args, "trace": self.trace_summary()}
        res = T.call(name, **args)
        yield self._e("tool_result", res.summary or res.error, agent,
                      data={"tool": name, **res.data} if res.ok else {"tool": name},
                      level="ok" if res.ok else "error", duration_ms=res.ms,
                      call_id=cid, parent=parent,
                      detail="" if res.ok else res.error)
                          
        self._last[name] = res
        self._results.append((name, res))

    def _collect_visual_artifacts(self, tool: str, agent: str,
                                  parent: int | None) -> Iterator[AgentEvent]:
                                   

                                           
                                   
           
        res = self._last.get(tool)
        if not res or not res.ok:
            return
        kinds = {
            "detect_image": (("annotated", "检测标注图"),),
            "segment_defect": (("mask", "裂缝分割掩膜"),),
        }.get(tool, ())
        for key, kind in kinds:
            path = str(res.data.get(key) or "")
            if not path:
                continue
            self.artifacts.append({"kind": kind, "path": path})
            yield self._e("artifact", f"已生成{kind}：{path.rsplit('/', 1)[-1].rsplit(chr(92), 1)[-1]}",
                          agent, data={"path": path, "kind": kind}, level="ok", parent=parent)

    def _archive_file(self, path: str) -> str:
                                       
        src = Path(path) if path else None
        if src is None or not src.is_file() or self.task_dir is None:
            return ""
        dst = self.task_dir / src.name
        try:
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
            return str(dst)
        except OSError:
            return ""

    def _write_aggregate_csv(self, tool: str, agent: str,
                             parent: int | None) -> Iterator[AgentEvent]:
                                   
        if self.task_dir is None:
            return
        rows: list[dict] = []
        if tool == "detect_image":
            for name, res in self._results:
                if name != tool or not res.ok:
                    continue
                data = res.data
                for d in data.get("detections", []):
                    rows.append({
                        "影像文件": data.get("image", ""), "影像ID": data.get("image_id", ""),
                        "点位编号": data.get("point_id", ""), "巡检批次": data.get("batch", ""),
                        "病害类别": d.get("cls_name", ""), "置信度": round(float(d.get("conf") or 0), 3),
                        "X1": d.get("x1", ""), "Y1": d.get("y1", ""),
                        "X2": d.get("x2", ""), "Y2": d.get("y2", ""),
                        "来源": d.get("source") or data.get("source", ""),
                    })
            filename, kind = "病害检测汇总.csv", "检测数据汇总CSV"
        elif tool == "segment_defect":
            for name, res in self._results:
                if name != tool or not res.ok:
                    continue
                data = res.data
                image = db.get_image(int(data.get("image_id") or 0))
                for s in data.get("segments", []):
                    rows.append({
                        "影像文件": data.get("image", ""), "影像ID": data.get("image_id", ""),
                        "点位编号": image["point_id"] if image else "",
                        "巡检批次": image["batch"] if image else "",
                        "病害类别": s.get("cls_name", ""), "面积(cm²)": s.get("area_cm2", ""),
                        "裂缝长度(mm)": s.get("length_mm", ""), "平均宽度(mm)": s.get("avg_width_mm", ""),
                        "最大宽度(mm)": s.get("max_width_mm", ""), "面积占比": s.get("area_ratio", ""),
                        "GSD(mm/px)": s.get("gsd_mm_per_px", ""),
                        "量测不确定度(mm)": s.get("uncertainty_mm", ""), "置信度": s.get("conf", ""),
                    })
            filename, kind = "裂缝量化汇总.csv", "量化数据汇总CSV"
        else:
            return
        if not rows:
            return
        path = self.task_dir / filename
        T.report.export_csv(rows, path)
        self.artifacts.append({"kind": kind, "path": str(path)})
        yield self._e("artifact", f"已汇总 {len(rows)} 条记录：{filename}", agent,
                      data={"path": str(path), "kind": kind, "rows": len(rows)},
                      level="ok", parent=parent)

    def _finalize_task_archive(self) -> tuple[int, str, str]:
                                        

                                                     
                                                
           
        if self.task_dir is None:
            return 0, "", ""
        try:
            trace_path = self.task_dir / "智能体执行轨迹.jsonl"
            self.tracer.save_jsonl(trace_path)
            if not any(a.get("path") == str(trace_path) for a in self.artifacts):
                self.artifacts.append({"kind": "智能体执行轨迹", "path": str(trace_path)})
            files = sorted(p for p in self.task_dir.rglob("*") if p.is_file())
        except OSError:
            return 0, "", str(self.task_dir)

        names = "、".join(p.name for p in files[:5])
        if len(files) > 5:
            names += f" 等 {len(files)} 项"
        return len(files), names, str(self.task_dir)

    def trace_summary(self) -> dict:
                                         

                                                                   
                                                         
                                                   
                                                         

                                                  
                           
           
        steps: list[dict] = []
        for name, res in self._results:
            spec = T.TOOLS.get(name)
            agent = spec.agent if spec else "system"
            steps.append({
                "tool": name,
                "cn": spec.cn if spec else name,
                "agent": agent,
                "agent_cn": AGENTS.get(agent, (agent, "", ""))[0],
                "ok": bool(res.ok),
                "ms": int(res.ms or 0),
                "summary": (res.summary if res.ok else res.error or "")[:160],
            })

        delegates: list[dict] = []
        for ev in self.tracer.events:
            if ev.kind == "delegate":
                target = (ev.data or {}).get("target", "")
                delegates.append({
                    "agent": target,
                    "agent_cn": AGENTS.get(target, (target, "", ""))[0],
                    "reason": ev.detail or "",
                })

        if self.planner.name != "llm":
            planner_name = "本地规则引擎（未配置 API Key）"
        elif self.degraded:
            planner_name = (f"本地规则引擎（在线规划未完成，已降级续跑："
                            f"{self.degrade_reason or '模型未返回可用计划'}）")
        else:
            planner_name = f"{cfg.llm_provider_label(self.settings)}（在线）"

        return {
            "task": self._task,
            "planner": self.planner.name,
            "planner_name": planner_name,
            "degraded": self.degraded,
            "steps": steps,
            "delegates": delegates,
        }

                                                                        
         
                                                                        
    def stream(self, task: str) -> Iterator[AgentEvent]:
                           
        self._last = {}
        self._results = []
        self.artifacts = []
        self.answer = ""
        self.degraded = False
        self.degrade_reason = ""
        t0 = time.perf_counter()
        task = (task or "").strip()
        self._task = task

        yield self._e("run_start", f"收到任务：{task or '（空）'}", "system",
                      data={"task": task, "planner": self.planner.name},
                      detail=(f"规划来源：{cfg.llm_provider_label(self.settings)}（在线）"
                              if self.planner.name == "llm"
                              else "规划来源：本地规则引擎（未配置 API Key，"
                                   "全流程仍可完整运行）"))

        if not task:
            yield self._e("error", "任务为空，无法解析", "orchestrator", level="error")
            yield self._e("run_end", "任务终止", "system", level="error")
            return

                                           
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.task_dir = cfg.OUT_DIR / "tasks" / f"巡检任务_{stamp}"
        self.task_dir.mkdir(parents=True, exist_ok=True)

        slots = parse_slots(task)
        self._apply_image_scope(slots)
                                                
        yield self._e("thought", f"已解析请求：{slots.describe()}", "orchestrator",
                      data=slots.to_dict())

        if self._task_images:
            yield self._e(
                "decision",
                f"已锁定本次任务的 {len(self._task_images)} 张影像，"
                f"覆盖 {len({r['point_id'] for r in self._task_images if r['point_id']})} 个点位",
                "orchestrator", level="ok",
                data={"image_ids": [r["id"] for r in self._task_images],
                      "filenames": [r["filename"] for r in self._task_images]},
            )
        yield self._e("artifact", f"已创建本次任务归档目录：{self.task_dir.name}", "system",
                      data={"path": str(self.task_dir), "kind": "任务归档目录"}, level="ok")

        degraded = False
        if self.planner.name == "llm":
            try:
                ok = yield from self._llm_flow(task, slots)
            except Exception as exc:                                    
                ok = False
                self.degrade_reason = f"{type(exc).__name__}: {exc}"
            if not ok:
                degraded = True
                                                          
                                                     
                self.degraded = True
                yield self._e("warning",
                              f"在线规划未完成（{self.degrade_reason or '模型未返回可用计划'}），"
                              f"已自动切换到本地规则引擎续跑", "orchestrator",
                              level="warn", data={"reason": self.degrade_reason})
                                              
                yield from self._rule_flow(slots)
        else:
            yield from self._rule_flow(slots)

        answer = self._compose_answer(slots)
        ms = int((time.perf_counter() - t0) * 1000)
        yield self._e("decision", "已汇总结论", "orchestrator",
                      detail=answer[:200], data={"chars": len(answer)})
        yield self._e("run_end", f"任务完成，用时 {ms / 1000:.1f} s", "system",
                      data={"elapsed_ms": ms, "artifacts": self.artifacts,
                           "degraded": degraded},
                      level="ok" if not degraded else "warn",
                      duration_ms=ms)
        file_count, file_names, task_dir = self._finalize_task_archive()
        if task_dir:
            yield self._e(
                "artifact",
                f"本次检测 {len(self._task_images)} 张影像，生成 {file_count} 个文件",
                "system",
                detail=f"文件：{file_names or '任务归档资料'}；全部储存在：{task_dir}",
                data={"kind": "任务归档摘要", "path": task_dir,
                      "images": len(self._task_images), "file_count": file_count},
                level="ok",
            )
        self.answer = answer
        self.degraded = degraded
        self.elapsed_ms = ms

    def _apply_image_scope(self, slots: Slot) -> None:
                                        

                                           
                                              
                         
           
        self._task_images = []
        for iid in self.image_ids:
            row = db.get_image(iid)
            if row:
                self._task_images.append(dict(row))
        if not self._task_images:
            return
        if not slots.points:
            slots.points = list(dict.fromkeys(
                str(r.get("point_id") or "").upper() for r in self._task_images
                if r.get("point_id")))[:MAX_POINTS_PER_STEP]
        if not slots.batches:
            slots.batches = sorted({str(r.get("batch") or "").upper()
                                    for r in self._task_images if r.get("batch")})

    def run(self, task: str) -> AgentRun:
                                        
        events = list(self.stream(task))
        return AgentRun(task=task, planner=self.planner.name, answer=self.answer,
                        events=events, artifacts=self.artifacts,
                        degraded=self.degraded, degrade_reason=self.degrade_reason,
                        elapsed_ms=self.elapsed_ms)

                                                                        
          
                                                                        
    def _rule_flow(self, slots: Slot) -> Iterator[AgentEvent]:
                                            
        for want in slots.wants:
            if want == "import":
                yield from self._step_import(slots)
            elif want == "overview":
                yield from self._step_overview(slots)
            elif want in ("detect", "quantify"):
                yield from self._step_vision(slots, want)
            elif want == "trend":
                yield from self._step_trend(slots)
            elif want == "anomaly":
                yield from self._step_anomaly(slots)
            elif want == "grade":
                yield from self._step_grade(slots)
            elif want == "reflight":
                yield from self._step_reflight(slots)
            elif want == "report":
                yield from self._step_report(slots)

    def _step_import(self, slots: Slot) -> Iterator[AgentEvent]:
                                             
        d = self._delegate("mission", "先把新拍的影像读入库，后面每一步都从库里取数", None)
        yield d
        if self._task_images:
            yield self._e(
                "decision",
                f"本次任务影像已入库并完成关联：{len(self._task_images)} 张",
                "mission", parent=d.seq, level="ok",
                data={"images": [{"image_id": r["id"], "filename": r["filename"],
                                  "point_id": r.get("point_id", ""),
                                  "batch": r.get("batch", "")}
                                 for r in self._task_images]},
            )
            return
        yield self._e("thought",
                      "影像没有入库，检测与量化就无从谈起——「图像导入」是采集与"
                      "分析之间那一步。入库走的是与桌面「智能体工作台 → 导入影像」、网页上传"
                      "完全相同的一段代码，同一张图在三个入口下落成同一条记录。",
                      "mission", parent=d.seq)
        yield from self._tool("import_images", {}, "mission", d.seq)
        r = self._last.get("import_images")
        if r and r.ok:
            added = r.data.get("images") or []
            if added:
                yield self._e("decision",
                              f"新入库 {len(added)} 张，覆盖点位 "
                              + "、".join(sorted({i["point_id"] for i in added})),
                              "mission", parent=d.seq, level="ok",
                              data={"images": added})
            else:
                                                
                                              
                                
                yield self._e("warning",
                              r.summary + "（已在库的影像按原路径跳过，不重复建行）",
                              "mission", parent=d.seq, level="warn",
                              data={"skipped": r.data.get("skipped", 0)})

    def _step_overview(self, slots: Slot) -> Iterator[AgentEvent]:
        d = self._delegate("mission", "先摸清库内数据边界，再决定取数范围", None)
        yield d
        yield self._e("thought",
                      "巡检范围解析需要先知道库里有哪些点位、覆盖几个批次，"
                      "否则后面的查询可能是空的。", "mission", parent=d.seq)
        yield from self._tool("db_overview", {}, "mission", d.seq)
        pts = slots.points[:MAX_POINTS_PER_STEP]
        if pts:
            yield from self._tool("list_points",
                                  {"component": slots.components[0]} if slots.components
                                  else {}, "mission", d.seq)

    def _step_vision(self, slots: Slot, want: str) -> Iterator[AgentEvent]:
        agent = "vision" if want == "detect" else "quant"
        cn = "识别七类病害" if want == "detect" else "做像素级分割并换算实际尺寸"
                                              
                                      
        targets = self._task_images[:MAX_POINTS_PER_STEP]
        pts = slots.points[:MAX_POINTS_PER_STEP]
        if targets:
            d = self._delegate(agent, f"对本次任务 {len(targets)} 张影像{cn}", None)
            yield d
            yield self._e("thought", "任务范围已锁定，逐张处理已关联影像。",
                          agent, parent=d.seq)
            tool_name = "detect_image" if want == "detect" else "segment_defect"
            for image in targets:
                yield from self._tool(tool_name, {"image_id": image["id"],
                                                  "output_dir": str(self.task_dir or "")},
                                      agent, d.seq)
                yield from self._collect_visual_artifacts(tool_name, agent, d.seq)
            yield from self._write_aggregate_csv(tool_name, agent, d.seq)
            return
        if not pts:
                                            
            d0 = self._delegate("trend", "未指定点位，先筛出需要重点看的点位", None)
            yield d0
            yield from self._tool("find_anomalies", {}, "trend", d0.seq)
            anom = (self._last.get("find_anomalies").data.get("anomalies", [])
                    if self._last.get("find_anomalies") else [])
            pts = [a["point"] for a in anom][:MAX_POINTS_PER_STEP]
            if not pts:
                yield self._e("warning", "库内没有异常点位，跳过检测环节",
                              "orchestrator", level="warn")
                return
        d = self._delegate(agent, f"对 {len(pts)} 个点位{cn}", None)
        yield d
        yield self._e("thought",
                      f"检测必须由算法给出可复现的结果，不能由模型描述影像内容；"
                      f"因此这一环节全部走确定性代码。逐个处理 {'、'.join(pts)}。",
                      agent, parent=d.seq)
        for p in pts:
            tools = (["detect_image"] if want == "detect"
                     else ["segment_defect"])
            for tn in tools:
                yield from self._tool(tn, {"point_id": p,
                                           "output_dir": str(self.task_dir or "")},
                                      agent, d.seq)
                yield from self._collect_visual_artifacts(tn, agent, d.seq)
        yield from self._write_aggregate_csv("detect_image" if want == "detect"
                                             else "segment_defect", agent, d.seq)

    def _step_trend(self, slots: Slot) -> Iterator[AgentEvent]:
        pts = slots.points[:MAX_POINTS_PER_STEP]
        if not pts:
            yield from self._step_anomaly(slots)
            return
        d = self._delegate("trend", f"对 {len(pts)} 个点位做跨批次趋势比对", None)
        yield d
        yield self._e("thought",
                      "趋势必须按批次先聚合再比首末期：同一批次内同一类别可能有多处检出，"
                      "直接取首末两条记录容易落到同一批次上，算出无意义的增幅。",
                      "trend", parent=d.seq)

                                  
                                                 
                                                 
                                               
                                      
        yield from self._tool("query_timeseries", {}, "trend", d.seq)
        rows = (self._last["query_timeseries"].data.get("rows", [])
                if self._last.get("query_timeseries") else [])
        have: dict[str, dict[str, float]] = {}
        history_batches: dict[str, set[str]] = {}
        for r in rows:
            have.setdefault(r["point_id"], {})[r["cls_key"]] = r["area_cm2"]
            history_batches.setdefault(r["point_id"], set()).add(str(r.get("batch") or ""))

        want = slots.classes[0] if slots.classes else ""
        skipped: list[str] = []
        for p in pts:
            avail = have.get(p)
                                                                            
                                                                           
                                                                             
                                                                          
            if not avail or len(history_batches.get(p, set()) - {""}) < 2:
                skipped.append(p)
                continue
            if want and want in avail:
                cls = want
            else:
                cls = max(avail, key=lambda k: avail[k])
                if want and cls != want and want in cfg.DISEASE_BY_KEY:
                    yield self._e(
                        "decision",
                        f"{p} 库内无「{cfg.DISEASE_BY_KEY[want].name}」记录，"
                        f"改按该点位主病害「{cfg.DISEASE_BY_KEY[cls].name}」比对",
                        "trend", parent=d.seq)
            yield from self._tool("analyze_trend", {"point_id": p, "cls_key": cls},
                                  "trend", d.seq)
        if skipped:
            yield self._e("decision",
                          f"{len(skipped)} 个点位缺少至少两期量化记录，已跳过"
                          f"（{'、'.join(skipped[:6])}"
                          f"{'…' if len(skipped) > 6 else ''}）",
                          "trend", parent=d.seq, data={"skipped": skipped})

    def _step_anomaly(self, slots: Slot) -> Iterator[AgentEvent]:
        d = self._delegate("trend", "全库扫描增幅超阈值的点位", None)
        yield d
        yield self._e("thought",
                      "增幅阈值取 30%：低于此值的年际波动可能只是量测噪声，"
                      "而 2·GSD 的量测不确定度本身就在这个量级附近。",
                      "trend", parent=d.seq)
        yield from self._tool("find_anomalies", {}, "trend", d.seq)

    def _step_grade(self, slots: Slot) -> Iterator[AgentEvent]:
        d = self._delegate("trend", "按现行规范条文给出处置等级", None)
        yield d
        yield self._e("thought",
                      "定级有两条彼此独立的判据：实测值是否超限、发展是否过快。"
                      "一条静止的超限裂缝也必须处置，一处尚小但快速发展的病害也要提前介入，"
                      "因此两者分别判定，命中最严的一条。", "trend", parent=d.seq)
        trends = [(n, r) for n, r in self._results if n == "analyze_trend" and r.ok]
        if trends:
            for _, r in trends[:MAX_POINTS_PER_STEP]:
                t = r.data["trend"]
                yield from self._tool("grade_defect",
                                      {"cls_key": t["cls"], "width_mm": t["width"],
                                       "growth": t["growth"],
                                       "component": t["point"][:1]},
                                      "trend", d.seq)
        else:
                                  
            anom = (self._last.get("find_anomalies").data.get("anomalies", [])
                    if self._last.get("find_anomalies") else [])
            if not anom:
                yield self._e("warning", "无可定级的对象：既没有趋势结果也没有异常点位",
                              "trend", level="warn", parent=d.seq)
                return
            for a in anom[:MAX_POINTS_PER_STEP]:
                yield from self._tool("grade_defect",
                                      {"cls_key": a["cls"], "width_mm": a["width"],
                                       "growth": a["growth"],
                                       "component": a["point"][:1]},
                                      "trend", d.seq)

    def _step_reflight(self, slots: Slot) -> Iterator[AgentEvent]:
        d = self._delegate("refly",
                                 "审计影像采集质量，判断哪些点位的量测值本身不可信",
                                 None)
        yield d
        yield self._e("thought",
                      "先判断「这个数准不准」，再谈它超没超限。裂缝宽度的量测不确定度是 "
                      "2·GSD，若它超过规范限值的三分之一，超限与否在统计上就不可判定，"
                      "此时给出的加固建议是建立在不可信的读数上的。",
                      "refly", parent=d.seq)
        args: dict = {}
        if slots.points:
            args["points"] = slots.points[:MAX_POINTS_PER_STEP]
        if slots.batches:
            args["batches"] = slots.batches
        yield from self._tool("plan_reflight", args, "refly", d.seq)
        r = self._last.get("plan_reflight")
        if r and r.ok and r.data.get("waypoints"):
            for w in r.data["waypoints"]:
                yield self._e(
                    "decision",
                    f"{w['point_id']} → 拍摄距离 {w['shoot_distance']:.2f} m，"
                    f"变焦 {w['zoom']:.2f}×，预期 {w['expected_px_width']:.0f} 像素宽",
                    "refly", detail=w["note"], parent=d.seq,
                    data={"point_id": w["point_id"], "trigger": w["trigger_code"],
                          "gsd": w["expected_gsd_mm_per_px"]})
            csv_path = self._archive_file(r.data.get("csv", ""))
            json_path = self._archive_file(r.data.get("json", ""))
            if csv_path:
                self.artifacts.append({"kind": "复飞航点CSV", "path": csv_path})
            if json_path:
                self.artifacts.append({"kind": "复飞航点JSON", "path": json_path})
            yield self._e("artifact", f"已导出 {len(r.data['waypoints'])} 个复飞航点",
                          "refly", data={"csv": csv_path, "json": json_path},
                          level="ok", parent=d.seq)
            cites = r.data.get("citations") or []
            if cites:
                yield self._e("decision",
                              "判据依据：" + "；".join(
                                  f"{c['citation']}（{c['title']}）"
                                  for c in cites[:3]),
                              "refly",
                              detail="条文为示意性整理，以规范原文为准",
                              parent=d.seq)

    def _step_report(self, slots: Slot) -> Iterator[AgentEvent]:
        d = self._delegate("report", "把前面各环节的结果装配成完整报告", None)
        yield d
        yield self._e("thought",
                      "报告章节顺序固定（数据来源→检测统计→长周期趋势→异常点位→"
                      "智能研判→说明），这样不同批次的报告可以逐章对照；"
                      "只有第五章的措辞由模型润色，其余章节的数字全部来自数据库。",
                      "report", parent=d.seq)
        text = self._judgement_text()
        yield from self._tool("make_report", {"llm_text": text}, "report", d.seq)
        r = self._last.get("make_report")
        if r and r.ok:
            md_path = self._archive_file(r.data.get("markdown", ""))
            html_path = self._archive_file(r.data.get("html", ""))
            if md_path:
                self.artifacts.append({"kind": "巡检报告Markdown", "path": md_path})
            if html_path:
                self.artifacts.append({"kind": "巡检报告HTML", "path": html_path})
            yield self._e("artifact", "报告已生成（Markdown / HTML）", "report",
                          data={"markdown": md_path, "html": html_path},
                          level="ok", parent=d.seq)

                                                                        
          
                                                                        
    def _llm_flow(self, task: str, slots: Slot) -> Iterator[AgentEvent]:
                                                   
        planner: LLMPlanner = self.planner
        messages = planner.seed(task, slots)
        pending: list[dict] = []                            

        for rnd in range(1, self.max_rounds + 1):
            res = planner.turn(messages)
            if not res.get("ok"):
                self.degrade_reason = res.get("error") or "模型调用失败"
                return False
            msg = res.get("message") or {}
            content = (msg.get("content") or "").strip()
            calls = msg.get("tool_calls") or []

            if content and not calls:
                yield self._e("thought", content[:400], "orchestrator")

            if not calls:
                plan = LLMPlanner.parse_text_plan(content)
                if plan:
                    pending = [s for s in plan.get("steps", [])
                               if isinstance(s, dict) and s.get("tool")]
                    if plan.get("thoughts"):
                        yield self._e("thought", str(plan["thoughts"])[:400],
                                      "orchestrator",
                                      detail="模型未发起工具调用，改以 JSON 计划形式返回")
                    if not pending:
                        self.answer = content
                        return True
                    break                                            
                              
                if content:
                    yield self._e("thought",
                                  "模型未调用工具，直接给出结论；本系统中数值均须由工具产出，"
                                  "此处结论仅作为措辞参考。", "orchestrator", level="warn")
                    self.answer = content
                    return True
                self.degrade_reason = "模型既未调用工具也未返回内容"
                return False

            messages.append({"role": "assistant", "content": content or "",
                             "tool_calls": calls})

            for tc in calls:
                fn = (tc.get("function") or {})
                name = fn.get("name") or ""
                try:
                    args = json_loads(fn.get("arguments") or "{}")
                except ValueError:
                    args = {}
                spec = T.TOOLS.get(name)
                if spec is None:
                    yield self._e("warning", f"模型请求了未注册的工具：{name}",
                                  "orchestrator", level="warn")
                    messages.append({"role": "tool", "tool_call_id": tc.get("id", ""),
                                     "content": json_dumps({"error": "未注册的工具"})})
                    continue
                d = self._delegate(spec.agent, f"模型判定需要「{spec.cn}」", None)
                yield d
                gen = self._tool(name, args if isinstance(args, dict) else {},
                                 spec.agent, d.seq)
                last = None
                for ev in gen:
                    last = ev
                    yield ev
                payload = (last.data if last and last.kind == "tool_result" else {})
                payload.pop("tool", None)
                messages.append({"role": "tool", "tool_call_id": tc.get("id", ""),
                                 "content": json_dumps(payload)[:6000]})

                                         
        for step in pending:
            name = step.get("tool")
            spec = T.TOOLS.get(name)
            if spec is None:
                continue
            d = self._delegate(spec.agent, f"按模型给出的 JSON 计划执行「{spec.cn}」",
                                     None)
            yield d
            yield from self._tool(name, step.get("args") or {}, spec.agent, d.seq)
        return True

                                                                        
          
                                                                        
    def _judgement_text(self) -> str:
                                          

                                              
                       
           
        lines: list[str] = []
        for name, r in self._results:
            if name == "analyze_trend" and r.ok:
                t = r.data["trend"]
                lines.append(f"{t['point']}（{t['component']}）{t['cls_name']}："
                             f"面积 {t['area0']:.1f}→{t['area1']:.1f} cm²，"
                             f"增幅 {t['growth'] * 100:+.1f}%，"
                             f"最新宽度 {t['width']:.2f} mm。")
        if not lines:
            for name, r in self._results:
                if name == "find_anomalies" and r.ok:
                    for a in r.data.get("anomalies", [])[:8]:
                        lines.append(f"{a['point']}（{a['component']}）{a['cls_name']}："
                                     f"增幅 {a['growth'] * 100:+.1f}%，"
                                     f"判为{a['level']}。")
        return "\n".join(lines)

    def _compose_answer(self, slots: Slot) -> str:
                                           
        parts: list[str] = []
        g = self._last.get

                   
        trends = [r for n, r in self._results if n == "analyze_trend" and r.ok]
        anom = (g("find_anomalies").data.get("anomalies", [])
                if g("find_anomalies") and g("find_anomalies").ok else [])
        grades = [r for n, r in self._results if n == "grade_defect" and r.ok]
        hard = [r for r in grades if r.data.get("grade") == "加固"]

        if hard:
                                                  
                                                  
            names = "、".join(
                f"{r.data['cls_name']}（{r.data['limit_mm']:g} mm 限值）"
                if r.data.get("limit_mm") is not None else r.data["cls_name"]
                for r in hard[:3])
            parts.append(f"结论：有 {len(hard)} 处病害达到「加固」等级，涉及 {names}，"
                         f"建议安排专项检测并编制加固方案。")
        elif grades:
            parts.append(f"结论：共 {len(grades)} 处病害完成定级，"
                         f"最高等级为「{grades[0].data.get('grade')}」。")
        elif anom:
            parts.append(f"结论：筛出 {len(anom)} 处病害发展异常，"
                         f"最突出的是 {anom[0]['point']}"
                         f"（{anom[0]['component']}）{anom[0]['cls_name']}，"
                         f"增幅 {anom[0]['growth'] * 100:+.0f}%。")
        elif trends:
            parts.append(f"结论：完成 {len(trends)} 个点位的趋势比对。")
        else:
            parts.append("结论：本次任务未产生需要处置的病害结论。")

                    
        if trends:
            parts.append("\n数据依据：")
            for r in trends[:6]:
                t = r.data["trend"]
                parts.append(f"· {t['point']}（{t['component']}）{t['cls_name']}："
                             f"{t['area0']:.1f} → {t['area1']:.1f} cm²"
                             f"（{t['growth'] * 100:+.1f}%），最大宽度 {t['width']:.2f} mm")

                    
        if grades:
            parts.append("\n处置建议：")
            seen: set[tuple] = set()
            for r in grades[:6]:
                key = (r.data["cls_name"], r.data["grade"])
                if key in seen:
                    continue
                seen.add(key)
                parts.append(f"· {r.data['cls_name']} → 「{r.data['grade']}」："
                             f"{r.data['reason']}")

                    
        cites: list[str] = []
        for r in grades:
            for c in r.data.get("clauses", [])[:1]:
                if c["citation"] not in cites:
                    cites.append(c["citation"])
        if cites:
            parts.append("\n规范依据：" + "、".join(cites[:4])
                         + "（条文为示意性整理，以规范原文为准）")

                    
        rf = g("plan_reflight")
        if rf and rf.ok and rf.data.get("waypoints"):
            wps = rf.data["waypoints"]
            parts.append(f"\n采集质量：审计发现 {len(rf.data['issues'])} 项问题，"
                         f"其中 {len(wps)} 个点位需复飞。")
            for w in wps[:5]:
                parts.append(f"· {w['point_id']}：{w['trigger_desc']} → "
                             f"拍摄距离 {w['shoot_distance']:.2f} m、"
                             f"变焦 {w['zoom']:.2f}×、预期 {w['expected_px_width']:.0f} 像素宽")
        elif rf and rf.ok:
            parts.append("\n采集质量：审计未发现需要复飞的点位，"
                         "现有影像满足量测精度要求。")

                  
        if self.artifacts:
            parts.append("\n产出文件：")
            for a in self.artifacts:
                if a.get("path"):
                    parts.append(f"· {a['kind']}：{a['path']}")

        if self.planner.name != "llm":
            parts.append("\n（本次未调用大模型 API，以上结论由本地确定性规则引擎产出，"
                         "数值均来自数据库实测记录。）")
        return "\n".join(parts)


def json_loads(s: str):
                                              
    try:
        return json.loads(s)
    except (ValueError, TypeError):
        cleaned = (s or "").strip().rstrip(",")
        return json.loads(cleaned) if cleaned else {}


def json_dumps(o) -> str:
    return json.dumps(o, ensure_ascii=False, default=str)


def run_task(task: str, settings: dict | None = None) -> AgentRun:
                     
    return Orchestrator(settings).run(task)
