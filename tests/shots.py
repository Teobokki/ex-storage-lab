"""Screenshot run under Wine/Xvfb (EXSL_SHOTS=<dir>): fake profile, real scan, user-style ticks, confirm, recycle, result.
©2026 EX Inc./HYPERION DIGITAL ©2026"""
import os
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QDialog


def run(app, w):
    out = os.environ["EXSL_SHOTS"]; os.makedirs(out, exist_ok=True)
    seq = []

    def grab(widget, name):
        app.processEvents(); widget.grab().save(os.path.join(out, name)); print("SHOT", name, flush=True)

    def start():
        g = w.screen().availableGeometry(); print("SCREEN", g.width(), g.height(), "DPR", w.devicePixelRatioF(), "WIN", w.width(), w.height(), flush=True)
        grab(w, "shot_start.png")
        w.min_mb.setValue(500)
        w.b.scan_done.connect(lambda cats: QTimer.singleShot(600, after_scan))
        w.scan()

    def after_scan():
        if seq:
            return
        seq.append(1)
        t = w.tree
        for k in range(t.topLevelItemCount()):
            top = t.topLevelItem(k); cat = top.data(0, Qt.UserRole)[1]
            if cat.id in ("temp", "browser"):
                top.setCheckState(0, Qt.Checked)
            if cat.id in ("browser", "large"):
                top.setExpanded(True)
            if cat.id == "large":
                for j in range(top.childCount()):
                    ch = top.child(j); d = ch.data(0, Qt.UserRole)
                    if d and d[1].path.endswith("project_backup_old.7z"):
                        ch.setCheckState(0, Qt.Checked)
        t.scrollToTop()
        def second():
            for k in range(t.topLevelItemCount()):
                top = t.topLevelItem(k); cid = top.data(0, Qt.UserRole)[1].id
                top.setExpanded(cid in ("large", "dupes", "installers"))
            last = t.topLevelItem(t.topLevelItemCount() - 1)
            t.scrollToItem(last.child(last.childCount() - 1))
            QTimer.singleShot(400, lambda: (grab(w, "shot_files.png"), QTimer.singleShot(300, confirm)))
        QTimer.singleShot(500, lambda: (grab(w, "shot_scan.png"), QTimer.singleShot(300, second)))

    def confirm():
        def snap():
            dlg = getattr(w, "_dlg", None)
            if dlg is None:
                print("NO CONFIRM DIALOG", flush=True); app.quit(); return
            grab(dlg, "shot_confirm.png")
            dlg.accept()
        QTimer.singleShot(900, snap)
        w.clean()

    def after_result(dlg):
        QTimer.singleShot(900, lambda: (grab(dlg, "shot_result.png"), QTimer.singleShot(300, app.quit)))
    w.after_result = after_result
    QTimer.singleShot(1500, start)
    QTimer.singleShot(150000, app.quit)        # safety net
