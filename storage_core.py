"""EX STORAGE LAB - scanning and deleting engine (no UI).

Rules this module enforces on every path, whatever the UI asks for:
  * only paths inside the current user's own folders are ever touched (profile, %TEMP%, %LOCALAPPDATA%, Downloads...);
  * Windows, Program Files, ProgramData and the system drive root are always refused;
  * nothing is deleted unless delete() is called with an explicit list of items the user ticked;
  * files that are in use / locked / need admin are skipped and reported, never forced.
©2026 EX Inc./HYPERION DIGITAL ©2026"""
import ctypes, hashlib, os, re, shutil, stat, string, sys, time

IS_WIN = os.name == "nt"
APP = "EX STORAGE LAB"

# names that must never be shown by this app (store policy) - matched per path component / whole word
_BLOCK_WORDS = re.compile(r"(minecraft|steam|gta|photoshop|adobe|call[ _.-]?of[ _.-]?duty)", re.I)
_BLOCK_COD = re.compile(r"(^|[^a-z0-9])cod([^a-z0-9]|$)", re.I)


def hidden_name(path):
    p = path.replace("\\", "/")
    return bool(_BLOCK_WORDS.search(p) or _BLOCK_COD.search(p))


# ---------------------------------------------------------------- environment / safety
def env(name, default=""):
    v = os.environ.get(name) or default
    return os.path.normpath(v) if v else ""


def user_dirs():
    home = env("USERPROFILE") or os.path.expanduser("~")
    local = env("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
    roaming = env("APPDATA") or os.path.join(home, "AppData", "Roaming")
    temp = env("TEMP") or env("TMP") or os.path.join(local, "Temp")
    known = {k: known_folder(k, os.path.join(home, k)) for k in ("Downloads", "Desktop", "Documents", "Videos", "Music", "Pictures")}
    return {"home": home, "local": local, "roaming": roaming, "temp": temp, **known}


_KF = {"Downloads": "{374DE290-123F-4565-9164-39C4925E467B}", "Desktop": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
       "Documents": "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}", "Videos": "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}",
       "Music": "{4BD8D571-6D19-48D3-BE97-422220080E43}", "Pictures": "{33E28130-4E1E-4676-835A-98395C3BC3BB}"}


def known_folder(name, fallback):
    """real location of Downloads/Documents/... (they can be moved, e.g. to OneDrive)"""
    if IS_WIN and not os.environ.get("EXSL_NO_KNOWNFOLDER"):     # (tests point the app at a fake profile)
        try:

            class GUID(ctypes.Structure):
                _fields_ = [("a", ctypes.c_uint32), ("b", ctypes.c_uint16), ("c", ctypes.c_uint16), ("d", ctypes.c_ubyte * 8)]
            g = GUID(); ctypes.oledll.ole32.CLSIDFromString(ctypes.c_wchar_p(_KF[name]), ctypes.byref(g))
            p = ctypes.c_wchar_p()
            ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(p))
            v = p.value; ctypes.windll.ole32.CoTaskMemFree(p)
            if v and os.path.isdir(v):
                return os.path.normpath(v)
        except Exception:
            pass
    return os.path.normpath(fallback)


def _norm(p):
    return os.path.normcase(os.path.abspath(p)).rstrip("\\/")


def _inside(p, root):
    p, root = _norm(p), _norm(root)
    return bool(root) and (p == root or p.startswith(root + os.sep))


def forbidden_roots():
    out = []
    for k in ("WINDIR", "SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "ProgramData", "CommonProgramFiles",
              "CommonProgramFiles(x86)", "ALLUSERSPROFILE", "PUBLIC"):
        v = os.environ.get(k)
        if v:
            out.append(v)
    if IS_WIN:
        out += ["C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)", "C:\\ProgramData"]
    else:
        out += ["/bin", "/boot", "/etc", "/lib", "/lib64", "/sbin", "/usr", "/var", "/opt", "/sys", "/proc", "/dev"]
    return [r for r in out if r]


class Guard:
    """decides whether a path may be deleted. Built once per session from the environment."""

    def __init__(self, dirs=None):
        self.dirs = dirs or user_dirs()
        self.forbidden = forbidden_roots()
        home = self.dirs["home"]
        self.allowed = [home] + [self.dirs[k] for k in ("local", "roaming", "temp", "Downloads", "Desktop", "Documents", "Videos", "Music", "Pictures")]
        # %TEMP% only counts when it is the user's own (never C:\Windows\Temp)
        if not _inside(self.dirs["temp"], home) and not _inside(self.dirs["temp"], self.dirs["local"]):
            self.allowed.remove(self.dirs["temp"])

    def ok(self, path):
        if not path or not os.path.isabs(path):
            return False
        n = _norm(path)
        if os.path.splitdrive(n)[1] in ("", os.sep):            # a drive root / filesystem root
            return False
        if any(_inside(n, f) for f in self.forbidden):
            return False
        if not any(_inside(n, a) and _norm(a) != n for a in self.allowed):   # inside (never equal to) an allowed root
            return False
        if any(_norm(self.dirs[k]) == n for k in self.dirs):    # never a whole known folder itself
            return False
        return True


# ---------------------------------------------------------------- data
class Item:
    __slots__ = ("path", "size", "mtime", "kind", "count", "selected", "group", "keep_root", "note")

    def __init__(self, path, size, mtime, kind="file", count=1, group=None, keep_root=False, note=""):
        self.path, self.size, self.mtime, self.kind, self.count = path, size, mtime, kind, count
        self.selected = False            # NOTHING is ever pre-selected
        self.group, self.keep_root, self.note = group, keep_root, note


class Category:
    def __init__(self, cid, title, desc, risk="safe", permanent_only=False):
        self.id, self.title, self.desc, self.risk, self.permanent_only = cid, title, desc, risk, permanent_only
        self.items = []
        self.error = ""

    @property
    def size(self):
        return sum(i.size for i in self.items)

    @property
    def selected_items(self):
        return [i for i in self.items if i.selected]


def human(n):
    n = float(n or 0)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return ("%d %s" % (n, u)) if u == "B" else ("%.1f %s" % (n, u))
        n /= 1024


# ---------------------------------------------------------------- helpers
def _is_link(entry_or_path):
    try:
        st = os.lstat(entry_or_path) if isinstance(entry_or_path, str) else entry_or_path.stat(follow_symlinks=False)
        if stat.S_ISLNK(st.st_mode):
            return True
        return bool(getattr(st, "st_file_attributes", 0) & 0x400)      # FILE_ATTRIBUTE_REPARSE_POINT (junctions etc.)
    except OSError:
        return True


_CLOUD = 0x400000 | 0x1000 | 0x40000       # RECALL_ON_DATA_ACCESS | OFFLINE | RECALL_ON_OPEN (OneDrive placeholders)


def tree_size(path, cancel=None, limit_files=200000):
    """(bytes, files, newest mtime) of a folder, never following links/junctions"""
    total = files = 0; newest = 0.0
    stack = [path]
    while stack:
        if cancel and cancel():
            break
        d = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    try:
                        if _is_link(e):
                            continue
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        else:
                            st = e.stat(follow_symlinks=False); total += st.st_size; files += 1; newest = max(newest, st.st_mtime)
                            if files >= limit_files:
                                return total, files, newest
                    except OSError:
                        continue
        except OSError:
            continue
    return total, files, newest


def walk_files(root, cancel=None, max_depth=12):
    """yield (path, stat) for files under root; skips links/junctions, cloud placeholders and unreadable folders"""
    stack = [(root, 0)]
    while stack:
        if cancel and cancel():
            return
        d, depth = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    try:
                        if _is_link(e):
                            continue
                        if e.is_dir(follow_symlinks=False):
                            if depth < max_depth and not e.name.startswith("$"):
                                stack.append((e.path, depth + 1))
                        elif e.is_file(follow_symlinks=False):
                            st = e.stat(follow_symlinks=False)
                            if getattr(st, "st_file_attributes", 0) & _CLOUD:
                                continue
                            yield e.path, st
                    except OSError:
                        continue
        except OSError:
            continue


def _dir_item(path, cancel, keep_root=True, label=None):
    if not os.path.isdir(path) or _is_link(path) or hidden_name(path):
        return None
    size, n, newest = tree_size(path, cancel)
    if n == 0:
        return None
    return Item(path, size, newest or os.path.getmtime(path), "folder", n, keep_root=keep_root, note=label or "")


# ---------------------------------------------------------------- scanners
BROWSERS = [
    ("Microsoft Edge", ("local", r"Microsoft/Edge/User Data")),
    ("Google Chrome", ("local", r"Google/Chrome/User Data")),
    ("Brave", ("local", r"BraveSoftware/Brave-Browser/User Data")),
    ("Opera", ("local", r"Opera Software/Opera Stable")),
    ("Opera", ("roaming", r"Opera Software/Opera Stable")),
    ("Opera GX", ("local", r"Opera Software/Opera GX Stable")),
    ("Opera GX", ("roaming", r"Opera Software/Opera GX Stable")),
]
# ONLY these cache sub-folders are ever listed - never profiles, passwords, cookies, history, bookmarks or extensions
CHROMIUM_CACHE = ("Cache", "Code Cache", "GPUCache", "DawnCache", "DawnGraphiteCache", "DawnWebGPUCache", "ShaderCache", "GrShaderCache")
CACHE_NAMES = {"cache", "caches", "cache2", "code cache", "gpucache", "shadercache", "grshadercache", "dxcache", "glcache",
               "dawncache", "htmlcache", "webcache", "cacheddata", "cache_data", "dxccache", "d3dscache", "startupcache"}
KNOWN_APP_CACHES = [r"pip/Cache", r"npm-cache", r"Yarn/Cache", r"NuGet/v3-cache", r"NuGet/plugins-cache", r"Microsoft/Windows/INetCache",
                    r"D3DSCache", r"NVIDIA/DXCache", r"NVIDIA/GLCache", r"NVIDIA Corporation/NV_Cache", r"AMD/DxCache", r"AMD/DxcCache",
                    r"AMD/GLCache", r"AMD/VkCache", r"Intel/ShaderCache", r"go-build", r"pnpm-cache", r"ms-playwright-cache",
                    r"Microsoft/Windows/WebCache.old", r"CrashReportClient"]
SKIP_LOCAL_TOP = {"temp", "packages", "microsoft", "programs", "google", "bravesoftware", "opera software", "mozilla", "ex storage lab",
                  "hyperion digital ex", "crashdumps", "connecteddevicesplatform", "comms", "publishers", "virtualstore"}


class Scanner:
    def __init__(self, guard=None, cancel=None, progress=None):
        self.g = guard or Guard(); self.d = self.g.dirs
        self.cancel = cancel or (lambda: False)
        self.progress = progress or (lambda text: None)

    def _add(self, cat, item):
        if item and not hidden_name(item.path) and self.g.ok(item.path):
            cat.items.append(item)

    # 1. temp ---------------------------------------------------------
    def temp(self, skip_recent_hours=24):
        cat = Category("temp", "Temporary files", "Your Temp folders (%%TEMP%% and %%LOCALAPPDATA%%\\Temp). Items changed in the last %d h are left out because apps may still be using them." % skip_recent_hours)
        roots = []
        for r in (self.d["temp"], os.path.join(self.d["local"], "Temp")):
            if os.path.isdir(r) and _norm(r) not in [_norm(x) for x in roots] and self.g.ok(os.path.join(r, "x")):
                roots.append(r)
        cutoff = time.time() - skip_recent_hours * 3600
        for r in roots:
            self.progress("Scanning %s" % r)
            try:
                entries = list(os.scandir(r))
            except OSError as e:
                cat.error = str(e); continue
            for e in entries:
                if self.cancel():
                    return cat
                try:
                    if _is_link(e):
                        continue
                    if e.is_dir(follow_symlinks=False):
                        it = _dir_item(e.path, self.cancel, keep_root=False)
                    else:
                        st = e.stat(follow_symlinks=False); it = Item(e.path, st.st_size, st.st_mtime)
                    if it and it.mtime < cutoff:
                        self._add(cat, it)
                except OSError:
                    continue
        return cat

    # 2. recycle bin --------------------------------------------------
    def recycle(self):
        cat = Category("recycle", "Recycle Bin", "Files you already deleted. Emptying the Recycle Bin is always permanent.", permanent_only=True)
        size, count = recycle_bin_info()
        if count:
            cat.items.append(Item("Recycle Bin", size, time.time(), "recyclebin", count, note="%d item(s) on all drives" % count))
        elif size is None:
            cat.error = "The Recycle Bin size could not be read on this system."
        return cat

    # 3. browser caches -----------------------------------------------
    def browsers(self):
        cat = Category("browser", "Browser caches", "Cache folders only (Edge, Chrome, Firefox, Opera, Brave). Profiles, passwords, cookies, history and bookmarks are never touched. Close the browser first for the best result.")
        for name, (base, rel) in BROWSERS:
            root = os.path.join(self.d[base], *rel.split("/"))
            if not os.path.isdir(root):
                continue
            self.progress("Scanning %s cache" % name)
            profiles = [root]
            try:
                profiles += [e.path for e in os.scandir(root) if e.is_dir(follow_symlinks=False) and
                             (e.name == "Default" or e.name.startswith("Profile ") or e.name in ("Guest Profile", "System Profile"))]
            except OSError:
                pass
            for p in profiles:
                for c in CHROMIUM_CACHE:
                    pc = os.path.join(p, c)
                    label = "%s \u00b7 %s \u00b7 %s" % (name, os.path.basename(p) if p != root else "shared", c)
                    self._add(cat, _dir_item(pc, self.cancel, True, label))
                if self.cancel():
                    return cat
        ff = os.path.join(self.d["local"], "Mozilla", "Firefox", "Profiles")      # the LOCAL half of a profile is cache only
        if os.path.isdir(ff):
            self.progress("Scanning Firefox cache")
            for e in os.scandir(ff):
                if e.is_dir(follow_symlinks=False):
                    for c in ("cache2", "startupCache", "thumbnails"):
                        self._add(cat, _dir_item(os.path.join(e.path, c), self.cancel, True, "Firefox \u00b7 %s \u00b7 %s" % (e.name, c)))
        return cat

    # 4. windows caches, dumps, error reports ---------------------------
    def windows(self):
        cat = Category("system", "Thumbnails, crash dumps & error reports", "Windows thumbnail cache, crash dumps and error reports in your own profile. Windows rebuilds thumbnails when needed; files Explorer is using are skipped.")
        exp = os.path.join(self.d["local"], "Microsoft", "Windows", "Explorer")
        self.progress("Scanning thumbnail cache")
        if os.path.isdir(exp):
            for e in os.scandir(exp):
                if e.is_file(follow_symlinks=False) and e.name.lower().startswith("thumbcache_") and e.name.lower().endswith(".db"):
                    st = e.stat(); self._add(cat, Item(e.path, st.st_size, st.st_mtime, note="Thumbnail cache"))
        dumps = os.path.join(self.d["local"], "CrashDumps")
        if os.path.isdir(dumps):
            for p, st in walk_files(dumps, self.cancel, 2):
                self._add(cat, Item(p, st.st_size, st.st_mtime, note="Crash dump"))
        for sub in ("ReportArchive", "ReportQueue", "Temp"):
            w = os.path.join(self.d["local"], "Microsoft", "Windows", "WER", sub)
            if os.path.isdir(w):
                for e in os.scandir(w):
                    if e.is_dir(follow_symlinks=False):
                        self._add(cat, _dir_item(e.path, self.cancel, False, "Error report"))
                    elif e.is_file(follow_symlinks=False):
                        st = e.stat(); self._add(cat, Item(e.path, st.st_size, st.st_mtime, note="Error report"))
        return cat

    # 5. app caches ----------------------------------------------------
    def app_caches(self):
        cat = Category("apps", "App caches", "Folders in %LOCALAPPDATA% that are clearly caches (named Cache, GPUCache, ShaderCache, ...). Apps rebuild them; close an app first to clear its cache fully.")
        local = self.d["local"]; seen = set()
        self.progress("Scanning app caches")
        for rel in KNOWN_APP_CACHES:
            p = os.path.join(local, *rel.split("/"))
            if os.path.isdir(p):
                seen.add(_norm(p)); self._add(cat, _dir_item(p, self.cancel, True, rel.replace("/", "\\")))
        try:
            tops = [e for e in os.scandir(local) if e.is_dir(follow_symlinks=False) and e.name.lower() not in SKIP_LOCAL_TOP]
        except OSError:
            tops = []
        for t in tops:                      # <vendor>\<name> and <vendor>\<app>\<name>, depth <= 3
            if self.cancel():
                break
            if _is_link(t.path) or hidden_name(t.path):
                continue
            stack = [(t.path, 1)]
            while stack:
                d, depth = stack.pop()
                try:
                    subs = [e for e in os.scandir(d) if e.is_dir(follow_symlinks=False) and not _is_link(e)]
                except OSError:
                    continue
                for e in subs:
                    if e.name.lower() in CACHE_NAMES:
                        if _norm(e.path) not in seen and not any(_inside(e.path, s) for s in seen):
                            seen.add(_norm(e.path))
                            self._add(cat, _dir_item(e.path, self.cancel, True, os.path.relpath(e.path, local)))
                    elif depth < 3 and e.name.lower() not in ("user data", "profiles", "extensions", "databases", "local storage"):
                        stack.append((e.path, depth + 1))
        return cat

    # 6. old installers ------------------------------------------------
    def installers(self, min_age_days=0):
        cat = Category("installers", "Old installers & archives in Downloads", "Setup files (.exe, .msi) and .zip archives in your Downloads folder. Check that you no longer need them before ticking.", risk="review")
        dl = self.d["Downloads"]
        if not os.path.isdir(dl):
            return cat
        self.progress("Scanning Downloads for installers")
        cutoff = time.time() - min_age_days * 86400
        for p, st in walk_files(dl, self.cancel, 3):
            if os.path.splitext(p)[1].lower() in (".exe", ".msi", ".zip") and st.st_mtime <= cutoff:
                self._add(cat, Item(p, st.st_size, st.st_mtime))
        cat.items.sort(key=lambda i: i.mtime)
        return cat

    # 7. large files ---------------------------------------------------
    def large(self, min_mb=500, folders=("Downloads", "Videos", "Desktop", "Documents", "Music", "Pictures")):
        cat = Category("large", "Large files (%d MB+)" % min_mb, "Big files in your own folders. These are YOUR files: only tick what you are sure you no longer need.", risk="personal")
        lim = min_mb * 1024 * 1024; seen = set()
        for k in folders:
            root = self.d.get(k)
            if not root or not os.path.isdir(root):
                continue
            self.progress("Looking for large files in %s" % root)
            for p, st in walk_files(root, self.cancel):
                if st.st_size >= lim and _norm(p) not in seen:
                    seen.add(_norm(p)); self._add(cat, Item(p, st.st_size, st.st_mtime, note=k))
        cat.items.sort(key=lambda i: -i.size)
        return cat

    # 8. duplicates ----------------------------------------------------
    def duplicates(self, min_kb=1):
        cat = Category("dupes", "Duplicate files in Downloads", "Files in Downloads with identical content (SHA-256). Keep at least one copy of each group - nothing is ticked for you.", risk="personal")
        dl = self.d["Downloads"]
        if not os.path.isdir(dl):
            return cat
        self.progress("Looking for duplicates in Downloads")
        by_size = {}
        for p, st in walk_files(dl, self.cancel, 6):
            if st.st_size >= min_kb * 1024:
                by_size.setdefault(st.st_size, []).append((p, st))
        gid = 0
        for size, files in sorted(by_size.items(), key=lambda kv: -kv[0]):
            if len(files) < 2 or self.cancel():
                continue
            by_head = {}
            for p, st in files:
                h = file_hash(p, 65536)
                if h:
                    by_head.setdefault(h, []).append((p, st))
            for grp in by_head.values():
                if len(grp) < 2:
                    continue
                by_full = {}
                for p, st in grp:
                    self.progress("Hashing %s" % os.path.basename(p))
                    h = file_hash(p) if size > 65536 else file_hash(p, 65536)
                    if h:
                        by_full.setdefault(h, []).append((p, st))
                for h, same in by_full.items():
                    if len(same) < 2:
                        continue
                    gid += 1
                    for p, st in sorted(same, key=lambda x: x[1].st_mtime):
                        self._add(cat, Item(p, st.st_size, st.st_mtime, group=gid, note="Group %d \u00b7 %d copies" % (gid, len(same))))
        return cat


def file_hash(path, limit=None):
    h = hashlib.sha256(); left = limit
    try:
        with open(path, "rb") as f:
            while True:
                b = f.read(1 << 20 if left is None else min(1 << 20, left))
                if not b:
                    break
                h.update(b)
                if left is not None:
                    left -= len(b)
                    if left <= 0:
                        break
        return h.hexdigest()
    except OSError:
        return None


# ---------------------------------------------------------------- drives
def drives():
    """[(label, total, used, free)] for fixed/removable drives"""
    out = []
    if IS_WIN:
        try:
            mask = ctypes.windll.kernel32.GetLogicalDrives()
            for i, L in enumerate(string.ascii_uppercase):
                if mask & (1 << i):
                    root = L + ":\\"
                    t = ctypes.windll.kernel32.GetDriveTypeW(root)
                    if t in (2, 3):                 # removable, fixed
                        try:
                            u = shutil.disk_usage(root)
                            if u.total > 0:
                                buf = ctypes.create_unicode_buffer(261)
                                ctypes.windll.kernel32.GetVolumeInformationW(root, buf, 261, None, None, None, None, 0)
                                out.append(("%s (%s)" % (buf.value or ("Removable" if t == 2 else "Local Disk"), L + ":"), u.total, u.used, u.free))
                        except OSError:
                            pass
        except Exception:
            pass
    if not out:
        u = shutil.disk_usage(os.path.expanduser("~"))
        out.append(("Home", u.total, u.used, u.free))
    return out


# ---------------------------------------------------------------- recycle bin (shell32)
class SHQUERYRBINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint32), ("i64Size", ctypes.c_int64), ("i64NumItems", ctypes.c_int64)]


def recycle_bin_info():
    if not IS_WIN:
        return None, 0
    try:
        info = SHQUERYRBINFO(); info.cbSize = ctypes.sizeof(info)
        hr = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
        if hr != 0:
            return None, 0
        return int(info.i64Size), int(info.i64NumItems)
    except Exception:
        return None, 0


def empty_recycle_bin():
    if not IS_WIN:
        return False, "not Windows"
    hr = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x1 | 0x2 | 0x4)   # no confirmation / progress / sound
    return (hr in (0, -2147418113)), "HRESULT 0x%08X" % (hr & 0xFFFFFFFF)       # E_UNEXPECTED = already empty


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [("hwnd", ctypes.c_void_p), ("wFunc", ctypes.c_uint), ("pFrom", ctypes.c_wchar_p), ("pTo", ctypes.c_wchar_p),
                ("fFlags", ctypes.c_uint16), ("fAnyOperationsAborted", ctypes.c_int), ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", ctypes.c_wchar_p)]


FO_DELETE = 3
FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI, FOF_WANTNUKEWARNING = 0x4, 0x10, 0x40, 0x400, 0x4000


def send_to_recycle_bin(path):
    """move one file/folder to the Recycle Bin. Returns (ok, message). Never falls back to a permanent delete."""
    if not IS_WIN:
        return _xdg_trash(path)
    op = SHFILEOPSTRUCTW(); op.wFunc = FO_DELETE; op.pFrom = path + "\0"; op.pTo = None
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_SILENT | FOF_WANTNUKEWARNING
    rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if rc == 0 and not op.fAnyOperationsAborted and not os.path.lexists(path):
        return True, ""
    return False, "in use or cannot be recycled (code %d)" % rc


def _xdg_trash(path):          # Linux test runs: freedesktop trash, so tests can verify "recycle" never destroys data
    try:
        tr = os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "Trash")
        os.makedirs(os.path.join(tr, "files"), exist_ok=True); os.makedirs(os.path.join(tr, "info"), exist_ok=True)
        base = os.path.basename(path); dst = os.path.join(tr, "files", base); n = 1
        while os.path.lexists(dst):
            n += 1; dst = os.path.join(tr, "files", "%s.%d" % (base, n))
        with open(os.path.join(tr, "info", os.path.basename(dst) + ".trashinfo"), "w") as f:
            f.write("[Trash Info]\nPath=%s\nDeletionDate=%s\n" % (path, time.strftime("%Y-%m-%dT%H:%M:%S")))
        shutil.move(path, dst)
        return True, ""
    except OSError as e:
        return False, str(e)


# ---------------------------------------------------------------- deleter
class Result:
    def __init__(self):
        self.freed = 0; self.removed = 0; self.skipped = []; self.log = []; self.refused = []

    def add_log(self, s):
        self.log.append(time.strftime("%H:%M:%S ") + s)


def _remove_file(path, recycle):
    if recycle:
        return send_to_recycle_bin(path)
    try:
        try:
            os.remove(path)
        except PermissionError:
            st = os.lstat(path)
            if IS_WIN and not (st.st_mode & stat.S_IWRITE):        # read-only temp files: clear the flag (no admin needed)
                os.chmod(path, stat.S_IWRITE); os.remove(path)
            else:
                raise
        return True, ""
    except OSError as e:
        return False, (getattr(e, "strerror", None) or str(e))


def delete(items, recycle=True, guard=None, progress=None, cancel=None):
    """delete EXACTLY these user-ticked items. Every path is re-checked by the Guard. Locked files are skipped."""
    g = guard or Guard(); r = Result(); progress = progress or (lambda f, t: None); cancel = cancel or (lambda: False)
    items = [i for i in items if i.selected]
    r.add_log("Mode: %s. %d item(s) ticked." % ("Move to Recycle Bin" if recycle else "Delete permanently", len(items)))
    for n, it in enumerate(items):
        if cancel():
            r.add_log("Stopped by user."); break
        progress(n / max(len(items), 1), it.path)
        if it.kind == "recyclebin":
            before, _ = recycle_bin_info(); ok, msg = empty_recycle_bin()
            if ok:
                after, _ = recycle_bin_info(); freed = max((before or it.size) - (after or 0), 0)
                r.freed += freed; r.removed += it.count; r.add_log("Emptied the Recycle Bin (%s)." % human(freed))
            else:
                r.skipped.append((it.path, msg)); r.add_log("Could not empty the Recycle Bin: %s" % msg)
            continue
        if not g.ok(it.path) or hidden_name(it.path):
            r.refused.append(it.path); r.add_log("REFUSED (protected location): %s" % it.path); continue
        if _is_link(it.path):
            r.refused.append(it.path); r.add_log("REFUSED (link/junction): %s" % it.path); continue
        if not os.path.lexists(it.path):
            r.add_log("Already gone: %s" % it.path); continue
        if os.path.isfile(it.path):
            size = os.path.getsize(it.path); ok, msg = _remove_file(it.path, recycle)
            if ok:
                r.freed += size; r.removed += 1; r.add_log("%s %s (%s)" % ("Recycled" if recycle else "Deleted", it.path, human(size)))
            else:
                r.skipped.append((it.path, msg)); r.add_log("Skipped (in use / locked): %s - %s" % (it.path, msg))
            continue
        _delete_folder(it, recycle, g, r, cancel)
    progress(1.0, "")
    r.add_log("Done. Freed %s from %d file(s); %d skipped; %d refused." % (human(r.freed), r.removed, len(r.skipped), len(r.refused)))
    return r


def _delete_folder(it, recycle, g, r, cancel):
    """folder items: whole-folder recycle when possible, else file by file (locked files are skipped)."""
    size, files, _ = tree_size(it.path)
    if recycle and not it.keep_root:
        ok, msg = send_to_recycle_bin(it.path)
        if ok:
            r.freed += size; r.removed += files; r.add_log("Recycled folder %s (%d file%s, %s)" % (it.path, files, "" if files == 1 else "s", human(size))); return
    freed = removed = skipped = 0
    dirs = []
    for p, st in list(walk_files(it.path, cancel, 64)):
        if not g.ok(p):
            r.refused.append(p); continue
        ok, msg = _remove_file(p, recycle)
        if ok:
            freed += st.st_size; removed += 1
        else:
            skipped += 1; r.skipped.append((p, msg))
    for root, ds, fs in os.walk(it.path, topdown=False, followlinks=False):
        if _norm(root) == _norm(it.path) and it.keep_root:
            continue
        if not _is_link(root):
            try:
                os.rmdir(root)
            except OSError:
                pass
    r.freed += freed; r.removed += removed
    r.add_log("%s %s: %d file%s, %s%s" % ("Recycled contents of" if recycle else "Cleared", it.path, removed, "" if removed == 1 else "s", human(freed),
                                         ("; %d in use, skipped" % skipped) if skipped else ""))
