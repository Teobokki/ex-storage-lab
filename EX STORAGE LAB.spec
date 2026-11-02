# -*- mode: python ; coding: utf-8 -*-
# EX STORAGE LAB - one onedir build; the installer and the portable zip are both made from dist\EX STORAGE LAB
DROP = ['QtNetwork', 'QtQml', 'QtQuick', 'QtPdf', 'QtWebEngine', 'QtWebEngineCore', 'QtWebEngineWidgets', 'QtWebChannel', 'QtOpenGL',
        'QtOpenGLWidgets', 'QtSvg', 'QtSql', 'QtTest', 'QtMultimedia', 'QtCharts', 'QtDataVisualization', 'Qt3DCore', 'QtBluetooth',
        'QtPositioning', 'QtSensors', 'QtSerialPort', 'QtDBus', 'QtDesigner', 'QtHelp', 'QtUiTools', 'QtXml', 'QtConcurrent', 'QtPrintSupport',
        'QtQuickWidgets', 'QtVirtualKeyboard', 'QtSpatialAudio', 'QtStateMachine', 'QtTextToSpeech', 'QtLocation', 'QtNfc', 'QtRemoteObjects',
        'QtScxml', 'QtWebSockets', 'QtHttpServer', 'QtGraphs', 'QtQuick3D', 'QtShaderTools']
a = Analysis(['ex_storage_lab.py'],
             datas=[('assets/logo.ico', 'assets'), ('assets/logo256.png', 'assets'), ('assets/cb_on.png', 'assets'),
                    ('assets/cb_off.png', 'assets'), ('assets/cb_part.png', 'assets')],
             hiddenimports=['truststore', 'certifi'],
             excludes=['tkinter', 'numpy', 'PIL', 'cv2', 'fitz', 'pymupdf', 'panda3d', 'webview', 'clr', 'pythonnet', 'shots', 'unittest',
                       'pydoc', 'soundcard', 'comtypes'] + ['PySide6.' + m for m in DROP],
             noarchive=False)
DROP_FILES = tuple(('qt6' + m[2:]).lower() for m in DROP)
a.binaries = [b for b in a.binaries if not any(x in b[0].lower().replace('\\', '/').split('/')[-1] for x in DROP_FILES)
              and 'opengl32sw' not in b[0].lower() and 'qtvirtualkeyboard' not in b[0].lower()]
a.datas = [d for d in a.datas if '/translations/' not in d[0].replace('\\', '/').lower()]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='EX STORAGE LAB', console=False, upx=False, version='version.txt',
          icon=['assets/logo.ico'])
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name='EX STORAGE LAB')
