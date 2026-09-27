               

                                                
                                           

                                                         
                            
   

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from .. import config as cfg
from ..core import backend, segment


class AppContext(QObject):
                 

    backendChanged = pyqtSignal()                           
    notified = pyqtSignal(str, str)                       
    currentChanged = pyqtSignal()                  
    navigate = pyqtSignal(str)                             

    def __init__(self, user: dict, parent: QObject | None = None):
        super().__init__(parent)
        self.user = dict(user or {})
        self.settings: dict = cfg.load_settings()
        self._detector: backend.DetectBackend | None = None
        self._segmenter: segment.SegmentBackend | None = None
                                                                                  
        self.current: dict = {}
                                                  
                                              
        self.agent_task: str = ""

    def open_agent(self, task: str = "") -> None:
                                     
        self.agent_task = task or ""
        self.navigate.emit("agent")

                                                                        
    @property
    def detector(self) -> backend.DetectBackend:
        if self._detector is None:
            self._detector = backend.make_detector(self.settings)
        return self._detector

    @property
    def segmenter(self) -> segment.SegmentBackend:
        if self._segmenter is None:
            self._segmenter = segment.make_segmenter(self.settings)
        return self._segmenter

    def reload_backends(self) -> None:
                                     
        self._detector = None
        self._segmenter = None
        self.backendChanged.emit()

                                                                        
    def apply_settings(self, new: dict, notify: bool = True) -> None:
        self.settings.update(new)
        cfg.save_settings(self.settings)
        self.reload_backends()
        if notify:
            self.toast("设置已保存", "ok")

                                                                      
    def set_current(self, bgr, path: str = "", meta: dict | None = None,
                    image_id: int | None = None) -> None:
        self.current = {"bgr": bgr, "path": path, "meta": meta or {},
                        "image_id": image_id}
        self.currentChanged.emit()

    def clear_current(self) -> None:
        self.current = {}
        self.currentChanged.emit()

    @property
    def bgr(self):
        return self.current.get("bgr")

                                                                        
    def toast(self, text: str, kind: str = "info") -> None:
        self.notified.emit(text, kind)

                                                                    
    def backend_label(self) -> tuple[str, bool]:
                                 
        d = self.detector
        if d.mode == "demo":
                                               
                                         
            return "演示后端", True
        if isinstance(d, backend.CrackUNetDetector):
            return "crack-seg U-Net v3 · 裂缝区域定位", False
        if isinstance(d, backend.YoloDetector):
            return d.name, False
                                             
                                         
        from ..core import metrics

        return f"{metrics.DET_MODEL} · {d.name}", False
