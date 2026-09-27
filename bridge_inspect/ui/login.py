             

                                              
                       

                                      
                                                  
   

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QRadialGradient
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QStyle, QStyleOption, QStylePainter,
    QVBoxLayout, QWidget,
)

from .. import config as cfg
from .. import db, theme
from . import hud, icons
from .widgets import IconBadge, Toast

C = theme.C

                                                           
                                
WIN_W, WIN_H = 980, 600
HERO_W = 440
                                                 
                               
WIN_SMALL = (880, 520)

                                                              
                         
                                               
                                                      
POINTS = [
    ("crack", "七类病害识别"),
    ("segment", "像素级尺寸换算"),
    ("trend", "跨批次趋势比对"),
    ("reflight", "采集质量审计与自主复飞"),
]


class HeroArt(QWidget):
                   

                                                 
                                                            

                                                            
                                                          
                                                  
                                                  
                                                           
                                   
       

    def __init__(self, width: int = 376, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._svg: QSvgRenderer | None = None
        self._vb = QSize(560, 300)                                   
        self._load(cfg.HERO_SVG)
        self.setFixedHeight(self.height_for_width(width))

    def _load(self, path) -> None:
                

                                                                         
                                                                   
                                                  
                                

                                                           
                     
           
        f = Path(path)
        if not f.exists():                                         
            return                                        
        r = QSvgRenderer(str(f), self)
        if not r.isValid():
            return
        self._svg = r
        if not r.defaultSize().isEmpty():
            self._vb = r.defaultSize()

    def height_for_width(self, width: int) -> int:
                                                             
        w = self._vb.width() or 1
        return max(90, int(round(width * self._vb.height() / float(w))))

    def resizeEvent(self, ev) -> None:                                  
        super().resizeEvent(ev)
        want = self.height_for_width(self.width())
        if want != self.height():                                            
            self.setFixedHeight(want)

    def paintEvent(self, _ev) -> None:                                  
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._svg is None:
            self._fallback(p)
            p.end()
            return
                                                                 
                                                   
        vb = self._vb
        s = min(self.width() / float(vb.width()),
                self.height() / float(vb.height()))
        w, h = vb.width() * s, vb.height() * s
        self._svg.render(p, QRectF((self.width() - w) / 2.0,
                                   (self.height() - h) / 2.0, w, h))
        p.end()

    def _fallback(self, p: QPainter) -> None:
                             

                                              
                                                      
                                                 
                       
           
        c = QColor(C["accent"])
        c.setAlpha(70)
        hud.paint_scene(p, QRectF(self.rect()), c)


class HeroPanel(QFrame):
                             

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("HeroPanel")                        
        self.setFixedWidth(HERO_W)                                 

    def paintEvent(self, _ev) -> None:                          
                         

                                                             
                                                         
             

                                                      
                                                                 
                                                

                                                
                                                
                                            
                                                            
           
        opt = QStyleOption()
        opt.initFrom(self)
        p = QStylePainter(self)
        p.drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        w, h = self.width(), self.height()
        for cx, cy, r, col, a in (
                (0.88 * w, 0.92 * h, 0.60 * w, C["accent_2"], 31),         
                (0.12 * w, 0.08 * h, 0.62 * w, C["accent"],   26)):        
            g = QRadialGradient(QPointF(cx, cy), r)
            c0, c1 = QColor(col), QColor(col)
            c0.setAlpha(a)
            c1.setAlpha(0)
            g.setColorAt(0.0, c0)
            g.setColorAt(1.0, c1)
            p.setBrush(g)
            p.drawRect(0, 0, w, h)


class _PointIcon(QWidget):
                  

                                                   
                                               
                                
       

    def __init__(self, name: str, size: int = 16, parent: QWidget | None = None):
        super().__init__(parent)
        self.name = name
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, _ev) -> None:                                  
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                                                   
        icons.paint(p, self.name, QRectF(self.rect()), QColor(C["accent"]), 1.8)
        p.end()


class LoginWindow(QDialog):
                                            

    loggedIn = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("AppRoot")
        self.setWindowTitle(f"{cfg.APP_NAME} · 登录")
        self.setFixedSize(*self._fit_size())
        self.user: dict | None = None

        s = cfg.load_settings()
        self.remember = QCheckBox("记住账号")
        self.remember.setChecked(bool(s.get("last_username")))
        if s.get("last_username"):                                     
            self._last_user = str(s["last_username"])
        else:
            self._last_user = ""

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._left(), 0)
        root.addWidget(self._right(), 1)

        self.toast = Toast(self)

    @staticmethod
    def _fit_size() -> tuple[int, int]:
                                    

                                                             
                                            
                              
           
        scr = QApplication.primaryScreen()
        if scr is not None:
            avail = scr.availableGeometry().height()
            if avail and avail < WIN_H + 60:
                return WIN_SMALL
        return WIN_W, WIN_H

                                                                   
    def _left(self) -> QWidget:
        w = HeroPanel()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(34, 34, 30, 30)
        lay.setSpacing(0)

        lay.addWidget(IconBadge("bridge", 46), 0, Qt.AlignmentFlag.AlignLeft)
        lay.addSpacing(16)

        t = QLabel(cfg.APP_NAME)
        t.setObjectName("HeroTitle")
        lay.addWidget(t)
        lay.addSpacing(8)

        sub = QLabel(cfg.APP_TITLE)
        sub.setObjectName("HeroSub")
        sub.setWordWrap(True)
        lay.addWidget(sub)

                                                         
                                                              
                                  
        lay.addStretch(1)
        self.art = HeroArt(HERO_W - 64)
        lay.addWidget(self.art)
        lay.addStretch(1)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(9)
        for i, (icon, text) in enumerate(POINTS):
            grid.addWidget(self._point(icon, text), i // 2, i % 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        lay.addSpacing(16)

                                                      
                                
        foot = QLabel(f"{cfg.APP_NAME_EN} · {cfg.APP_VERSION}")
        foot.setObjectName("HeroFoot")
        lay.addWidget(foot)
        return w

    @staticmethod
    def _point(icon: str, text: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(7)
        lay.addWidget(_PointIcon(icon))
        lab = QLabel(text)
        lab.setObjectName("HeroPoint")
        lay.addWidget(lab)
        lay.addStretch(1)
        return w

                                                                      
    def _right(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(80, 44, 80, 40)
        lay.setSpacing(0)

                                               
                                                      
                                              
        lay.addStretch(1)

        self.tab_login = QPushButton("登录")
        self.tab_reg = QPushButton("注册")
        tabs = QHBoxLayout()
        tabs.setSpacing(6)
        for b in (self.tab_login, self.tab_reg):
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setMinimumHeight(34)
            tabs.addWidget(b)
        self.tab_login.setChecked(True)
        self.tab_login.clicked.connect(lambda: self._switch(0))
        self.tab_reg.clicked.connect(lambda: self._switch(1))
        lay.addLayout(tabs)
        lay.addSpacing(28)

        self.title = QLabel("欢迎回来")
        self.title.setObjectName("FormTitle")
        lay.addWidget(self.title)
        self.subtitle = QLabel("请使用巡检账号登录系统")
        self.subtitle.setObjectName("FormSub")
        lay.addWidget(self.subtitle)
        lay.addSpacing(26)

        self.in_user = QLineEdit(self._last_user)
        self.in_user.setPlaceholderText("账号")
        self.in_user.setMinimumHeight(40)
        self.in_pwd = QLineEdit()
        self.in_pwd.setPlaceholderText("密码")
        self.in_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.in_pwd.setMinimumHeight(40)
        self.in_pwd2 = QLineEdit()
        self.in_pwd2.setPlaceholderText("确认密码")
        self.in_pwd2.setEchoMode(QLineEdit.EchoMode.Password)
        self.in_pwd2.setMinimumHeight(40)
        self.in_pwd2.hide()
        lay.addWidget(self.in_user)
        lay.addSpacing(12)
        lay.addWidget(self.in_pwd)
                                                      
                                                                   
                                           
        self.gap_pwd2 = QWidget()
        self.gap_pwd2.setFixedHeight(12)
        self.gap_pwd2.hide()
        lay.addWidget(self.gap_pwd2)
        lay.addWidget(self.in_pwd2)
        lay.addSpacing(12)
        self.in_pwd.returnPressed.connect(self._submit)
        self.in_pwd2.returnPressed.connect(self._submit)

        opt = QHBoxLayout()
        opt.addWidget(self.remember)
        opt.addStretch(1)
        hint = QLabel("内置账号 admin / 123456")
        hint.setObjectName("HeroFoot")
        opt.addWidget(hint)
        lay.addLayout(opt)
        lay.addSpacing(18)

        self.btn = QPushButton("登 录")
        self.btn.setProperty("accent", "primary")
        self.btn.setMinimumHeight(42)
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self._submit)
        lay.addWidget(self.btn)
        lay.addSpacing(12)

        self.msg = QLabel("")
        self.msg.setWordWrap(True)
        lay.addWidget(self.msg)
        lay.addSpacing(20)

        lay.addWidget(self._status())
        lay.addStretch(1)

        self._switch(0)
        return w

    @staticmethod
    def _status() -> QWidget:
                                        

                                                  
                                                    
                                                   
                        

                                                                
                                                    
                                           
           
        online = cfg.llm_ready()
        src = (cfg.llm_provider_label() + "（在线）" if online
               else "本地规则引擎（未配置 API Key）")
        try:
            st = db.stat_summary()
            n_img = int(st.get("images") or 0)
        except Exception:                                         
            n_img = 0                                              

        lab = QLabel(f"规划来源：{src}　影像 {n_img} 张")
        lab.setObjectName("HeroFoot")
        lab.setWordWrap(True)
        return lab

                                                                        
    def _switch(self, mode: int) -> None:
        self.mode = mode
        self.tab_login.setChecked(mode == 0)
        self.tab_reg.setChecked(mode == 1)
        self.tab_login.setProperty("accent", "primary" if mode == 0 else "")
        self.tab_reg.setProperty("accent", "primary" if mode == 1 else "")
        for b in (self.tab_login, self.tab_reg):
            b.style().unpolish(b)
            b.style().polish(b)
        self.title.setText("欢迎回来" if mode == 0 else "创建巡检账号")
        self.subtitle.setText("请使用巡检账号登录系统" if mode == 0
                              else "账号与口令将写入本地用户库")
        self.btn.setText("登 录" if mode == 0 else "注 册")
        self.in_pwd2.setVisible(mode == 1)
        self.gap_pwd2.setVisible(mode == 1)
        self.msg.setText("")

    def _submit(self) -> None:
        u = self.in_user.text().strip()
        p = self.in_pwd.text()
        if not u or not p:
            self.msg.setText("请填写账号与密码")
            return
        if self.mode == 0:
            row = db.verify_user(u, p)
            if not row:
                self.msg.setText("账号或密码不正确")
                return
            s = cfg.load_settings()
            s["last_username"] = u if self.remember.isChecked() else ""
            cfg.save_settings(s)
            self.user = dict(row)
            self.loggedIn.emit(self.user)
            self.accept()
            return

        if len(p) < 6:
            self.msg.setText("密码至少 6 位")
            return
        if p != self.in_pwd2.text():
            self.msg.setText("两次输入的密码不一致")
            return
        ok, msg = db.create_user(u, p, role="巡检员")
        if not ok:
            self.msg.setText(msg)
            return
        self.msg.setStyleSheet(f"font-size: 12.5px; color: {C['ok']};")
        self.msg.setText(msg + "，请登录")
        self.in_pwd.clear()
        self.in_pwd2.clear()
        QTimer.singleShot(900, lambda: self._switch(0))


def run_login() -> dict | None:
                                   
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
                                                   
                               
    theme.apply_app_font(app)
    app.setStyleSheet(theme.build_qss())
    db.ensure_default_user()
    w = LoginWindow()
    w.show()
    app.exec()
    return w.user
