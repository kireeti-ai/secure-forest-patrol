#!/usr/bin/env python3
"""
Regenerate the SAME frozen v1 segments with the digital filter enabled (variant B).
Reads sample_ids from datasets/v1/master_v1.csv (frozen splits untouched) and writes filtered
1 s segments to datasets/processed_filtered/ and a manifest to datasets/manifests/master_manifest_filtered.csv.
"""
import copy
import pandas as pd
from audio_preprocess import AudioPreprocessor, CONFIG, ML_ROOT

cfg = copy.deepcopy(CONFIG)
cfg['filter']['enabled'] = True
ids = set(pd.read_csv(ML_ROOT / "datasets/v1/master_v1.csv", usecols=['sample_id'])['sample_id'])
pre = AudioPreprocessor(cfg, processed_dir=ML_ROOT / "datasets/processed_filtered",
                        manifest_name="master_manifest_filtered.csv", keep_ids=ids)
df = pre.run()
missing = ids - set(df['sample_id'])
print(f"frozen ids: {len(ids)}, regenerated: {len(df)}, missing: {len(missing)}")
