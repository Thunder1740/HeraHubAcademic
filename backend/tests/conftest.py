from __future__ import annotations

import atexit
import os
import shutil
import tempfile


TEST_DATA_DIR = tempfile.mkdtemp(prefix="farmahub-tests-")
os.environ["FARMAHUB_DATA_DIR"] = TEST_DATA_DIR
atexit.register(lambda: shutil.rmtree(TEST_DATA_DIR, ignore_errors=True))
