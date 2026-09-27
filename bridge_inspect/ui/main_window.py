                           

                                                      
                       
   

from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QStackedWidget, QStatusBar, QWidget,
)

from .. import config as cfg
from .context import AppContext
from .hud import HudRoot
from .pages import AgentPage, DetectPage, HistoryPage, SegmentPage, SettingsPage, TrendPage
from .widgets import Sidebar, Toast


class MainWindow(QMainWindow):
    def __init__(self, user: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = AppContext(user, self)
        self.logged_out = False
        self._syncing = False

        self.setObjectName("AppRoot")
        self.setWindowTitle(f"{cfg.APP_NAME} · {cfg.APP_TITLE}")
        self.resize(1440, 902)
        self.setMinimumSize(1180, 760)

                                               
                                                                
        central = HudRoot()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar(user)
        self.sidebar.navChanged.connect(self.goto)
        self.sidebar.logoutClicked.connect(self.logout)
        root.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)

                                             
                                 
        self.pages = [AgentPage(self.ctx), DetectPage(self.ctx), SegmentPage(self.ctx),
                      HistoryPage(self.ctx), TrendPage(self.ctx), SettingsPage(self.ctx)]
        for p in self.pages:
            self.stack.addWidget(p)

        self._build_status()
        self.ctx.notified.connect(self.toast.show_message)
        self.ctx.navigate.connect(self.goto_key)
        self.goto(0)


                                                                        
    def _build_status(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)

        self.lbl_task = QLabel("就绪")
        self.lbl_backend = QLabel("")
        self.lbl_db = QLabel("")
        for w in (self.lbl_task, self.lbl_backend):
            w.setObjectName("Hint")
        self.lbl_db.setObjectName("Hint")

        sb.addWidget(self.lbl_task, 1)
        sb.addPermanentWidget(self.lbl_backend)
        sb.addPermanentWidget(self.lbl_db)
        self.toast = Toast(self)
        self._refresh_status()

    def _refresh_status(self) -> None:
        from .. import theme

        name, demo = self.ctx.backend_label()
        self.lbl_backend.setText(f"检测后端：{name}")
        self.lbl_backend.setStyleSheet(
            f"color: {theme.C['warn'] if demo else theme.C['ok']};")
        self.lbl_db.setText(f"数据库：{cfg.DB_PATH.name}")

                                                                        
    def goto(self, index: int) -> None:
        if not (0 <= index < len(self.pages)):
            return
        self.stack.setCurrentIndex(index)
        page = self.pages[index]
                                            
                          
        if not self._syncing:
            self._syncing = True
            btn = self.sidebar.group.button(index)
            if btn and not btn.isChecked():
                btn.setChecked(True)
            self._syncing = False
        if hasattr(page, "on_show"):
            page.on_show()
                                                 
                                           
                    

    def goto_key(self, key: str) -> None:
                                           
                                
        for i, p in enumerate(self.pages):
            if getattr(p, "key", "") == key:
                self.goto(i)
                return

    def logout(self) -> None:
                                    
        self.logged_out = True
        self.close()
