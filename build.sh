#!/bin/sh
# ONE Windows build: PyInstaller onedir -> Inno Setup installer + portable zip (same files)
set -e
export WINEPREFIX=/workspace/exwifi/.wine WINEDEBUG=-all
cd /workspace/ex-storage-lab
V=1.0.0
rm -rf build "dist/EX STORAGE LAB"
wine 'C:\Python311\python.exe' -m PyInstaller --noconfirm "EX STORAGE LAB.spec" > pyi.log 2>&1; echo PYI_DONE
wine 'C:\InnoSetup\ISCC.exe' installer.iss > iss.log 2>&1; echo ISS_DONE
cd dist && rm -f EX.STORAGE.LAB.$V.Windows.x64.zip && python3 -c "import shutil;shutil.make_archive('EX.STORAGE.LAB.$V.Windows.x64','zip','.','EX STORAGE LAB')" && echo ZIP_DONE
ls -la; sha256sum EX.STORAGE.LAB.Setup.$V.exe EX.STORAGE.LAB.$V.Windows.x64.zip
