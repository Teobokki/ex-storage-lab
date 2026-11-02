"""Builds a fake Windows user profile (temp files, browser caches, downloads, duplicates...) and points the
environment at it. Used by the tests and the screenshot run. ©2026 EX Inc./HYPERION DIGITAL ©2026"""
import os, time

OLD = time.time() - 10 * 86400


def w(path, size=0, data=None, old=True):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        if data is not None:
            f.write(data)
        else:
            chunk = os.urandom(min(size, 1 << 20)) if size else b""
            left = size
            while left > 0:
                f.write(chunk[:left]); left -= len(chunk)
    if old:
        os.utime(path, (OLD, OLD))
    return path


def sparse(path, size):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.truncate(size)
    os.utime(path, (OLD, OLD)); return path


def build(root, big_mb=60, showcase=False):
    j = lambda *p: os.path.join(root, *p)
    home = j("Users", "alex"); local = os.path.join(home, "AppData", "Local"); roam = os.path.join(home, "AppData", "Roaming")
    temp = os.path.join(local, "Temp"); dl = os.path.join(home, "Downloads")
    os.environ.update({"USERPROFILE": home, "LOCALAPPDATA": local, "APPDATA": roam, "TEMP": temp, "TMP": temp, "EXSL_NO_KNOWNFOLDER": "1"})
    f = {}
    # temp
    f["tmp_old"] = w(os.path.join(temp, "setup_log_4411.tmp"), 300_000)
    f["tmp_dir"] = w(os.path.join(temp, "unpack_8812", "payload.bin"), 2_500_000)
    w(os.path.join(temp, "unpack_8812", "sub", "data.cab"), 1_200_000)
    f["tmp_new"] = w(os.path.join(temp, "in_use_right_now.tmp"), 50_000, old=False)
    # browser caches + data that must NEVER be listed
    for b in (("Google", "Chrome", "User Data"), ("Microsoft", "Edge", "User Data"), ("BraveSoftware", "Brave-Browser", "User Data")):
        ud = os.path.join(local, *b)
        f.setdefault("cache", w(os.path.join(ud, "Default", "Cache", "Cache_Data", "data_1"), 4_000_000))
        w(os.path.join(ud, "Default", "Code Cache", "js", "a1"), 900_000)
        w(os.path.join(ud, "Profile 1", "GPUCache", "data_0"), 400_000)
        f.setdefault("cookies", w(os.path.join(ud, "Default", "Network", "Cookies"), 20_000))
        f.setdefault("history", w(os.path.join(ud, "Default", "History"), 30_000))
        f.setdefault("logins", w(os.path.join(ud, "Default", "Login Data"), 10_000))
        w(os.path.join(ud, "Default", "Bookmarks"), 5_000)
    w(os.path.join(local, "Opera Software", "Opera Stable", "Cache", "Cache_Data", "f_0001"), 700_000)
    w(os.path.join(local, "Mozilla", "Firefox", "Profiles", "ab12.default-release", "cache2", "entries", "E1"), 1_500_000)
    f["ff_places"] = w(os.path.join(roam, "Mozilla", "Firefox", "Profiles", "ab12.default-release", "places.sqlite"), 40_000)
    # windows caches / dumps / reports
    w(os.path.join(local, "Microsoft", "Windows", "Explorer", "thumbcache_256.db"), 3_000_000)
    w(os.path.join(local, "Microsoft", "Windows", "Explorer", "iconcache_32.db"), 100_000)
    w(os.path.join(local, "CrashDumps", "Notes.exe.4412.dmp"), 6_000_000)
    w(os.path.join(local, "Microsoft", "Windows", "WER", "ReportArchive", "AppCrash_Notes_1", "Report.wer"), 80_000)
    # app caches
    w(os.path.join(local, "pip", "Cache", "http", "x1"), 2_000_000)
    w(os.path.join(local, "NVIDIA", "DXCache", "s1.bin"), 1_800_000)
    w(os.path.join(local, "PixelPaint", "Cache", "thumbs.bin"), 1_100_000)
    f["app_settings"] = w(os.path.join(local, "PixelPaint", "settings.json"), 2_000)
    w(os.path.join(local, "Steam", "htmlcache", "Cache", "x"), 500_000)      # must be hidden (store policy)
    # downloads: installers, duplicates, big files, documents
    f["inst"] = w(os.path.join(dl, "PhotoTool_Setup_2.3.exe"), 3_500_000)
    w(os.path.join(dl, "driver_pack.msi"), 2_200_000)
    w(os.path.join(dl, "holiday_photos.zip"), 1_600_000)
    blob = os.urandom(1_300_000)
    f["dup_a"] = w(os.path.join(dl, "report.pdf"), data=blob)
    f["dup_b"] = w(os.path.join(dl, "report (1).pdf"), data=blob)
    f["dup_c"] = w(os.path.join(dl, "old", "report copy.pdf"), data=blob)
    w(os.path.join(dl, "same_size_diff.pdf"), data=blob[:-1] + b"X")
    f["doc"] = w(os.path.join(home, "Documents", "thesis.docx"), 400_000)
    f["big"] = w(os.path.join(home, "Videos", "family_trip_4k.mp4"), big_mb * 1024 * 1024)
    if showcase:                       # screenshot run: realistic sizes without writing gigabytes (sparse files)
        sparse(os.path.join(home, "Videos", "screen_recording_2026-08-14.mp4"), 2_400_000_000)
        sparse(os.path.join(home, "Downloads", "linux_distro_x64.iso"), 4_700_000_000)
        sparse(os.path.join(home, "Desktop", "project_backup_old.7z"), 1_150_000_000)
        sparse(os.path.join(home, "Documents", "VM disks", "testbox.vhdx"), 8_200_000_000)
        sparse(os.path.join(dl, "OfficeSuite_Setup_x64.exe"), 812_000_000)
        sparse(os.path.join(local, "Microsoft", "Edge", "User Data", "Default", "Cache", "Cache_Data", "data_3"), 310_000_000)
        sparse(os.path.join(local, "Google", "Chrome", "User Data", "Default", "Code Cache", "js", "big"), 140_000_000)
        sparse(os.path.join(temp, "dl_cache_77", "pkg.bin"), 920_000_000)
        sparse(os.path.join(local, "NVIDIA", "DXCache", "big.bin"), 260_000_000)
    return {"home": home, "local": local, "temp": temp, "dl": dl, "files": f}
