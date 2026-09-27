                                           

                                        
                                           
                            
   

from __future__ import annotations

                                                                            
      
                                                                            
C = {
                
    "app":          "#0B1220",
    "sidebar_top":  "#0E1930",
    "sidebar_bot":  "#0A1120",
    "panel":        "#111C2E",
    "card":         "#16213A",
    "card_hi":      "#1B2946",
    "input":        "#0D1728",
    "hover":        "#1E2C4A",

        
    "border":       "#22314F",
    "border_hi":    "#2F4266",

          
    "accent":       "#22D3EE",
    "accent_2":     "#3B82F6",
    "accent_dim":   "#155E75",
    "brand_a":      "#2563EB",
    "brand_b":      "#22D3EE",

        
    "text":         "#E8EEF9",
    "text_dim":     "#8FA3C0",
    "text_muted":   "#5C6E8A",
    "text_on":      "#04121F",

         
    "ok":           "#34D399",
    "warn":         "#FBBF24",
    "danger":       "#F87171",
    "info":         "#60A5FA",
    "purple":       "#A78BFA",
}

                                        
                                                    
                                               
 
                                           
                                          
                                          
FONT_FAMILIES = ["SimSun", "宋体", "Songti SC",
                 "Microsoft YaHei UI", "Microsoft YaHei", "sans-serif"]
                                     
MONO_FAMILIES = ["Cascadia Mono", "Consolas", "Courier New", "monospace"]


def _stack(families: list[str]) -> str:
                                     
    return ", ".join(f'"{f}"' for f in families)


FONT_STACK = _stack(FONT_FAMILIES)
MONO_STACK = _stack(MONO_FAMILIES)


def apply_app_font(app) -> None:
                            

                                                        
                                                                
                                                 
                             

                                                   
                        
       
    from PyQt6.QtGui import QFont

    font = QFont()
    font.setFamilies(FONT_FAMILIES)
                                               
    font.setPointSizeF(10)
                                
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)


def _grad(a: str, b: str, horizontal: bool = True) -> str:
                       
    x2, y2 = ("1", "0") if horizontal else ("0", "1")
    return f"qlineargradient(x1:0, y1:0, x2:{x2}, y2:{y2}, stop:0 {a}, stop:1 {b})"


                                                                            
       
                                                                            
def build_qss() -> str:
    c = C
    return f"""
* {{
    font-family: {FONT_STACK};
    outline: none;
}}

QWidget {{
    background: transparent;
    color: {c['text']};
    font-size: 14px;
}}

QMainWindow, QDialog, #AppRoot {{
    background: {c['app']};
}}

#Sidebar {{
    background: {_grad(c['sidebar_top'], c['sidebar_bot'], horizontal=False)};
    border-right: 1px solid {c['border']};
}}
#BrandTitle   {{ font-size: 18px; font-weight: 700; color: {c['text']}; }}
#BrandSub     {{ font-size: 11px;  color: {c['text_muted']}; letter-spacing: 1.5px; }}
#NavGroup     {{ font-size: 12.5px; color: {c['text_muted']}; letter-spacing: 1px;
                 padding: 0 6px; }}
#UserCard     {{ background: {c['card']}; border: 1px solid {c['border']};
                 border-radius: 10px; }}
#UserName     {{ font-size: 14px; font-weight: 600; color: {c['text']}; }}
#UserRole     {{ font-size: 12.5px; color: {c['text_muted']}; }}

#HeroPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0.6, y2:1,
                                stop:0 {c['sidebar_top']}, stop:1 {c['sidebar_bot']});
    border-right: 1px solid {c['border']};
}}
#HeroTitle   {{ font-size: 30px; font-weight: 700; color: {c['text']}; }}
#HeroSub     {{ font-size: 12.5px; color: {c['text_dim']}; }}
#HeroPoint   {{ font-size: 12.5px; color: {c['text_dim']}; }}
#HeroFoot    {{ font-size: 12.5px; color: {c['text_muted']}; }}
#FormTitle   {{ font-size: 19px; font-weight: 700; color: {c['text']}; }}
#FormSub     {{ font-size: 12.5px; color: {c['text_muted']}; }}

QPushButton#NavItem {{
    text-align: left;
    padding: 0 12px 0 40px;
    min-height: 40px;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 8px;
    color: {c['text_dim']};
    font-size: 14px;
}}
QPushButton#NavItem:hover {{
    background: {c['hover']};
    color: {c['text']};
}}
QPushButton#NavItem:checked {{
    background: {_grad('#1D3A63', '#123047')};
    border-left: 3px solid {c['accent']};
    color: {c['text']};
    font-weight: 600;
}}

#Header {{
    background: {_grad(c['card_hi'], c['panel'], horizontal=False)};
    border-bottom: 1px solid {c['border']};
}}
#PageTitle    {{ font-size: 18px; font-weight: 700; color: {c['text']}; }}
#PageSubtitle {{ font-size: 12.5px; color: {c['text_dim']}; }}

#Panel {{
    background: {c['panel']};
    border: 1px solid {c['border']};
    border-radius: 12px;
}}
#Card {{
    background: {c['card']};
    border: 1px solid {c['border']};
    border-radius: 10px;
}}
#Card:hover {{ border: 1px solid {c['border_hi']}; }}
#StatCard {{
    background: {_grad('#17253F', '#141F36', horizontal=False)};
    border: 1px solid {c['border']};
    border-radius: 10px;
}}
#StatCardAccent {{
    background: {_grad('#173A50', '#152A44', horizontal=False)};
    border: 1px solid {c['accent_dim']};
    border-radius: 10px;
}}
#CardTitle    {{ font-size: 14px; font-weight: 600; color: {c['text']}; }}
#PanelTitle   {{ font-size: 14px; font-weight: 600; color: {c['text_dim']};
                 letter-spacing: 1px; }}
#StatLabel    {{ font-size: 12.5px; color: {c['text_dim']}; }}
#StatValue    {{ font-size: 24px; font-weight: 700; color: {c['text']}; }}
#StatValueAccent {{ font-size: 24px; font-weight: 700; color: {c['accent']}; }}
#StatUnit     {{ font-size: 12.5px; color: {c['text_muted']}; }}
#Hint         {{ font-size: 12.5px; color: {c['text_muted']}; }}
#Mono         {{ font-family: {MONO_STACK}; font-size: 12.5px; color: {c['text_dim']}; }}

QPushButton {{
    background: {c['card']};
    border: 1px solid {c['border_hi']};
    border-radius: 8px;
    padding: 7px 14px;
    color: {c['text_dim']};
    font-size: 12.5px;
}}
QPushButton:hover  {{ background: {c['hover']}; color: {c['text']};
                      border: 1px solid {c['accent_dim']}; }}
QPushButton:pressed {{ background: {c['input']}; }}
QPushButton:disabled {{ color: {c['text_muted']}; border: 1px solid {c['border']};
                        background: {c['panel']}; }}

QPushButton[accent="primary"] {{
    background: {_grad(c['brand_a'], '#1D4ED8')};
    border: 1px solid {c['brand_a']};
    color: #FFFFFF;
    font-weight: 600;
}}
QPushButton[accent="primary"]:hover {{
    background: {_grad('#3B82F6', c['brand_b'])};
    border: 1px solid {c['accent']};
}}
QPushButton[accent="primary"]:disabled {{
    background: {c['panel']}; color: {c['text_muted']};
    border: 1px solid {c['border']};
}}

QPushButton[accent="cyan"] {{
    background: {_grad('#0E7490', '#155E75')};
    border: 1px solid {c['accent']};
    color: #ECFEFF;
    font-weight: 600;
}}
QPushButton[accent="cyan"]:hover {{ background: {_grad('#0891B2', '#0E7490')}; }}

QPushButton[accent="danger"] {{
    background: transparent;
    border: 1px solid #7F2E38;
    color: {c['danger']};
}}
QPushButton[accent="danger"]:hover {{ background: #3A1A22; border-color: {c['danger']}; }}

QPushButton#Ghost {{ background: transparent; border: 1px solid transparent; }}

QPushButton#Chip {{
    background: transparent;
    border: 1px solid {c['border_hi']};
    border-radius: 11px;
    padding: 2px 9px;
    color: {c['text_muted']};
    font-size: 12.5px;
}}
QPushButton#Chip:hover {{ border-color: {c['accent_dim']}; color: {c['text_dim']}; }}
QPushButton#Chip:checked {{
    background: {c['accent_dim']};
    border: 1px solid {c['accent']};
    color: {c['text_on']};
    font-weight: 600;
}}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit {{
    background: {c['input']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 7px 10px;
    color: {c['text']};
    selection-background-color: {c['accent_dim']};
    selection-color: {c['text']};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QDateEdit:focus {{
    border: 1px solid {c['accent']};
}}
QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled {{ color: {c['text_muted']}; }}
QLineEdit[echoMode="2"] {{ letter-spacing: 2px; }}

QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {c['text_dim']};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {c['card']};
    border: 1px solid {c['border_hi']};
    border-radius: 8px;
    selection-background-color: {c['accent_dim']};
    color: {c['text']};
    padding: 4px;
    outline: none;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background: {c['card_hi']}; border: none; width: 16px;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    border-left: 3px solid transparent; border-right: 3px solid transparent;
    border-bottom: 4px solid {c['text_dim']};
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    border-left: 3px solid transparent; border-right: 3px solid transparent;
    border-top: 4px solid {c['text_dim']};
}}

QSlider::groove:horizontal {{
    height: 4px; background: {c['border']}; border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {_grad(c['brand_a'], c['accent'])}; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: #FFFFFF; width: 13px; height: 13px;
    margin: -5px 0; border-radius: 6px; border: 2px solid {c['accent']};
}}

QCheckBox {{ spacing: 7px; color: {c['text_dim']}; }}
QCheckBox::indicator {{
    width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid {c['border_hi']}; background: {c['input']};
}}
QCheckBox::indicator:checked {{
    background: {_grad(c['brand_a'], c['accent'])};
    border: 1px solid {c['accent']};
}}

QTableWidget, QTableView {{
    background: {c['card']};
    alternate-background-color: {c['card_hi']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    gridline-color: transparent;
    color: {c['text']};
    selection-background-color: {c['accent_dim']};
    selection-color: #FFFFFF;
}}
QTableWidget::item, QTableView::item {{ padding: 6px 8px; border: none; }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    background: {c['panel']};
    color: {c['text_dim']};
    border: none;
    border-bottom: 1px solid {c['border_hi']};
    padding: 7px 8px;
    font-size: 12.5px;
    font-weight: 600;
}}
QHeaderView::section:first {{ border-top-left-radius: 8px; }}
QHeaderView::section:last  {{ border-top-right-radius: 8px; }}
QTableCornerButton::section {{ background: {c['panel']}; border: none; }}

QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar::tab {{
    background: transparent;
    color: {c['text_muted']};
    padding: 7px 16px;
    margin-right: 4px;
    border: none;
    border-radius: 8px;
    font-size: 12.5px;
}}
QTabBar::tab:hover {{ color: {c['text']}; background: {c['card']}; }}
QTabBar::tab:selected {{
    background: {_grad('#1D3A63', '#123047')};
    color: {c['accent']};
    font-weight: 600;
}}

QScrollBar:vertical {{ background: transparent; width: 9px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background: {c['border_hi']}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {c['accent_dim']}; }}
QScrollBar:horizontal {{ background: transparent; height: 9px; margin: 2px; }}
QScrollBar::handle:horizontal {{
    background: {c['border_hi']}; border-radius: 4px; min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {c['accent_dim']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QSplitter::handle {{ background: transparent; }}
QSplitter::handle:hover {{ background: {c['border_hi']}; }}

QProgressBar {{
    background: {c['input']}; border: 1px solid {c['border']};
    border-radius: 6px; height: 8px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{
    background: {_grad(c['brand_a'], c['accent'])}; border-radius: 6px;
}}

QStatusBar {{ background: {c['panel']}; border-top: 1px solid {c['border']};
              color: {c['text_muted']}; font-size: 12.5px; }}
QStatusBar::item {{ border: none; }}

QToolTip {{
    background: {c['card']}; color: {c['text']};
    border: 1px solid {c['accent_dim']}; border-radius: 6px; padding: 5px 8px;
}}

QMenu {{
    background: {c['card']}; border: 1px solid {c['border_hi']};
    border-radius: 8px; padding: 5px;
}}
QMenu::item {{ padding: 6px 22px; border-radius: 6px; color: {c['text_dim']}; }}
QMenu::item:selected {{ background: {c['accent_dim']}; color: #FFFFFF; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

QFrame[role="hline"] {{ background: {c['border']}; max-height: 1px; border: none; }}

#Badge {{
    border-radius: 9px; padding: 2px 10px; font-size: 12.5px; font-weight: 600;
}}
#Badge[demo="true"]  {{ background: #3A2E12; color: {c['warn']};
                        border: 1px solid #6B5312; }}
#Badge[demo="false"] {{ background: #10322A; color: {c['ok']};
                        border: 1px solid #1C5E4A; }}
"""


                                                                            
                              
                                                                            
def _mpl_cjk_families() -> list[str]:
                                  

                                                            
                                                   
                                           
                                        
       
    from matplotlib import font_manager

    for fam in ("SimSun", "Microsoft YaHei", "SimHei"):
        try:
            font_manager.findfont(font_manager.FontProperties(family=fam),
                                  fallback_to_default=False)
                                                  
            return [fam, "DejaVu Sans"]
        except Exception:                                                
            continue
    return ["Microsoft YaHei", "SimHei", "DejaVu Sans"]


def apply_mpl_theme() -> None:
                                           
    import matplotlib
    matplotlib.rcParams.update({
        "figure.facecolor": C["card"],
        "axes.facecolor": C["card"],
        "savefig.facecolor": C["card"],
        "axes.edgecolor": C["border"],
        "axes.labelcolor": C["text_dim"],
        "axes.titlecolor": C["text"],
        "text.color": C["text"],
        "xtick.color": C["text_muted"],
        "ytick.color": C["text_muted"],
        "grid.color": C["border"],
        "grid.alpha": 0.55,
        "axes.grid": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 9,
        "axes.titlesize": 10.5,
        "legend.frameon": False,
        "legend.labelcolor": C["text_dim"],
        "figure.autolayout": True,
        "font.sans-serif": _mpl_cjk_families(),
                                                  
                                                 
        "axes.unicode_minus": False,
    })
