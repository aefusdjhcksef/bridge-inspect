                     

                   

                                         
                                       
                                          
                                 

                                      
                                       
          

                  

                                            
                                                        
                                          
                             

            

                                          
                                                   
                                    
   

from __future__ import annotations

from dataclasses import dataclass

                              
DISCLAIMER = "示意文本，以规范原文为准"

RAIL = "《铁路桥隧建筑物修理规则》"
HIGHWAY = "《公路桥梁技术状况评定标准》JTG/T H21"
PRACTICE = "无人机桥梁巡检作业通行做法"


@dataclass(frozen=True)
class Clause:
    cid: str                                    
    source: str                                
    code: str                                  
    title: str
    text: str                                          
    cls_keys: tuple[str, ...] = ()                       
    components: tuple[str, ...] = ()                     
    limit_mm: float | None = None
    action: str = "观察"                                
    keywords: tuple[str, ...] = ()

    @property
    def citation(self) -> str:
        return f"{self.source}{self.code}"

    def to_dict(self) -> dict:
        return {
            "cid": self.cid, "source": self.source, "code": self.code,
            "title": self.title, "text": self.text, "citation": self.citation,
            "limit_mm": self.limit_mm, "action": self.action,
            "disclaimer": DISCLAIMER,
        }


CLAUSES: tuple[Clause, ...] = (
                                                                        
    Clause("CR-01", RAIL, "第3.2.1条", "裂缝超限处置",
           "钢筋混凝土构件裂缝宽度超过限值时，应查明原因，采用灌注、封闭或加固处理。",
           ("crack",), limit_mm=0.30, action="加固"),
    Clause("CR-02", RAIL, "第3.2.2条", "裂缝接近限值",
           "裂缝宽度已达到限值八成以上或持续发展者，应缩短检查周期并作专项观测。",
           ("crack",), limit_mm=0.24, action="维修", keywords=("发展", "扩展")),
    Clause("CR-03", RAIL, "第3.2.5条", "裂缝观测记录",
           "裂缝观测应记录长度、宽度、走向与所在部位，并附有比例尺的影像资料。",
           ("crack",), action="观察"),
    Clause("CR-04", PRACTICE, "第20条", "量测影像的分辨率要求",
           "用于裂缝宽度量测的影像，其地面分辨率不应低于所需量测精度的 1/3，"
           "否则量测结果不具备判定超限与否的统计意义。",
           ("crack",), action="维修", keywords=("分辨率", "GSD", "精度", "量测")),
                                                                      
    Clause("SP-01", RAIL, "第3.3.2条", "剥落修补",
           "混凝土剥落掉块应及时凿除松散层、清理至密实基面后修补，防止钢筋进一步外露。",
           ("spalling",), action="维修"),
    Clause("SP-02", RAIL, "第3.3.4条", "剥落面积较大",
           "剥落面积大于 0.5 m² 或深度超过保护层厚度时，应编制专项修补方案。",
           ("spalling",), action="加固", keywords=("面积", "深度")),
                                                                        
    Clause("EB-01", RAIL, "第3.4.1条", "露筋除锈阻锈",
           "钢筋外露、锈蚀应除锈并涂阻锈剂后，用高强砂浆或聚合物砂浆恢复保护层。",
           ("exposed_bar",), action="维修"),
    Clause("EB-02", RAIL, "第3.4.3条", "主筋截面损失",
           "主筋外露且截面损失率大于 5% 时，应进行承载力验算并加固。",
           ("exposed_bar",), action="加固", keywords=("截面", "损失", "承载力")),
                                                                      
    Clause("SW-01", RAIL, "第3.5.1条", "渗水先治水",
           "渗水、泛碱应排查防水层破损与排水通道堵塞，先治水后治面。",
           ("seepage",), action="维修"),
    Clause("SW-02", RAIL, "第3.5.3条", "析出物清理",
           "析出物应清理并观察是否复现；伴随裂缝的渗水按裂缝条款处理。",
           ("seepage",), action="观察", keywords=("泛碱", "析出")),
                                                                      
    Clause("HC-01", RAIL, "第3.6.2条", "蜂窝麻面封闭",
           "蜂窝麻面等外观缺陷应作表面封闭处理，面积较大者采用聚合物砂浆修补。",
           ("honeycomb",), action="观察"),
                                                                      
    Clause("BR-01", RAIL, "第4.2.1条", "支座检查项",
           "支座应检查位移、转角、脱空、剪切变形与钢材锈蚀，并复测支座位移量。",
           ("bearing",), ("C",), action="观察"),
    Clause("BR-02", RAIL, "第4.2.3条", "支座位移超限",
           "支座位移量超过设计允许值或出现明显脱空时，应顶升复位或更换支座。",
           ("bearing",), ("C",), action="加固", keywords=("位移", "脱空", "滑移")),
                                                                     
    Clause("JT-01", RAIL, "第4.3.2条", "伸缩装置维护",
           "伸缩装置应保持缝内清洁、伸缩自由，错台量与缝宽应定期量测记录。",
           ("joint_offset",), ("F",), action="观察"),
    Clause("JT-02", RAIL, "第4.3.4条", "错台超限处置",
           "伸缩缝错台量超过 5 mm 或影响行车平顺时，应清理杂物并调整伸缩装置。",
           ("joint_offset",), ("F",), limit_mm=5.0, action="维修",
           keywords=("错台", "平顺")),
                                                                    
    Clause("GN-01", HIGHWAY, "第5.1条", "技术状况评定",
           "按构件缺损的类型、程度与发展状况评定技术状况等级。", (), (), action="观察"),
    Clause("GN-02", HIGHWAY, "第5.3条", "缺损评分维度",
           "裂缝、剥落等缺损按「程度」与「发展」两个维度分别评分，两者独立不叠加。",
           ("crack", "spalling"), (), action="观察", keywords=("程度", "发展", "定级")),
    Clause("GN-03", HIGHWAY, "第4.2条", "检查分类与周期",
           "桥梁检查分为经常检查、定期检查与特殊检查，定期检查周期不超过 3 年。",
           (), (), action="观察", keywords=("周期", "定期检查")),
    Clause("GN-04", RAIL, "第2.1.4条", "检查记录要求",
           "检查记录应包含病害位置、尺寸、数量及影像资料，按同一基准比对历次记录。",
           (), (), action="观察", keywords=("记录", "基准", "比对")),
    Clause("GN-05", PRACTICE, "第19条", "同视场复拍条件",
           "同一航点复拍应保持相同站位与云台姿态，图像重叠率不低于 85%，"
           "以保证历次影像具备可比性。",
           (), (), limit_mm=0.85, action="维修",
           keywords=("重合率", "复拍", "同视场", "重叠率")),
)

CLAUSE_BY_ID = {c.cid: c for c in CLAUSES}

                              
_SYNONYMS: dict[str, tuple[str, ...]] = {
    "crack": ("裂缝", "裂纹", "开裂", "龟裂"),
    "spalling": ("剥落", "掉块", "空鼓", "脱落"),
    "exposed_bar": ("露筋", "钢筋外露", "锈蚀", "锈胀"),
    "seepage": ("渗水", "泛碱", "湿渍", "析出", "漏水"),
    "honeycomb": ("蜂窝", "麻面", "外观缺陷"),
    "bearing": ("支座", "滑移", "位移", "脱空"),
    "joint_offset": ("错台", "伸缩缝", "伸缩装置", "接缝"),
}


def expand_keywords(terms: list[str] | tuple[str, ...]) -> list[str]:
                            
    out: list[str] = []
    for t in terms:
        t = (t or "").strip()
        if not t:
            continue
        out.append(t)
        for _key, words in _SYNONYMS.items():
            if t in words or t == _key:
                out.extend(words)
                out.append(_key)
             
    seen: set[str] = set()
    uniq = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def search(classes: list[str] | tuple[str, ...] = (),
           components: list[str] | tuple[str, ...] = (),
           top_k: int = 3,
           extra_kw: list[str] | tuple[str, ...] = (),
           strict_component: bool = True) -> list[Clause]:
                                         

                                              
                                            
                              

                                        

                                               
                                               
                                                  
                                                 
                                               
                                              
                                     
                                            
       
    cls_set = {c for c in classes if c}
    comp_set = {(c or "").upper() for c in components if c}
    words = expand_keywords(list(extra_kw))

    scored: list[tuple[float, Clause]] = []
    for c in CLAUSES:
        score = 0.0
        if c.cls_keys:
            hit = cls_set & set(c.cls_keys)
            if not hit:
                                                   
                                           
                                              
                continue
            score += 3.0 * len(hit)
        else:
            score += 0.5
        if c.components:
            hit = comp_set & set(c.components)
            if not hit:
                if strict_component:
                    continue
                                             
            else:
                score += 2.0 * len(hit)
        elif comp_set:
            score += 0.2
        if words:
            hay = f"{c.title}{c.text}{c.code}{' '.join(c.keywords)}"
            score += sum(1.0 for w in words if w and w in hay)
        scored.append((score, c))

                        
                                      
                                         
                                            
                                           
                                                    
                                
                                            
    scored.sort(key=lambda sc: (-sc[0], -(sc[1].limit_mm or 0.0),
                                len(sc[1].cls_keys) or 99, sc[1].cid))
    return [c for _, c in scored[:max(1, top_k)]]


def for_disease(cls_key: str, component: str = "", top_k: int = 3) -> list[Clause]:
                             

                                             
                                              
                                                
                                                 
                                        
       
    return search([cls_key], [component] if component else [], top_k=top_k,
                  strict_component=False)


def limit_of(cls_key: str) -> float | None:
                                                                  
    for c in CLAUSES:
        if cls_key in c.cls_keys and c.limit_mm is not None:
            return c.limit_mm
    return None
