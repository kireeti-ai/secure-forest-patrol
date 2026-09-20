#!/usr/bin/env python3
"""Retry failed Sensing the Forest extraction for specific files."""
import json, sys, os
from pathlib import Path

ML_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ML_DIR))
os.chdir(ML_DIR)

from scripts.streaming_zip import RangeHTTPFile
import zipfile

URL = "https://zenodo.org/api/records/18909809/files/42937__sensingtheforest__natural-soundscape-dataset-part-1.zip/content"
OUT = Path("datasets/raw/sensing_forest/audio")

targets = json.load(open(Path(__file__).resolve().parent.parent / "datasets" / "raw" / "sensing_forest" / "selected_subset.json"))

rf = RangeHTTPFile(URL)
zf = zipfile.ZipFile(rf, "r")
want = set(targets)
missing = []
for name in targets:
    outpath = OUT / name
    if outpath.exists() and outpath.stat().st_size > 1024:
        print(f"SKIP existing: {name} ({outpath.stat().st_size/1048576:.1f}MB)")
    else:
        missing.append(name)

print(f"Need to extract: {len(missing)} files")
for name in missing:
    found = False
    for i in zf.infolist():
        if i.filename.endswith(name):
            try:
                data = zf.read(i)
                outpath = OUT / i.filename
                outpath.parent.mkdir(parents=True, exist_ok=True)
                outpath.write_bytes(data)
                print(f"OK: {name} ({len(data)/1048576:.1f}MB)")
                found = True
            except Exception as e:
                print(f"FAIL: {name}: {e}")
            break
    if not found:
        print(f"NOT FOUND: {name}")
zf.close()
