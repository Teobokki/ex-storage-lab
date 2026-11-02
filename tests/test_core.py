"""EX STORAGE LAB engine tests on a fake user profile. Linux:  python3 -m unittest tests/test_core.py -v
Windows/Wine:  python -m unittest tests\\test_core.py -v   (uses the real Recycle Bin API + Windows file locking)"""
import hashlib, os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fakeprofile

ROOT = tempfile.mkdtemp(prefix="exsl_t_")
if os.name != "nt":
    os.environ["XDG_DATA_HOME"] = os.path.join(ROOT, "xdg")
import storage_core as core


def snapshot(root):
    out = {}
    for d, ds, fs in os.walk(root):
        for n in fs:
            p = os.path.join(d, n)
            with open(p, "rb") as fh:
                out[p] = hashlib.sha256(fh.read()).hexdigest()
    return out


class T(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(os.path.join(ROOT, "p"), ignore_errors=True)
        self.fp = fakeprofile.build(os.path.join(ROOT, "p"), big_mb=12)
        self.g = core.Guard()

    def scan(self):
        s = core.Scanner(self.g)
        return {c.id: c for c in (s.temp(), s.browsers(), s.windows(), s.app_caches(), s.installers(), s.large(10), s.duplicates())}

    def paths(self, cat):
        return [i.path for i in cat.items]

    def test_categories_found(self):
        c = self.scan(); f = self.fp["files"]
        self.assertIn(f["tmp_old"], self.paths(c["temp"]))
        self.assertIn(os.path.dirname(f["tmp_dir"]), self.paths(c["temp"]))
        self.assertNotIn(f["tmp_new"], self.paths(c["temp"]))                 # recent temp files are left alone
        self.assertGreaterEqual(len(c["browser"].items), 8)
        self.assertTrue(any("cache2" in p for p in self.paths(c["browser"])))
        self.assertTrue(any("Opera" in p for p in self.paths(c["browser"])))
        self.assertEqual(len(c["system"].items), 3)                           # thumbcache, dump, WER report (not iconcache)
        self.assertTrue(any(p.endswith(os.path.join("pip", "Cache")) for p in self.paths(c["apps"])))
        self.assertTrue(any(p.endswith(os.path.join("PixelPaint", "Cache")) for p in self.paths(c["apps"])))
        self.assertEqual(len(c["installers"].items), 3)
        self.assertEqual(self.paths(c["large"]), [f["big"]])
        dupes = self.paths(c["dupes"])
        self.assertEqual(sorted(dupes), sorted([f["dup_a"], f["dup_b"], f["dup_c"]]))
        self.assertEqual(len({i.group for i in c["dupes"].items}), 1)

    def test_never_lists_private_browser_data_or_settings(self):
        allp = [p for cat in self.scan().values() for p in self.paths(cat)]
        f = self.fp["files"]
        for k in ("cookies", "history", "logins", "ff_places", "app_settings", "doc"):
            for p in allp:
                self.assertFalse(p == f[k] or f[k].startswith(p + os.sep), (k, p))
        self.assertFalse(any("Steam" in p for p in allp))                       # hidden names never shown
        self.assertFalse(any(os.path.basename(p) in ("User Data", "Default", "Profile 1") for p in allp))

    def test_nothing_preselected_and_nothing_deleted_without_selection(self):
        before = snapshot(self.fp["home"]); cats = self.scan()
        items = [i for c in cats.values() for i in c.items]
        self.assertTrue(items)
        self.assertFalse(any(i.selected for i in items))
        r = core.delete(items, recycle=False, guard=self.g)                     # passing everything, but nothing is ticked
        self.assertEqual(r.removed, 0); self.assertEqual(r.freed, 0)
        self.assertEqual(before, snapshot(self.fp["home"]))

    def test_permanent_delete_exactly_the_ticked_items(self):
        cats = self.scan(); f = self.fp["files"]
        tick = [i for i in cats["temp"].items if i.path == f["tmp_old"]] + [cats["dupes"].items[1]]
        cache = next(i for i in cats["browser"].items if i.path.endswith(os.path.join("Chrome", "User Data", "Default", "Cache")))
        tick.append(cache)
        for i in tick:
            i.selected = True
        before = snapshot(self.fp["home"])
        r = core.delete([i for c in cats.values() for i in c.items], recycle=False, guard=self.g)
        after = snapshot(self.fp["home"])
        gone = set(before) - set(after)
        expect = {f["tmp_old"], cats["dupes"].items[1].path} | {p for p in before if p.startswith(cache.path + os.sep)}
        self.assertEqual(gone, expect)
        self.assertTrue(os.path.isdir(cache.path))                               # cache root folder is kept, only emptied
        self.assertTrue(os.path.exists(f["cookies"]))
        self.assertEqual(r.freed, 300_000 + 1_300_000 + 4_000_000)

    def test_recycle_mode_keeps_data_recoverable(self):
        cats = self.scan(); f = self.fp["files"]
        it = next(i for i in cats["installers"].items if i.path == f["inst"]); it.selected = True
        d = next(i for i in cats["temp"].items if i.kind == "folder"); d.selected = True
        r = core.delete([it, d], recycle=True, guard=self.g)
        self.assertFalse(os.path.exists(f["inst"])); self.assertFalse(os.path.exists(d.path))
        self.assertEqual(r.removed, 3, r.log); self.assertEqual(len(r.skipped), 0, r.skipped)
        if os.name != "nt":
            trash = os.listdir(os.path.join(os.environ["XDG_DATA_HOME"], "Trash", "files"))
            self.assertIn(os.path.basename(f["inst"]), trash)

    def test_guard_refuses_outside_and_roots(self):
        g = self.g; home = self.fp["home"]
        self.assertFalse(g.ok(home)); self.assertFalse(g.ok(self.fp["dl"])); self.assertFalse(g.ok(self.fp["local"]))
        self.assertFalse(g.ok(os.path.join(ROOT, "elsewhere.txt")))
        self.assertFalse(g.ok("C:\\Windows\\System32\\x.dll" if os.name == "nt" else "/etc/passwd"))
        self.assertFalse(g.ok("relative.txt")); self.assertFalse(g.ok(os.path.abspath(os.sep)))
        self.assertTrue(g.ok(self.fp["files"]["tmp_old"]))
        outside = fakeprofile.w(os.path.join(ROOT, "outside", "keep.txt"), 100)
        fake = core.Item(outside, 100, 0); fake.selected = True
        r = core.delete([fake], recycle=False, guard=g)
        self.assertTrue(os.path.exists(outside)); self.assertEqual(r.refused, [outside])

    def test_links_not_followed(self):
        if not hasattr(os, "symlink") or os.name == "nt":
            self.skipTest("symlinks need privileges on Windows")
        target = fakeprofile.w(os.path.join(ROOT, "precious", "keep.bin"), 5000)
        cache = os.path.join(self.fp["local"], "pip", "Cache")
        os.symlink(os.path.dirname(target), os.path.join(cache, "link"))
        cats = self.scan()
        it = next(i for i in cats["apps"].items if i.path == cache); it.selected = True
        core.delete([it], recycle=False, guard=self.g)
        self.assertTrue(os.path.exists(target))

    def test_locked_files_are_skipped(self):
        cats = self.scan(); f = self.fp["files"]
        it = next(i for i in cats["temp"].items if i.path == f["tmp_old"]); it.selected = True
        folder = next(i for i in cats["temp"].items if i.kind == "folder"); folder.selected = True
        locked = os.path.join(folder.path, "payload.bin")
        if os.name == "nt":
            h = open(f["tmp_old"], "rb"); h2 = open(locked, "rb")    # CRT opens without FILE_SHARE_DELETE -> in use
        else:
            os.chmod(os.path.dirname(f["tmp_old"]), 0o555)            # simulate "access denied" for direct temp files
        try:
            r = core.delete([it, folder], recycle=False, guard=self.g)
        finally:
            if os.name == "nt":
                h.close(); h2.close()
            else:
                os.chmod(os.path.dirname(f["tmp_old"]), 0o755)
        self.assertTrue(os.path.exists(f["tmp_old"]))
        self.assertIn(f["tmp_old"], [p for p, _ in r.skipped])
        if os.name == "nt":
            self.assertTrue(os.path.exists(locked))
            self.assertFalse(os.path.exists(os.path.join(folder.path, "sub", "data.cab")))

    def test_hidden_names(self):
        for p in ("C:/x/Steam/a", "D:/Games/Minecraft/x", "c:/a/GTA V/b", "/x/Adobe/y", "/x/Call of Duty/z", "/x/COD/z"):
            self.assertTrue(core.hidden_name(p), p)
        for p in ("C:/x/Code/Cache", "/x/codec/a", "/x/Downloads/report.pdf"):
            self.assertFalse(core.hidden_name(p), p)

    def test_drives(self):
        d = core.drives(); self.assertTrue(d); self.assertTrue(all(t >= u for _, t, u, _ in d))


if __name__ == "__main__":
    unittest.main()
