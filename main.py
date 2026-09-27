                                 

     
                                       

                                             
                              

       
                                        
                                                   
                                 
   

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bridge_inspect import config as cfg                      
from bridge_inspect import db, theme                          


def main() -> int:
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName(cfg.APP_NAME)
    app.setApplicationVersion(cfg.APP_VERSION)

                                              
    theme.apply_app_font(app)
    app.setStyleSheet(theme.build_qss())

    db.connect()
    db.ensure_default_user()

                            
    while True:
        from bridge_inspect.ui.login import LoginWindow

        login = LoginWindow()
        if not login.exec():
            return 0

        from bridge_inspect.ui.main_window import MainWindow

        win = MainWindow(login.user)
        win.show()
        app.exec()
        if not getattr(win, "logged_out", False):
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
