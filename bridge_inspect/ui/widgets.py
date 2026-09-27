          

                                               
                              
   

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from PyQt6.QtCore import QRectF, QStandardPaths, Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import (
    QColor, QFont, QLinearGradient, QPageSize, QPainter, QPixmap,
)
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QButtonGroup, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QStyle, QStyleOption, QStylePainter, QTabWidget,
    QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget,
    QHeaderView, QAbstractItemView, QMessageBox,
)

from .. import config as cfg
from .. import theme
from ..core import imgutil
from . import hud, icons

C = theme.C

                                               
                                                         
                                                 
                                           


                                                                            
      
                                                                            
def hline() -> QFrame:
    f = QFrame()
    f.setProperty("role", "hline")
    f.setFixedHeight(1)
    return f


                                                          
                                                       
                                   
                                                         
                                      


class Panel(QFrame):
                          

    def __init__(self, title: str = "", parent: QWidget | None = None,
                 padding: int = 14):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(padding, padding, padding, padding)
        self.box.setSpacing(10)

        self.head = QHBoxLayout()
        self.head.setSpacing(8)
        self.title = QLabel(title)
        self.title.setObjectName("PanelTitle")
        self.head.addWidget(self.title)
        self.head.addStretch(1)
        self.box.addLayout(self.head)
        if not title:
            self.title.hide()

    def set_title(self, text: str) -> None:
        self.title.setText(text)
        self.title.setVisible(bool(text))

    def add_head_widget(self, w: QWidget) -> None:
        self.head.addWidget(w)

    def body(self) -> QVBoxLayout:
        return self.box


class StatCard(QFrame):
                                              

    def __init__(self, label: str, value: str = "0", unit: str = "",
                 accent: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StatCardAccent" if accent else "StatCard")
        self.setMinimumHeight(84)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 11, 14, 11)
        lay.setSpacing(3)

        self.lab = QLabel(label)
        self.lab.setObjectName("StatLabel")

        row = QHBoxLayout()
        row.setSpacing(4)
        self.val = QLabel(value)
        self.val.setObjectName("StatValueAccent" if accent else "StatValue")
        row.addWidget(self.val)
        self.unit = QLabel(unit)
        self.unit.setObjectName("StatUnit")
        self.unit.setAlignment(Qt.AlignmentFlag.AlignBottom)
        row.addWidget(self.unit, 0, Qt.AlignmentFlag.AlignBottom)
        row.addStretch(1)

        lay.addWidget(self.lab)
        lay.addLayout(row)
        lay.addStretch(1)

    def set_value(self, value, unit: str | None = None) -> None:
        self.val.setText(str(value))
        if unit is not None:
            self.unit.setText(unit)


class Badge(QLabel):
                            

    def __init__(self, text: str = "", demo: bool = True,
                 parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setObjectName("Badge")
        self.setProperty("demo", "true" if demo else "false")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def set_state(self, text: str, demo: bool) -> None:
        self.setText(text)
        self.setProperty("demo", "true" if demo else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class Hint(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setObjectName("Hint")
        self.setWordWrap(True)


class IconBadge(QWidget):
                                

                                          
                                                      
                               
       

    def __init__(self, name: str, size: int = 38, parent: QWidget | None = None):
        super().__init__(parent)
        self.name = name
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, _ev) -> None:                                    
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0.0, QColor(C["brand_a"]))
        g.setColorAt(1.0, QColor(C["brand_b"]))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(QRectF(self.rect()), 10, 10)
        inset = self.width() * 0.21
        icons.paint(p, self.name, QRectF(self.rect()).adjusted(
            inset, inset, -inset, -inset), QColor("#FFFFFF"), 1.7)
        p.end()


class PageHeader(QFrame):
                                    

                                                        
                                   
       

    def __init__(self, icon: str, title: str, subtitle: str,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Header")
        self.setFixedHeight(72)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(13)

        lay.addWidget(IconBadge(icon))

        col = QVBoxLayout()
        col.setSpacing(1)
        t = QLabel(title)
        t.setObjectName("PageTitle")
        s = QLabel(subtitle)
        s.setObjectName("PageSubtitle")
        col.addWidget(t)
        col.addWidget(s)
        lay.addLayout(col)
        lay.addStretch(1)

        self.actions = QHBoxLayout()
        self.actions.setSpacing(8)
        lay.addLayout(self.actions)

    def add_action(self, w: QWidget) -> None:
        self.actions.addWidget(w)

    def paintEvent(self, _ev) -> None:                                    
                        

                                                       
                                                            
                                                     
           
        opt = QStyleOption()
        opt.initFrom(self)
        p = QStylePainter(self)
        p.drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt)
        hud.paint_ruler(
            p, QRectF(0, 0, self.width(), self.height() - 1),
            QColor(34, 211, 238, 36), QColor(34, 211, 238, 78))


class ToolBar(QWidget):
                                           

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.lay = QHBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(8)

    def add(self, text: str, slot=None, accent: str = "",
            tooltip: str = "", enabled: bool = True) -> QPushButton:
        b = QPushButton(text)
        if accent:
            b.setProperty("accent", accent)
        if tooltip:
            b.setToolTip(tooltip)
        b.setEnabled(enabled)
        if slot:
            b.clicked.connect(slot)
        self.lay.addWidget(b)
        return b

    def addWidget(self, w: QWidget) -> None:                               
                                      
        self.lay.addWidget(w)

    def stretch(self) -> None:
        self.lay.addStretch(1)


class SubTabs(QTabWidget):
                     

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setDocumentMode(True)
        self.tabBar().setExpanding(False)


def pick_images(parent, multiple: bool) -> list[str] | str:
                            

                                              
                                           
                      
       
    s = cfg.load_settings()
    start = s.get("last_image_dir") or QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.PicturesLocation) or str(cfg.IMG_DIR)
    filt = imgutil.dialog_filter()
    if multiple:
        paths, _ = QFileDialog.getOpenFileNames(parent, "选择影像", start, filt)
    else:
        one, _ = QFileDialog.getOpenFileName(parent, "选择影像", start, filt)
        paths = [one] if one else []
    if paths:
        s["last_image_dir"] = str(Path(paths[0]).parent)
        cfg.save_settings(s)
    return paths


def ask_ingest(parent, filename: str) -> bool:
                             

                                            
                                              
                                            
                                                             

                                          
               
       
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle("影像尚未入库")
    box.setText(f"「{filename}」不在本系统的影像库里。")
    box.setInformativeText(
        "要现在入库吗？\n\n"
        "入库会把这张影像复制一份到 data/images/，之后检测结果才有地方保存，"
        "分割量化、长周期监测与报告里也才看得到它。\n\n"
        "选「仅查看」只是把图打开看看，检测结果不会保存。")
    yes = box.addButton("入库并继续", QMessageBox.ButtonRole.AcceptRole)
    box.addButton("仅查看", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(yes)
    box.exec()
    return box.clickedButton() is yes


def make_table(headers: list[str], stretch_col: int = -1) -> QTableWidget:
                   
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.setAlternatingRowColors(True)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setShowGrid(False)
    t.horizontalHeader().setHighlightSections(False)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    if stretch_col >= 0:
        t.horizontalHeader().setSectionResizeMode(
            stretch_col, QHeaderView.ResizeMode.Stretch)
    t.setWordWrap(False)
    return t


def _needs_tooltip(text: str) -> bool:
                            

                                            
                                        
       
    if not text:
        return False
                                                  
    if any("一" <= ch <= "鿿" for ch in text):
        return True
    return len(text) > 12


def fill_table(table: QTableWidget, rows: Iterable[Iterable], color_of=None) -> None:
                                            
    rows = list(rows)
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        col = color_of(row) if color_of else None
        for c, v in enumerate(row):
            text = "" if v is None else str(v)
            it = QTableWidgetItem(text)
                                            
                                        
            if _needs_tooltip(text):
                it.setToolTip(text)
            if col:
                it.setForeground(QColor(col))
            if c > 0:
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(r, c, it)


class KeyValue(QWidget):
                                       

    def __init__(self, parent: QWidget | None = None, columns: int = 1):
        super().__init__(parent)
        self.columns = columns
        self.grid = QHBoxLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(18)
        self._cols: list[QVBoxLayout] = []
        for _ in range(columns):
            col = QVBoxLayout()
            col.setSpacing(7)
            self._cols.append(col)
            self.grid.addLayout(col)
        self._n = 0

    def clear(self) -> None:
        for col in self._cols:
            while col.count():
                item = col.takeAt(0)
                w = item.widget()
                if w:
                                                                          
                                                      
                                                      
                                                               
                    w.setParent(None)
                    w.deleteLater()
        self._n = 0

    def add(self, key: str, value: str, color: str | None = None) -> None:
        col = self._cols[self._n % self.columns]
        self._n += 1
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        k = QLabel(key)
        k.setObjectName("StatLabel")
        k.setMinimumWidth(84)
        v = QLabel(str(value))
        v.setWordWrap(True)
        v.setStyleSheet(f"color: {color or C['text']}; font-size: 12.5px;")
        lay.addWidget(k)
        lay.addWidget(v, 1)
        col.addWidget(row)


class ChartView(QFrame):
                                    

    def __init__(self, parent: QWidget | None = None, height: int = 240,
                 toolbar_hint: str = ""):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumHeight(height)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 6)
        lay.setSpacing(4)

        self.hint = QLabel(toolbar_hint)
        self.hint.setObjectName("Hint")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        if toolbar_hint:
            lay.addWidget(self.hint)

        self.canvas = None
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure

            theme.apply_mpl_theme()
            self.fig = Figure(figsize=(5, 3), dpi=100)
            self.canvas = FigureCanvasQTAgg(self.fig)
            self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding,
                                      QSizePolicy.Policy.Expanding)
            lay.addWidget(self.canvas, 1)
            self.ax = self.fig.add_subplot(111)
            self.empty_hint()
        except Exception as exc:                                          
            self.fig = None
            self.ax = None
            fallback = QLabel(f"图表组件不可用：{exc}")
            fallback.setObjectName("Hint")
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(fallback, 1)

                                                                      
    def _reset(self):
        if self.fig is None:
            return None
        self.fig.clear()
        self.ax = self.fig.add_subplot(111)
        return self.ax

    def _finish(self):
        if self.fig is not None:
            self.fig.tight_layout()
            self.canvas.draw_idle()

    def empty_hint(self, text: str = "暂无数据") -> None:
        ax = self._reset()
        if ax is None:
            return
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.text(0.5, 0.5, text, ha="center", va="center",
                color=C["text_muted"], fontsize=10, transform=ax.transAxes)
        self._finish()

    def plot_lines(self, x: list, series: dict[str, list], xlabel: str = "",
                   ylabel: str = "", marker: str = "o") -> None:
                                      
        ax = self._reset()
        if ax is None:
            return
        colors = [C["accent"], C["accent_2"], C["warn"], C["ok"],
                  C["purple"], C["danger"], C["info"]]
        for i, (name, ys) in enumerate(series.items()):
            col = colors[i % len(colors)]
            ax.plot(x[: len(ys)], ys, marker=marker, markersize=4.5,
                    linewidth=1.9, color=col, label=name,
                    markerfacecolor=C["card"], markeredgewidth=1.6)
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)
        if len(series) > 1:
            ax.legend(loc="best", fontsize=8.5)
        ax.grid(True, alpha=0.35, linestyle="--", linewidth=0.6)
        self._finish()

    def plot_bars(self, labels: list[str], values: list[float],
                  colors: list[str] | None = None, ylabel: str = "") -> None:
        ax = self._reset()
        if ax is None:
            return
        cols = colors or [C["accent"]] * len(labels)
        bars = ax.bar(labels, values, color=cols, width=0.62,
                      edgecolor="none")
        for b, v in zip(bars, values):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                    f"{v:.2f}", ha="center", va="bottom",
                    fontsize=8, color=C["text_dim"])
        if ylabel:
            ax.set_ylabel(ylabel)
        ax.grid(True, axis="y", alpha=0.35, linestyle="--", linewidth=0.6)
        ax.tick_params(axis="x", labelsize=8.5)
        self._finish()

                                                      
                                                        
                                               
                                       
                           


class ImageView(QLabel):
                                      

    filesDropped = pyqtSignal(list)
    clicked = pyqtSignal()

    def __init__(self, placeholder: str = "尚未载入图像",
                 accept_drop: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.placeholder = placeholder
        self.setAcceptDrops(accept_drop)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(
            f"background: {C['input']}; border: 1px dashed {C['border_hi']};"
            f"border-radius: 10px; color: {C['text_muted']}; font-size: 12.5px;")
        self._src: QPixmap | None = None
        self._text = placeholder
        self._caption = ""

                                                                      
    def set_image(self, bgr, caption: str = "") -> None:
        if bgr is None:
            self.clear_image()
            return
        self._src = imgutil.bgr_to_qpixmap(bgr)
        self._caption = caption
        self._render()

    def set_qimage(self, qimg, caption: str = "") -> None:
        if qimg is None or qimg.isNull():
            self.clear_image()
            return
        self._src = QPixmap.fromImage(qimg)
        self._caption = caption
        self._render()

    def clear_image(self) -> None:
        self._src = None
        self._caption = ""
        self._render()

    def has_image(self) -> bool:
        return self._src is not None

                                                                        
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._render()

    def _render(self) -> None:
        if self._src is None:
            self.setPixmap(QPixmap())
            self.setText(self.placeholder)
            return
        self.setText("")
        area = self.size() - QSize(16, 16)
        if area.width() <= 0 or area.height() <= 0:
            return
        scaled = self._src.scaled(
            area, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        if not self._caption:
            self.setPixmap(scaled)
            return
                                                     
        canvas = QPixmap(area)
        canvas.fill(QColor(C["input"]))
        p = QPainter(canvas)
        p.drawPixmap((area.width() - scaled.width()) // 2,
                     (area.height() - scaled.height()) // 2, scaled)
        p.setPen(QColor(C["text_dim"]))
        f = QFont(); f.setPointSize(9); p.setFont(f)
        m = p.fontMetrics()
        tw = m.horizontalAdvance(self._caption)
        p.fillRect(8, area.height() - 26, tw + 16, 20, QColor(11, 18, 32, 205))
        p.drawText(16, area.height() - 12, self._caption)
        p.end()
        self.setPixmap(canvas)

                                                                        
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        paths = [p for p in paths if imgutil.is_supported(p)]
        if paths:
            self.filesDropped.emit(paths)

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        if self._src is not None:
            self.clicked.emit()


class HtmlView(QTextBrowser):
                            

                                                   
                                                      
                                            
                                       

                                                         
                                       
       

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(
            f"QTextBrowser {{ background: #FFFFFF; color: #000000;"
            f" border: 1px solid {C['border']}; border-radius: 8px; }}")
                                                 
        self.document().setDocumentMargin(8)


def open_html_dialog(parent: QWidget, html: str, title: str,
                     path: str | Path | None = None) -> None:
                                    

                                               
                                            
                            
       
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.resize(940, 780)
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(12, 12, 12, 12)
    lay.setSpacing(10)

    view = HtmlView(dlg)
    view.setHtml(html)
    lay.addWidget(view, 1)

    head = QLabel("报告以 A4 竖排版式渲染；「打印」可直接输出到打印机或"
                  "「Microsoft Print to PDF」另存为 PDF。")
    head.setStyleSheet(f"color: {C['text_muted']}; font-size: 12.5px;")
    head.setWordWrap(True)

    row = QHBoxLayout()
    row.setSpacing(8)
    row.addWidget(head, 1)

    def do_print() -> None:
                                                 
                                        
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        dlg_pr = QPrintDialog(printer, dlg)
        dlg_pr.setWindowTitle("打印巡检报告")
        if dlg_pr.exec() == QPrintDialog.DialogCode.Accepted:
            view.print_(printer)

    if path is not None:
        p = Path(path)
        btn_br = QPushButton("用浏览器打开")
        btn_br.setToolTip("交给系统默认浏览器，可用于打印、另存 PDF 或分享")
        btn_br.clicked.connect(
            lambda: os.startfile(str(p)))                             
        row.addWidget(btn_br)

    btn_print = QPushButton("打印")
    btn_print.setProperty("accent", "primary")
    btn_print.clicked.connect(do_print)
    row.addWidget(btn_print)

    btn_close = QPushButton("关闭")
    btn_close.clicked.connect(dlg.accept)
    row.addWidget(btn_close)
    lay.addLayout(row)

    dlg.exec()


class Toast(QLabel):
                          

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("Badge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text: str, kind: str = "info",
                     msec: int = 2600) -> None:
        color = {"ok": C["ok"], "warn": C["warn"],
                 "error": C["danger"], "info": C["accent"]}.get(kind, C["accent"])
        self.setText(text)
        self.setStyleSheet(
            f"#Badge {{ background: {C['card_hi']}; color: {color};"
            f"border: 1px solid {color}; border-radius: 9px;"
            f"padding: 9px 18px; font-size: 12.5px; }}")
        self.adjustSize()
        self.move(max(10, (self.parent().width() - self.width()) // 2), 88)
        self.raise_()
        self.show()
        self._timer.start(msec)


class NavButton(QPushButton):
                       

                                                   
                                                  
                                  

                                                         
                           
       

    ICON_X = 15.0
    ICON_SIZE = 18.0
    ICON_SW = 1.55                                             

    def __init__(self, key: str, text: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.key = key
        self.setObjectName("NavItem")

    def paintEvent(self, _ev) -> None:                                    
        super().paintEvent(_ev)                        
        checked = self.isChecked()
        color = QColor(C["accent"] if checked
                       else (C["text"] if self.underMouse() else C["text_dim"]))
        box = QRectF(self.ICON_X, (self.height() - self.ICON_SIZE) / 2.0,
                     self.ICON_SIZE, self.ICON_SIZE)
        p = QPainter(self)
                                               
                                         
        if checked:
            glow = QColor(C["accent"])
            glow.setAlpha(60)
            icons.paint(p, self.key, box, glow, self.ICON_SW + 2.4)
        icons.paint(p, self.key, box, color, self.ICON_SW)
        p.end()


class Sidebar(QFrame):
                                         

    navChanged = pyqtSignal(int)
    logoutClicked = pyqtSignal()

                                       
                             
                                          
    ITEMS = [
        ("agent", "任务工作台", "用自然语言下达巡检任务"),
        ("detect", "目标检测", "识别七类桥梁病害"),
        ("segment", "分割量化", "像素级量化裂缝长度与宽度"),
        ("history", "检测历史", "历史任务、报告与产物文件"),
        ("trend", "长周期监测", "多批次同视场比对"),
        ("settings", "系统管理", "模型、存储与大模型接口"),
    ]

    def __init__(self, user: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(244)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 20, 14, 16)
        lay.setSpacing(8)

        lay.addWidget(self._brand())
        lay.addSpacing(12)
        grp = QLabel("功能导航")
        grp.setObjectName("NavGroup")
        lay.addWidget(grp)
        lay.addSpacing(2)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        for i, (key, name, tip) in enumerate(self.ITEMS):
            b = NavButton(key, name)
            b.setCheckable(True)
                                           
                                       
            b.setToolTip(f"{tip}\n图标：{icons.about(key)}" if icons.about(key) else tip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if i == 0:
                b.setChecked(True)
            self.group.addButton(b, i)
            lay.addWidget(b)
        self.group.idClicked.connect(self.navChanged.emit)

        lay.addStretch(1)
                                               
        lay.addWidget(hud.StripArt())
        lay.addWidget(self._user_card(user))

    def _brand(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(2, 0, 0, 0)
        lay.setSpacing(10)
        logo = QLabel("桥")
        logo.setFixedSize(38, 38)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 {C['brand_a']}, stop:1 {C['brand_b']});"
            f"border-radius: 11px; color: #FFFFFF; font-size: 19px;"
            f"font-weight: 700;")
        lay.addWidget(logo)
        col = QVBoxLayout()
        col.setSpacing(0)
        t = QLabel("桥梁智巡")
        t.setObjectName("BrandTitle")
        s = QLabel("BRIDGE INSPECTION")
        s.setObjectName("BrandSub")
        col.addWidget(t)
        col.addWidget(s)
        lay.addLayout(col)
        lay.addStretch(1)
        return w

    def _user_card(self, user: dict) -> QWidget:
        w = QFrame()
        w.setObjectName("UserCard")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(9)
        name = (user.get("display_name") or user.get("username") or "用户")
        av = QLabel(name[:1])
        av.setFixedSize(32, 32)
        av.setAlignment(Qt.AlignmentFlag.AlignCenter)
        av.setStyleSheet(
            f"background: {C['accent_dim']}; border-radius: 16px;"
            f"color: {C['accent']}; font-size: 14px; font-weight: 700;")
        top.addWidget(av)
        col = QVBoxLayout()
        col.setSpacing(1)
        n = QLabel(name)
        n.setObjectName("UserName")
        r = QLabel(user.get("role") or "巡检员")
        r.setObjectName("UserRole")
        col.addWidget(n)
        col.addWidget(r)
        top.addLayout(col)
        top.addStretch(1)
        lay.addLayout(top)

        out = QPushButton("退出登录")
        out.setProperty("accent", "danger")
        out.clicked.connect(self.logoutClicked.emit)
        lay.addWidget(out)
        return w

    def select(self, index: int) -> None:
        b = self.group.button(index)
        if b:
            b.setChecked(True)
            self.navChanged.emit(index)


def scrollable(widget: QWidget) -> QScrollArea:
                    
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return area
