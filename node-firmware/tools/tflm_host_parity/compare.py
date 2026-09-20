"""Compare TFLite Micro (stock FC vs our per-channel FC) with Python TFLite on real test-set windows."""
import json, subprocess, sys
import numpy as np, pandas as pd, soundfile as sf, tensorflow as tf
sys.path.insert(0, "ml/preprocessing")
from feature_extraction import get_feature_extractor  # noqa: E402

harness, per_class = sys.argv[1], int(sys.argv[2])
MP = "ml/models/final/forest_acoustic_int8.tflite"
meta = json.load(open("ml/models/final/final_metadata.json")); mean, std = meta["feature_mean"], meta["feature_std"]
df = pd.read_csv("ml/datasets/v1/test_v1.csv"); df = df[df.quality_status == "OK"]
sub = pd.concat([df[df["class"] == c].sample(n=min(per_class, (df["class"] == c).sum()), random_state=3) for c in ("background", "chainsaw", "gunshot")])
ex = get_feature_extractor()
it = tf.lite.Interpreter(model_path=MP); it.allocate_tensors(); i = it.get_input_details()[0]; o = it.get_output_details()[0]; sc, zp = i["quantization"]
tens, py = [], []
for _, r in sub.iterrows():
    a, _ = sf.read("ml/" + r["processed_path"] if not r["processed_path"].startswith("ml/") else r["processed_path"], dtype="float32")
    t = np.round(((ex.extract_mel_spectrogram(a, 16000).astype(np.float32) - mean) / std)[..., None].astype(np.float32) / sc + zp).astype(np.int8)
    it.set_tensor(i["index"], t[None]); it.invoke(); py.append(it.get_tensor(o["index"])[0].astype(int)); tens.append(t.reshape(-1))
py = np.array(py); labels = np.array(sub["class"].map({"background": 0, "chainsaw": 1, "gunshot": 2}))
stdin = "\n".join(" ".join(map(str, t)) for t in tens) + "\n"
def run(mode):
    out = subprocess.run([harness, MP, mode], input=stdin, capture_output=True, text=True).stdout.strip().split("\n")
    return np.array([list(map(int, l.split())) for l in out])
for name, d in (("stock TFLM FC", run("stock")), ("per-channel FC (firmware)", run("fixed"))):
    diff = np.abs(d - py)
    print(f"{name:26s} exact={100*(diff.max(1)==0).mean():5.1f}%  max|diff|={diff.max():3d}  mean|diff|={diff.mean():.2f}  "
          f"same class as Python={100*(d.argmax(1)==py.argmax(1)).mean():.1f}%  accuracy={100*(d.argmax(1)==labels).mean():.1f}%  (n={len(py)})")
print(f"{'Python TFLite (reference)':26s} accuracy={100*(py.argmax(1)==labels).mean():.1f}%")
