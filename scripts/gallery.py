#!/usr/bin/env python3
import runpy
import sys
from pathlib import Path
sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[1]
runner = root / ".reference-ui/scripts/reference-ui.py"
sys.path.insert(0, str(runner.parent))
sys.argv = [str(runner), "--workspace", str(root), *sys.argv[1:]]
runpy.run_path(str(runner), run_name="__main__")
