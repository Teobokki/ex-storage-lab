import os, sys, tempfile, shutil
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here); sys.path.insert(0, os.path.dirname(here))
import fakeprofile
root = os.path.join(tempfile.gettempdir(), "exsl_shots_profile"); shutil.rmtree(root, ignore_errors=True)
fakeprofile.build(root, big_mb=1, showcase=True)
os.environ["EXSL_SHOTS"] = sys.argv[1]
import ex_storage_lab
ex_storage_lab.main()
