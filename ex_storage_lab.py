"""EX STORAGE LAB - frees up storage, but only deletes what YOU tick and confirm.
©2026 EX Inc./HYPERION DIGITAL ©2026"""
import json, os, re, ssl, sys, threading, time, urllib.error, urllib.request

APP_NAME = "EX STORAGE LAB"
APP_VERSION = "1.0.0"
REPO = "Teobokki/ex-storage-lab"
LATEST_URL = "https://raw.githubusercontent.com/%s/main/latest.json" % REPO
RELEASES_URL = "https://github.com/%s/releases/latest" % REPO
COPYRIGHT = "\u00a92026 EX Inc./HYPERION DIGITAL \u00a92026"

if os.name == "nt":                         # per-monitor DPI awareness before any window exists (Qt also does this)
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))     # PER_MONITOR_AWARE_V2
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("EXInc.EXStorageLab")
    except Exception:
        pass

from PySide6.QtCore import Qt, Signal, QObject, QTimer, QUrl, QSize
from PySide6.QtGui import QIcon, QPixmap, QFont, QDesktopServices, QGuiApplication, QColor, QBrush
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
                               QProgressBar, QTreeWidget, QTreeWidgetItem, QHeaderView, QDialog, QRadioButton, QButtonGroup,
                               QPlainTextEdit, QSpinBox, QMessageBox, QScrollArea, QSplitter, QSizePolicy, QAbstractItemView, QCheckBox)
import storage_core as core

BG, PANEL, PANEL2, LINE, TEXT, MUTED = "#2c313b", "#353a46", "#3d4351", "#4a5263", "#e9eef5", "#9ba7b9"
TEAL, BLUE, VIOLET, WARN, RED = "#52e0b6", "#4f9de8", "#8b7cf2", "#f0c46a", "#ef7a7a"
GRAD = "qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 %s, stop:0.55 %s, stop:1 %s)" % (TEAL, BLUE, VIOLET)


def res(*p):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *p)


def data_dir():
    d = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), APP_NAME)
    os.makedirs(os.path.join(d, "logs"), exist_ok=True)
    return d


QSS = """
* { color:%(TEXT)s; font-family:'Segoe UI','Noto Sans','DejaVu Sans'; font-size:10pt; }
QMainWindow, QDialog { background:%(BG)s; }
QFrame#panel { background:%(PANEL)s; border:1px solid %(LINE)s; border-radius:10px; }
QLabel#title { font-size:19pt; font-weight:800; letter-spacing:1px; }
QLabel#h2 { font-size:9pt; font-weight:800; letter-spacing:2px; color:%(TEAL)s; }
QLabel#muted { color:%(MUTED)s; }
QLabel#big { font-size:15pt; font-weight:800; }
QPushButton { background:%(PANEL2)s; border:1px solid %(LINE)s; border-radius:8px; padding:7px 16px; font-weight:600; }
QPushButton:hover { border-color:%(BLUE)s; }
QPushButton:disabled { color:#6f7889; border-color:#424857; }
QPushButton#primary { background:%(GRAD)s; color:#10202a; border:none; font-weight:800; padding:9px 22px; }
QPushButton#primary:disabled { background:#475062; color:#8a93a3; }
QPushButton#danger { background:#a84b55; border:none; font-weight:800; padding:9px 22px; }
QProgressBar { background:#262a33; border:1px solid %(LINE)s; border-radius:6px; text-align:center; color:transparent; }
QProgressBar::chunk { background:%(GRAD)s; border-radius:5px; }
QTreeWidget { background:%(PANEL)s; alternate-background-color:#393f4c; border:1px solid %(LINE)s; border-radius:8px; }
QTreeWidget::item { padding:4px 2px; }
QTreeWidget::item:selected { background:#44506a; }
QHeaderView::section { background:%(PANEL2)s; color:%(MUTED)s; border:none; border-bottom:1px solid %(LINE)s; padding:6px; font-weight:700; }
QPlainTextEdit { background:#262a33; border:1px solid %(LINE)s; border-radius:8px; font-family:Consolas,'DejaVu Sans Mono',monospace; font-size:9pt; }
QSpinBox { background:#262a33; border:1px solid %(LINE)s; border-radius:6px; padding:4px 6px; }
QRadioButton, QCheckBox { spacing:8px; }
QScrollBar:vertical { background:transparent; width:12px; } QScrollBar::handle:vertical { background:#566074; border-radius:5px; min-height:30px; }
QScrollBar:horizontal { background:transparent; height:12px; } QScrollBar::handle:horizontal { background:#566074; border-radius:5px; min-width:30px; }
QScrollBar::add-line, QScrollBar::sub-line { height:0; width:0; }
QScrollBar::add-page, QScrollBar::sub-page { background:transparent; }
QAbstractScrollArea::corner { background:transparent; }
QScrollArea { background:transparent; border:none; } QScrollArea > QWidget > QWidget { background:transparent; }
QSplitter::handle { background:transparent; }
QTreeWidget::indicator, QCheckBox::indicator { width:16px; height:16px; }
QTreeWidget::indicator:unchecked, QCheckBox::indicator:unchecked { image:url(%(CB_OFF)s); }
QTreeWidget::indicator:checked, QCheckBox::indicator:checked { image:url(%(CB_ON)s); }
QTreeWidget::indicator:indeterminate { image:url(%(CB_PART)s); }
""" % dict(TEXT=TEXT, BG=BG, PANEL=PANEL, PANEL2=PANEL2, LINE=LINE, TEAL=TEAL, MUTED=MUTED, BLUE=BLUE, GRAD=GRAD,
           CB_OFF="{CB_OFF}", CB_ON="{CB_ON}", CB_PART="{CB_PART}")


def lbl(text, name=None, wrap=False):
    l = QLabel(text)
    if name:
        l.setObjectName(name)
    l.setWordWrap(wrap)
    return l


def panel():
    f = QFrame(); f.setObjectName("panel"); return f


_DIRS = None


def short_path(text):
    """replace the user's folders with %LOCALAPPDATA% / %APPDATA% / %USERPROFILE% in a path or log line"""
    global _DIRS
    if _DIRS is None:
        d = core.user_dirs(); _DIRS = [(d[k], n) for k, n in (("local", "%LOCALAPPDATA%"), ("roaming", "%APPDATA%"), ("home", "%USERPROFILE%")) if d.get(k)]
    for root, name in _DIRS:
        text = re.sub(re.escape(root) + r"(?=[\\/]|$|\s|:)", lambda m: name, text, flags=re.I)
    return text


def plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def fmt_date(t):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(t)) if t else ""


# ---------------------------------------------------------------- update check (verifying TLS, never CERT_NONE)
def _fallback_context():
    """certifi's bundle PLUS every Windows ROOT/CA certificate. Always verifying (CERT_REQUIRED + hostname check)."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    try:
        import certifi
        ctx.load_verify_locations(cafile=certifi.where())
    except Exception:
        ctx.load_default_certs()
    if hasattr(ssl, "enum_certificates"):
        for store in ("ROOT", "CA"):
            try:
                for der, enc, trust in ssl.enum_certificates(store):
                    if enc == "x509_asn" and (trust is True or "1.3.6.1.5.5.7.3.1" in trust):
                        try:
                            ctx.load_verify_locations(cadata=der)
                        except Exception:
                            pass
            except Exception:
                pass
    return ctx


_INJECTED = False


def _truststore_context():
    """the Windows certificate store via truststore (works behind antivirus / proxy HTTPS scanning)"""
    global _INJECTED
    import truststore
    if not _INJECTED:
        truststore.inject_into_ssl(); _INJECTED = True
    return ssl.create_default_context()


def fetch_latest():
    req = urllib.request.Request(LATEST_URL + "?t=%d" % time.time(), headers={"User-Agent": "%s/%s" % (APP_NAME, APP_VERSION), "Cache-Control": "no-cache"})
    errors = []
    for make in (_truststore_context, _fallback_context):
        try:
            ctx = make()
        except Exception as e:
            errors.append(str(e)); continue
        try:
            with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                return json.loads(r.read().decode("utf-8"))
        except (ssl.SSLError, urllib.error.URLError) as e:
            if isinstance(e, urllib.error.HTTPError):
                raise
            errors.append(str(e))
    raise RuntimeError("; ".join(errors) or "no connection")


def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:4]) + (0,) * (4 - len(re.findall(r"\d+", str(v))[:4]))


class Bridge(QObject):
    scan_progress = Signal(str)
    scan_done = Signal(list)
    del_progress = Signal(float, str)
    del_done = Signal(object)
    update_done = Signal(object, str)


# ---------------------------------------------------------------- drive bars
class DriveRow(QWidget):
    def __init__(self, name, total, used, free):
        super().__init__()
        h = QHBoxLayout(self); h.setContentsMargins(0, 2, 0, 2); h.setSpacing(12)
        n = lbl(name); n.setMinimumWidth(150); n.setStyleSheet("font-weight:700"); h.addWidget(n)
        bar = QProgressBar(); bar.setRange(0, 1000); bar.setValue(int(used / total * 1000) if total else 0); bar.setFixedHeight(14)
        if total and used / total > 0.9:
            bar.setStyleSheet("QProgressBar::chunk{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 %s,stop:1 %s);border-radius:5px}" % (WARN, RED))
        h.addWidget(bar, 1)
        t = lbl("%s used of %s  \u00b7  %s free" % (core.human(used), core.human(total), core.human(free)), "muted"); t.setMinimumWidth(250)
        h.addWidget(t)


# ---------------------------------------------------------------- dialogs
class ConfirmDialog(QDialog):
    def __init__(self, parent, chosen):
        super().__init__(parent)
        self.setWindowTitle("Confirm - %s" % APP_NAME); self.setModal(True)
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(860, int(scr.width() * 0.8)), min(640, int(scr.height() * 0.8)))
        v = QVBoxLayout(self); v.setContentsMargins(22, 20, 22, 18); v.setSpacing(10)
        total = sum(i.size for c, i in chosen)
        v.addWidget(lbl("CONFIRM WHAT WILL BE REMOVED", "h2"))
        v.addWidget(lbl("%d item(s)  \u00b7  %s" % (len(chosen), core.human(total)), "big"))
        v.addWidget(lbl("This is the exact list. Nothing else will be touched. Files that are in use are skipped.", "muted", True))
        box = QPlainTextEdit(); box.setReadOnly(True); box.setLineWrapMode(QPlainTextEdit.NoWrap)
        lines = []
        for c, i in chosen:
            extra = ("   (folder, %s)" % plural(i.count, "file")) if i.kind == "folder" else ""
            what = short_path(i.path) if i.kind != "recyclebin" else "Recycle Bin - " + i.note
            lines.append("%10s   %-28s %s%s" % (core.human(i.size), c.title[:28], what, extra))
        box.setPlainText("\n".join(lines)); v.addWidget(box, 1)
        warn = []
        if any(c.risk == "personal" for c, i in chosen):
            warn.append("You ticked some of YOUR OWN files (Large files / Duplicates). Make sure you don't need them.")
        groups = {}
        for c, i in chosen:
            if c.id == "dupes":
                groups.setdefault(i.group, 0); groups[i.group] += 1
        dupe_cat = next((c for c, i in chosen if c.id == "dupes"), None)
        if dupe_cat:
            full = [g for g, n in groups.items() if n >= sum(1 for x in dupe_cat.items if x.group == g)]
            if full:
                warn.append("Warning: you ticked EVERY copy in %d duplicate group(s) - no copy of those files would be kept." % len(full))
        if any(c.permanent_only for c, i in chosen):
            warn.append("Emptying the Recycle Bin is always permanent.")
        for w in warn:
            l = lbl("\u26a0  " + w, None, True); l.setStyleSheet("color:%s;font-weight:600" % WARN); v.addWidget(l)
        v.addWidget(lbl("HOW SHOULD THEY BE REMOVED?", "h2"))
        self.rb_recycle = QRadioButton("Move to Recycle Bin  (recommended - you can restore them later)")
        self.rb_perm = QRadioButton("Delete permanently  (frees the space right away, cannot be undone)")
        self.rb_recycle.setChecked(True)
        grp = QButtonGroup(self); grp.addButton(self.rb_recycle); grp.addButton(self.rb_perm)
        v.addWidget(self.rb_recycle); v.addWidget(self.rb_perm)
        self.rb_perm.toggled.connect(self._mode)
        row = QHBoxLayout(); row.addStretch(1)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject); row.addWidget(cancel)
        self.go = QPushButton("Move %d item(s) to Recycle Bin" % len(chosen)); self.go.setObjectName("primary"); self.go.clicked.connect(self.accept)
        self.n = len(chosen); row.addWidget(self.go); v.addLayout(row)
        cancel.setDefault(True); cancel.setFocus()

    def _mode(self, perm):
        self.go.setText(("Delete %d item(s) permanently" if perm else "Move %d item(s) to Recycle Bin") % self.n)
        self.go.setObjectName("danger" if perm else "primary"); self.go.style().unpolish(self.go); self.go.style().polish(self.go)

    @property
    def recycle(self):
        return self.rb_recycle.isChecked()


class ResultDialog(QDialog):
    def __init__(self, parent, r, recycle, logfile):
        super().__init__(parent)
        self.setWindowTitle("Done - %s" % APP_NAME)
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(820, int(scr.width() * 0.8)), min(560, int(scr.height() * 0.8)))
        v = QVBoxLayout(self); v.setContentsMargins(22, 20, 22, 18); v.setSpacing(10)
        v.addWidget(lbl("CLEAN-UP COMPLETE", "h2"))
        t = lbl("%s freed" % core.human(r.freed), "title"); v.addWidget(t)
        v.addWidget(lbl("%s %s  \u00b7  %d skipped (in use or locked)  \u00b7  %d refused (protected)" % (
            plural(r.removed, "file"), "moved to the Recycle Bin" if recycle else "deleted permanently", len(r.skipped), len(r.refused)), "muted", True))
        if recycle and r.freed:
            v.addWidget(lbl("Space moved to the Recycle Bin is freed on disk only after you empty the Recycle Bin.", "muted", True))
        log = QPlainTextEdit(); log.setReadOnly(True); log.setLineWrapMode(QPlainTextEdit.NoWrap)
        log.setPlainText(short_path("\n".join(r.log + (["", "Skipped:"] + ["  %s - %s" % s for s in r.skipped[:500]] if r.skipped else []))))
        v.addWidget(log, 1)
        row = QHBoxLayout(); v.addLayout(row)
        o = QPushButton("Open log file"); o.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(logfile))); row.addWidget(o)
        row.addStretch(1)
        ok = QPushButton("OK"); ok.setObjectName("primary"); ok.clicked.connect(self.accept); row.addWidget(ok)


# ---------------------------------------------------------------- main window
CAT_ORDER = ["temp", "recycle", "browser", "system", "apps", "installers", "large", "dupes"]


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("%s %s" % (APP_NAME, APP_VERSION)); self.setWindowIcon(QIcon(res("assets", "logo.ico")))
        self.b = Bridge(); self.cats = []; self.busy = False; self._cancel = False; self._syncing = False
        self.b.scan_progress.connect(self.on_scan_progress); self.b.scan_done.connect(self.on_scan_done)
        self.b.del_progress.connect(self.on_del_progress); self.b.del_done.connect(self.on_del_done)
        self.b.update_done.connect(self.on_update_done)
        self.logfile = os.path.join(data_dir(), "logs", time.strftime("clean-%Y%m%d-%H%M%S.log"))
        root = QWidget(); self.setCentralWidget(root)
        v = QVBoxLayout(root); v.setContentsMargins(18, 14, 18, 10); v.setSpacing(10)

        # header
        hd = QHBoxLayout(); hd.setSpacing(14)
        logo = QLabel(); logo.setPixmap(QPixmap(res("assets", "logo256.png")).scaled(58, 58, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        hd.addWidget(logo)
        tc = QVBoxLayout(); tc.setSpacing(0)
        tc.addWidget(lbl(APP_NAME, "title"))
        tc.addWidget(lbl("Free up space safely - you choose exactly what gets removed.", "muted"))
        hd.addLayout(tc, 1)
        self.upd = QPushButton("Check for updates"); self.upd.clicked.connect(self.check_updates); hd.addWidget(self.upd)
        v.addLayout(hd)

        # drives
        dp = panel(); dl = QVBoxLayout(dp); dl.setContentsMargins(16, 12, 16, 12); dl.setSpacing(4)
        top = QHBoxLayout(); top.addWidget(lbl("DRIVES", "h2")); top.addStretch(1)
        rf = QPushButton("Refresh"); rf.clicked.connect(self.load_drives); top.addWidget(rf); dl.addLayout(top)
        dw = QWidget(); self.drive_box = QVBoxLayout(dw); self.drive_box.setContentsMargins(0, 0, 6, 0); self.drive_box.setSpacing(2)
        self.drive_scroll = QScrollArea(); self.drive_scroll.setWidget(dw); self.drive_scroll.setWidgetResizable(True)
        self.drive_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.drive_scroll.setFrameShape(QFrame.NoFrame)
        dl.addWidget(self.drive_scroll)
        v.addWidget(dp)

        # scan bar
        sp = panel(); sl = QHBoxLayout(sp); sl.setContentsMargins(16, 10, 16, 10); sl.setSpacing(12)
        self.scan_btn = QPushButton("Scan for reclaimable space"); self.scan_btn.setObjectName("primary"); self.scan_btn.clicked.connect(self.scan)
        sl.addWidget(self.scan_btn)
        sl.addWidget(lbl("Large files from", "muted"))
        self.min_mb = QSpinBox(); self.min_mb.setRange(50, 100000); self.min_mb.setSingleStep(50); self.min_mb.setValue(500); self.min_mb.setSuffix(" MB")
        sl.addWidget(self.min_mb)
        self.scan_info = lbl("Nothing is selected or deleted until you tick it and confirm.", "muted", True); self.scan_info.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        sl.addWidget(self.scan_info, 1)
        self.stop_btn = QPushButton("Stop"); self.stop_btn.clicked.connect(self.stop); self.stop_btn.hide(); sl.addWidget(self.stop_btn)
        v.addWidget(sp)
        self.bar = QProgressBar(); self.bar.setFixedHeight(6); self.bar.setRange(0, 0); self.bar.hide(); v.addWidget(self.bar)

        # results + log
        split = QSplitter(Qt.Vertical); split.setChildrenCollapsible(False)
        self.tree = QTreeWidget(); self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(["What can be removed", "Size", "Files", "Date", "Location"])
        self.tree.setAlternatingRowColors(True); self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QAbstractItemView.NoSelection)
        h = self.tree.header(); h.setStretchLastSection(True); h.setSectionResizeMode(0, QHeaderView.Interactive)
        for c in (1, 2, 3):
            h.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.Stretch)
        self.tree.itemChanged.connect(self.on_item_changed)
        self.tree.setMinimumHeight(160)
        split.addWidget(self.tree)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(5000); self.log.setMinimumHeight(60)
        split.addWidget(self.log); split.setStretchFactor(0, 5); split.setStretchFactor(1, 1)
        v.addWidget(split, 1)

        # footer
        ft = QHBoxLayout(); ft.setSpacing(12)
        self.sel_lbl = lbl("Selected: nothing", "big"); ft.addWidget(self.sel_lbl)
        ft.addStretch(1)
        self.log_btn = QPushButton("Hide log"); self.log_btn.clicked.connect(lambda: self.show_log(not self.log.isVisible())); ft.addWidget(self.log_btn)
        self.none_btn = QPushButton("Untick all"); self.none_btn.clicked.connect(self.untick_all); ft.addWidget(self.none_btn)
        self.clean_btn = QPushButton("Review && remove selected\u2026"); self.clean_btn.setObjectName("primary"); self.clean_btn.setEnabled(False)
        self.clean_btn.clicked.connect(self.clean); ft.addWidget(self.clean_btn)
        v.addLayout(ft)
        cp = lbl("%s  \u00b7  v%s" % (COPYRIGHT, APP_VERSION), "muted"); cp.setStyleSheet("font-size:8pt;color:%s" % MUTED); v.addWidget(cp, 0, Qt.AlignRight)

        self.load_drives()
        g = (self.screen() or QGuiApplication.primaryScreen()).availableGeometry()
        if g.height() < 760:                     # small laptop screens: give the list the room, log on demand
            self.show_log(False)
        self.add_log("%s %s started. Log file: %s" % (APP_NAME, APP_VERSION, self.logfile))
        self.fit_to_screen()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.tree.setColumnWidth(0, max(260, int(self.tree.viewport().width() * 0.42)))

    def fit_to_screen(self):
        g = (self.screen() or QGuiApplication.primaryScreen()).availableGeometry()
        w, h = min(1240, int(g.width() * 0.92)), min(860, int(g.height() * 0.90))
        self.setMinimumSize(min(780, g.width() - 40), min(520, g.height() - 60))
        self.resize(w, h); self.move(g.x() + (g.width() - w) // 2, g.y() + (g.height() - h) // 2)

    # ---- log
    def show_log(self, on):
        self.log.setVisible(on); self.log_btn.setText("Hide log" if on else "Show log")

    def add_log(self, s):
        line = time.strftime("%H:%M:%S ") + s
        self.log.appendPlainText(short_path(line))
        try:
            with open(self.logfile, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    # ---- drives
    def load_drives(self):
        while self.drive_box.count():
            w = self.drive_box.takeAt(0).widget()
            if w:
                w.deleteLater()
        ds = core.drives()
        for d in ds:
            self.drive_box.addWidget(DriveRow(*d))
        g = (self.screen() or QGuiApplication.primaryScreen()).availableGeometry()
        rows = min(len(ds), 2 if g.height() < 700 else (3 if g.height() < 900 else 5))     # small laptop screens: scroll the rest
        self.drive_scroll.setFixedHeight(rows * max(self.fontMetrics().height() + 12, 26) + 4)

    # ---- scan
    def set_busy(self, on, text=""):
        self.busy = on; self.bar.setVisible(on); self.stop_btn.setVisible(on)
        self.scan_btn.setEnabled(not on); self.clean_btn.setEnabled(not on and bool(self.chosen())); self.min_mb.setEnabled(not on)
        if text:
            self.scan_info.setText(text)

    def stop(self):
        self._cancel = True

    def scan(self):
        self._cancel = False; self.tree.clear(); self.cats = []; self.update_sel()
        self.set_busy(True, "Scanning\u2026"); self.add_log("Scan started (large files from %d MB)." % self.min_mb.value())
        mb = self.min_mb.value()

        def run():
            s = core.Scanner(cancel=lambda: self._cancel, progress=self.b.scan_progress.emit)
            out = []
            for fn in (s.temp, s.recycle, s.browsers, s.windows, s.app_caches, s.installers, lambda: s.large(mb), s.duplicates):
                if self._cancel:
                    break
                try:
                    out.append(fn())
                except Exception as e:
                    self.b.scan_progress.emit("Scan step failed: %s" % e)
            self.b.scan_done.emit(out)
        threading.Thread(target=run, daemon=True).start()

    def on_scan_progress(self, t):
        self.scan_info.setText(t)
        if t.startswith("Scan step failed"):
            self.add_log(t)

    def on_scan_done(self, cats):
        self.cats = cats; self._syncing = True
        total = 0
        for c in cats:
            it = QTreeWidgetItem([c.title, core.human(c.size) if c.items else "-", str(sum(i.count for i in c.items)) if c.items else "", "", ""])
            it.setData(0, Qt.UserRole, ("cat", c))
            it.setToolTip(0, c.desc)
            f = it.font(0); f.setBold(True); it.setFont(0, f); it.setFont(1, f)
            it.setFirstColumnSpanned(False)
            if c.items:
                it.setFlags((it.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsAutoTristate)
                it.setCheckState(0, Qt.Unchecked)
            else:
                it.setFlags(it.flags() & ~Qt.ItemIsUserCheckable)
                it.setForeground(0, QBrush(QColor(MUTED)))
                it.setText(0, c.title + ("  -  " + c.error if c.error else "  -  nothing found"))
            if c.risk == "personal":
                it.setForeground(0, QBrush(QColor(WARN)))
            self.tree.addTopLevelItem(it)
            sub = QTreeWidgetItem([c.desc]); sub.setFlags(Qt.ItemIsEnabled); sub.setForeground(0, QBrush(QColor(MUTED)))
            it.addChild(sub); sub.setFirstColumnSpanned(True)
            for i in c.items[:5000]:
                if i.kind == "recyclebin":
                    name, loc = "Recycle Bin  -  " + i.note, "all drives"
                elif i.kind == "folder" and i.note:
                    name, loc = i.note, self.short(i.path)
                else:
                    name, loc = os.path.basename(i.path) or i.path, self.short(os.path.dirname(i.path))
                    if c.id == "dupes":
                        name = "[%s]  %s" % (i.note, name)
                ch = QTreeWidgetItem([name, core.human(i.size), str(i.count), fmt_date(i.mtime) if i.kind != "recyclebin" else "", loc])
                ch.setFlags((ch.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsAutoTristate); ch.setCheckState(0, Qt.Unchecked)
                ch.setData(0, Qt.UserRole, ("item", i)); ch.setToolTip(0, i.path); ch.setToolTip(4, i.path)
                it.addChild(ch)
            total += c.size
        self.tree.setColumnWidth(0, max(260, int(self.tree.viewport().width() * 0.42)))
        self._syncing = False
        self.set_busy(False, ("Found %s you could free in %d categories. Tick what you want removed - expand a category to pick individual files."
                              % (core.human(total), sum(1 for c in cats if c.items))) if not self._cancel else "Scan stopped.")
        self.add_log("Scan finished: %s reclaimable. " % core.human(total) + ", ".join("%s %s" % (c.title, core.human(c.size)) for c in cats))
        self.update_sel()

    # ---- selection
    def short(self, p):
        return short_path(p)

    def on_item_changed(self, item, col):
        if self._syncing or col != 0:
            return
        d = item.data(0, Qt.UserRole)
        if not d:
            return
        self._syncing = True
        try:
            if d[0] == "cat":                              # whole category ticked / unticked
                on = item.checkState(0) != Qt.Unchecked
                item.setCheckState(0, Qt.Checked if on else Qt.Unchecked)
                for k in range(item.childCount()):
                    ch = item.child(k); cd = ch.data(0, Qt.UserRole)
                    if cd:
                        ch.setCheckState(0, Qt.Checked if on else Qt.Unchecked); cd[1].selected = on
                for i in d[1].items[5000:]:
                    i.selected = on
            else:                                          # one file / folder
                d[1].selected = item.checkState(0) == Qt.Checked
                par = item.parent(); pc = par.data(0, Qt.UserRole)[1]
                n = sum(1 for i in pc.items if i.selected)
                par.setCheckState(0, Qt.Unchecked if n == 0 else (Qt.Checked if n == len(pc.items) else Qt.PartiallyChecked))
        finally:
            self._syncing = False
        self.update_sel()

    def chosen(self):
        """ticked items, each path once (a big installer can show up in two categories)"""
        out, seen = [], set()
        for c in self.cats:
            for i in c.items:
                k = os.path.normcase(i.path)
                if i.selected and k not in seen:
                    seen.add(k); out.append((c, i))
        return out

    def update_sel(self):
        ch = self.chosen()
        self.sel_lbl.setText("Selected: %s  (%d item%s)" % (core.human(sum(i.size for c, i in ch)), len(ch), "" if len(ch) == 1 else "s") if ch else "Selected: nothing")
        self.clean_btn.setEnabled(bool(ch) and not self.busy)

    def untick_all(self):
        for k in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(k)
            if it.flags() & Qt.ItemIsUserCheckable:
                self._syncing = True
                it.setCheckState(0, Qt.Unchecked)
                for j in range(it.childCount()):
                    if it.child(j).data(0, Qt.UserRole):
                        it.child(j).setCheckState(0, Qt.Unchecked)
                self._syncing = False
        for c in self.cats:
            for i in c.items:
                i.selected = False
        self.update_sel()

    # ---- clean
    def clean(self):
        ch = self.chosen()
        if not ch:
            return
        dlg = ConfirmDialog(self, ch)
        self._dlg = dlg
        if dlg.exec() != QDialog.Accepted:
            self.add_log("Clean-up cancelled - nothing was removed."); return
        self.run_delete(ch, dlg.recycle)

    def run_delete(self, ch, recycle):
        self._cancel = False; self.set_busy(True, "Removing\u2026"); self.bar.setRange(0, 1000)
        self.add_log("Removing %d item(s) - %s." % (len(ch), "Recycle Bin" if recycle else "permanent"))
        self._recycle = recycle; items = [i for c, i in ch]

        def run():
            try:
                r = core.delete(items, recycle=recycle, progress=self.b.del_progress.emit, cancel=lambda: self._cancel)
            except Exception as e:
                r = core.Result(); r.add_log("ERROR: %s" % e)
            self.b.del_done.emit(r)
        threading.Thread(target=run, daemon=True).start()

    def on_del_progress(self, f, path):
        self.bar.setValue(int(f * 1000)); self.scan_info.setText(path)

    def on_del_done(self, r):
        self.bar.setRange(0, 0); self.set_busy(False, "Freed %s." % core.human(r.freed))
        for line in r.log:
            self.add_log(line[9:])
        for p, why in r.skipped[:200]:
            self.add_log("Skipped: %s (%s)" % (p, why))
        self.load_drives()
        dlg = ResultDialog(self, r, self._recycle, self.logfile); self._res = dlg
        if os.environ.get("EXSL_SHOTS"):
            dlg.show(); self.after_result(dlg)
        else:
            dlg.exec()
        self.scan()

    def after_result(self, dlg):
        pass

    # ---- updates
    def check_updates(self):
        self.upd.setEnabled(False); self.upd.setText("Checking\u2026")

        def run():
            try:
                self.b.update_done.emit(fetch_latest(), "")
            except Exception as e:
                self.b.update_done.emit(None, str(e))
        threading.Thread(target=run, daemon=True).start()

    def on_update_done(self, lj, err):
        self.upd.setEnabled(True); self.upd.setText("Check for updates")
        if err or not isinstance(lj, dict):
            self.add_log("Update check failed: %s" % err)
            QMessageBox.warning(self, APP_NAME, "Could not check for updates right now.\n\n%s" % err); return
        latest = str(lj.get("version", "0"))
        if vtuple(latest) > vtuple(APP_VERSION):
            self.add_log("Update available: %s" % latest)
            m = QMessageBox(self); m.setWindowTitle(APP_NAME); m.setIcon(QMessageBox.Information)
            m.setText("EX STORAGE LAB %s is available (you have %s)." % (latest, APP_VERSION))
            m.setInformativeText(lj.get("notes", ""))
            get = m.addButton("Download update", QMessageBox.AcceptRole); m.addButton("Later", QMessageBox.RejectRole)
            m.exec()
            if m.clickedButton() is get:
                url = lj.get("installer_url") or lj.get("url") or lj.get("release_url") or RELEASES_URL
                if str(url).startswith("https://github.com/Teobokki/"):
                    QDesktopServices.openUrl(QUrl(url))
        else:
            self.add_log("Up to date (%s)." % APP_VERSION)
            QMessageBox.information(self, APP_NAME, "You have the latest version (%s)." % APP_VERSION)


def main():
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv); app.setApplicationName(APP_NAME); app.setStyle("Fusion")
    app.setWindowIcon(QIcon(res("assets", "logo.ico"))); app.setStyleSheet(QSS.replace("{CB_OFF}", res("assets", "cb_off.png").replace("\\", "/"))
                      .replace("{CB_ON}", res("assets", "cb_on.png").replace("\\", "/")).replace("{CB_PART}", res("assets", "cb_part.png").replace("\\", "/")))
    w = Main(); w.show()
    if os.environ.get("EXSL_SHOTS"):           # developer screenshot run (tests/shots.py is not part of the build)
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"))
        import shots
        shots.run(app, w)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
