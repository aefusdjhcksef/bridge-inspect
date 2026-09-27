                          

                                        
                                
                                         

                                                            
                            
                                               
                                  
                                                   

                                          
                                                              
   

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import QWidget

from .. import theme

                                                       
SCENE_W, SCENE_H = 520.0, 250.0
STRIP_W, STRIP_H = 152.0, 74.0


def _pen(p: QPainter, color: QColor, width: float = 1.3,
         dash: list[float] | None = None) -> None:
    pen = QPen(color, width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    if dash:
        pen.setDashPattern(dash)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)


def _lines(p: QPainter, color: QColor, width: float, *segs: tuple[float, ...],
           dash: list[float] | None = None) -> None:
                                                     
    _pen(p, color, width, dash)
    for x1, y1, x2, y2 in segs:
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))


                                                                            
    
                                                                            
def paint_grid(p: QPainter, rect: QRectF, fine: QColor, coarse: QColor,
               step: float = 28.0, every: int = 5) -> None:
                                   
    if rect.width() < step or rect.height() < step:
        return
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    for i in range(int(rect.width() // step) + 2):
        x = round(rect.left() + i * step) + 0.5                              
        if x > rect.right():
            break
        _pen(p, coarse if i % every == 0 else fine, 1.0)
        p.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
    for j in range(int(rect.height() // step) + 2):
        y = round(rect.top() + j * step) + 0.5
        if y > rect.bottom():
            break
        _pen(p, coarse if j % every == 0 else fine, 1.0)
        p.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
    p.restore()


def paint_ruler(p: QPainter, rect: QRectF, tick: QColor, major: QColor,
                step: float = 16.0, every: int = 8) -> None:
                                       
    if rect.width() < step * 2:
        return
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    base = rect.bottom() - 0.5
    for i in range(int(rect.width() // step) + 1):
        x = round(rect.left() + i * step) + 0.5
        if x > rect.right():
            break
        big = (i % every == 0)
        _pen(p, major if big else tick, 1.0)
        p.drawLine(QPointF(x, base), QPointF(x, base - (9.0 if big else 5.0)))
    p.restore()


                                                                            
    
                                                                            
def paint_scene(p: QPainter, rect: QRectF, color: QColor) -> None:
                                  

                                  
       
    if rect.width() < 200 or rect.height() < 110:
        return
    s = min(rect.width() / SCENE_W, rect.height() / SCENE_H)
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.translate(rect.right() - SCENE_W * s, rect.bottom() - SCENE_H * s)
    p.scale(s, s)

                                    
    _lines(p, color, 2.2, (18, 148, 502, 148), (18, 196, 502, 196))
    _lines(p, color, 1.3,
           (52, 148, 52, 196), (158, 148, 158, 196), (264, 148, 264, 196),
           (370, 148, 370, 196), (476, 148, 476, 196),
           (52, 196, 106, 148), (158, 196, 212, 148), (264, 196, 318, 148),
           (370, 196, 424, 148), (476, 196, 502, 165),
           (52, 196, 52, 236), (158, 196, 158, 242), (264, 196, 264, 248),
           (370, 196, 370, 242), (476, 196, 476, 236))

    water = QColor(color)
    water.setAlpha(int(color.alpha() * 0.6))
    _lines(p, water, 1.3,
           (10, 236, 58, 236), (118, 242, 158, 242), (224, 248, 264, 248),
           (330, 242, 370, 242), (436, 236, 484, 236), dash=[6, 7])

                                    
    _pen(p, color, 1.3, dash=[5, 7])
    path = _path((42, 62), (112, 20), (190, 96), (268, 58))
    path.cubicTo(QPointF(346, 20), QPointF(400, 78), QPointF(448, 40))
    p.drawPath(path)

    _pen(p, color, 1.3)
    p.setBrush(color)
    for cx, cy in ((42, 62), (170, 62), (268, 58), (386, 66)):
        p.drawEllipse(QPointF(cx, cy), 3.2, 3.2)
    p.setBrush(Qt.BrushStyle.NoBrush)

                                
    fov = QColor(color)
    fov.setAlpha(int(color.alpha() * 0.55))
    _lines(p, fov, 1.3, (448, 52, 344, 148), (448, 52, 500, 140), dash=[3, 5])

               
    p.save()
    p.translate(448, 40)
    _pen(p, color, 1.3)
    p.drawRoundedRect(QRectF(-11, -4.5, 22, 9), 3, 3)
    _lines(p, color, 1.3,
           (-11, -2.5, -21, -8), (11, -2.5, 21, -8),
           (-11, 2.5, -21, 8), (11, 2.5, 21, 8))
    for sx in (-24, 24):
        for sy in (-11, 11):
            p.drawEllipse(QPointF(sx, sy), 8, 2.2)
    _lines(p, color, 1.3, (0, 5.5, 0, 16.5))
    p.drawPolygon(QPolygonF([QPointF(-4, 22), QPointF(4, 22), QPointF(0, 28)]))
    p.restore()

                                  
    _lines(p, color, 1.6,
           (18, 14, 18, 8), (18, 8, 26, 8),
           (502, 14, 502, 8), (502, 8, 494, 8),
           (18, 244, 18, 250), (18, 250, 26, 250),
           (502, 244, 502, 250), (502, 250, 494, 250))
    p.restore()


def paint_strip(p: QPainter, rect: QRectF, color: QColor) -> None:
                                
    if rect.width() < 60 or rect.height() < 30:
        return
    s = min(rect.width() / STRIP_W, rect.height() / STRIP_H)
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.translate(rect.center().x() - STRIP_W * s / 2,
                rect.bottom() - STRIP_H * s)
    p.scale(s, s)

    _lines(p, color, 1.8, (6, 46, 146, 46), (6, 62, 146, 62))
    _lines(p, color, 1.2,
           (24, 46, 24, 62), (60, 46, 60, 62), (96, 46, 96, 62), (132, 46, 132, 62),
           (24, 62, 42, 46), (60, 62, 78, 46), (96, 62, 114, 46), (132, 62, 146, 62))

    faint = QColor(color)
    faint.setAlpha(int(color.alpha() * 0.6))
    _lines(p, faint, 1.2,
           (10, 68, 16, 68), (34, 68, 40, 68), (70, 68, 76, 68),
           (106, 68, 112, 68), (142, 68, 146, 68), dash=[4, 5])

    _pen(p, color, 1.2, dash=[4, 5])
    path = _path((22, 18), (50, 6), (76, 24), (104, 12))
    p.drawPath(path)

    _pen(p, color, 1.2)
    p.setBrush(color)
    p.drawEllipse(QPointF(22, 18), 2.2, 2.2)
    p.drawEllipse(QPointF(104, 12), 2.2, 2.2)
    p.setBrush(Qt.BrushStyle.NoBrush)

    p.save()
    p.translate(120, 10)
    p.drawRoundedRect(QRectF(-7, -3, 14, 6), 2, 2)
    _lines(p, color, 1.2,
           (-7, -1.6, -13, -5), (7, -1.6, 13, -5),
           (-7, 1.6, -13, 5), (7, 1.6, 13, 5))
    for sx in (-15, 15):
        for sy in (-6.6, 6.6):
            p.drawEllipse(QPointF(sx, sy), 5, 1.5)
    p.restore()
    p.restore()


def _path(p0: tuple[float, float], c1: tuple[float, float],
          c2: tuple[float, float], p1: tuple[float, float]) -> QPainterPath:
                                          
    path = QPainterPath(QPointF(*p0))
    path.cubicTo(QPointF(*c1), QPointF(*c2), QPointF(*p1))
    return path


                                                                            
    
                                                                            
class HudRoot(QWidget):
                         

                                                                
                                      
                                                     
       

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("HudRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def paintEvent(self, _ev) -> None:                                    
        p = QPainter(self)
        rect = QRectF(self.rect())
        p.fillRect(self.rect(), QColor(theme.C["app"]))
                                                      
                                                    
                                       
                                                        
        paint_grid(p, rect, QColor(34, 211, 238, 20), QColor(34, 211, 238, 40))
        art = QColor(theme.C["accent"])
        art.setAlpha(42)
        paint_scene(p, rect.adjusted(24, 24, -24, -24), art)


class StripArt(QWidget):
                                 

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(58)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, _ev) -> None:                                    
        p = QPainter(self)
        c = QColor(theme.C["accent"])
        c.setAlpha(115)
        paint_strip(p, QRectF(self.rect()), c)
