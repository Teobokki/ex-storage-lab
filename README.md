# EX STORAGE LAB

Frees up storage on Windows - but **only deletes what you tick and confirm**.

- Drive usage bars (used / free) for every local drive
- Scans for reclaimable space, grouped with sizes: Temp folders, Recycle Bin, browser caches (Edge, Chrome, Firefox, Opera, Brave - cache folders only, never profiles, passwords, cookies or history), Windows thumbnail cache / crash dumps / error reports, app caches in %LOCALAPPDATA%, old installers in Downloads, a Large Files finder and a hash-based Duplicate Files finder in Downloads
- Nothing is pre-selected. Tick categories or expand them to tick single files (path, size, date)
- A confirmation lists exactly what will be removed and the total size, with **Move to Recycle Bin** (default) or **Delete permanently**
- Result summary with the space freed and a log (also saved to `%LOCALAPPDATA%\EX STORAGE LAB\logs`)
- Files in use are skipped. Windows, Program Files, ProgramData and anything outside your own user folders are never touched. No admin rights, no UAC: per-user install
- Check for updates (reads `latest.json` on main, TLS always verified via the Windows certificate store)

Install: download `EX.STORAGE.LAB.Setup.<version>.exe` from [Releases](https://github.com/Teobokki/ex-storage-lab/releases), or use the portable zip. Also in the HYPERION DIGITAL EX store.

Build (Linux + Wine): `./build.sh`. Tests: `python3 -m unittest tests/test_core.py -v` (also runs under Windows Python).

©2026 EX Inc./HYPERION DIGITAL ©2026
