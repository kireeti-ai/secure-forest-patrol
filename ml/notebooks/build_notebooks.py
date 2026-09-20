"""Generates notebooks/01..10 as real, executable notebooks that import and reuse
functions from ml/preprocessing and ml/models. Run this, then execute each with
jupyter nbconvert --execute."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _nb_builder import build, md, code

NB_DIR = Path(__file__).parent
ML_ROOT = NB_DIR.parent

HEADER = """import sys, os
from pathlib import Path
ML_ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
sys.path.insert(0, str(ML_ROOT / 'preprocessing'))
sys.path.insert(0, str(ML_ROOT / 'scripts'))
sys.path.insert(0, str(ML_ROOT / 'models'))
import numpy as np, pandas as pd, matplotlib.pyplot as plt
FIG_DIR = ML_ROOT / 'reports' / 'figures'
FIG_DIR.mkdir(parents=True, exist_ok=True)
print('ML_ROOT =', ML_ROOT)
"""

# ---------------- 01: dataset exploration ----------------
nb01 = [
    md("# 01 - Dataset Exploration\n\n**Objective:** Explore the 6 raw datasets (`c3gd`, `fsc22`, `rodopi`, "
       "`esc50_hf`, `rfcx_frugalai`, `sensing_forest`) and the frozen v1 manifest to understand class "
       "balance, per-source contribution, and duration statistics."),
    code(HEADER),
    md("## Load the frozen v1 master manifest"),
    code("master = pd.read_csv(ML_ROOT / 'datasets' / 'v1' / 'master_v1.csv', low_memory=False)\n"
         "print('Total segments:', len(master))\n"
         "print('Total recordings:', master['original_recording_id'].nunique())\n"
         "master.head()"),
    md("## Class distribution"),
    code("class_counts = master['class'].value_counts()\n"
         "print(class_counts)\n"
         "fig, ax = plt.subplots(figsize=(5,4))\n"
         "class_counts.plot(kind='bar', ax=ax, color=['#4C72B0','#DD8452','#55A868'])\n"
         "ax.set_title('Segment count per class (master_v1)')\n"
         "ax.set_ylabel('segments')\n"
         "plt.tight_layout()\n"
         "plt.savefig(FIG_DIR / '01_class_distribution.png', dpi=120)\n"
         "plt.show()"),
    md("## Per-dataset contribution"),
    code("ct = pd.crosstab(master['dataset_id'], master['class'])\n"
         "print(ct)\n"
         "fig, ax = plt.subplots(figsize=(7,4))\n"
         "ct.plot(kind='bar', stacked=True, ax=ax)\n"
         "ax.set_title('Per-dataset segment contribution by class')\n"
         "plt.tight_layout()\n"
         "plt.savefig(FIG_DIR / '01_per_dataset_contribution.png', dpi=120)\n"
         "plt.show()"),
    md("## Duration statistics"),
    code("print(master['duration'].describe())\n"
         "print('Total duration (hours):', master['duration'].sum()/3600)"),
    md("## Conclusion\n\nThe dataset is heavily background-dominated (as expected for real forest "
       "acoustic monitoring), with chainsaw the second-most represented class and gunshot the rarest. "
       "This motivates class-weighted training in notebooks 04/05/06. See "
       "`reports/DATASET_V1_REPORT.md` for the full per-dataset breakdown and labeling-mapping "
       "documentation."),
]

# ---------------- 02: preprocessing and features ----------------
nb02 = [
    md("# 02 - Preprocessing and Feature Extraction\n\n**Objective:** Demonstrate the audio "
       "preprocessing pipeline (`preprocessing/audio_preprocess.py`) and feature extraction "
       "(`preprocessing/feature_extraction.py`) on a few real example clips, and visualize the "
       "resulting MFCC / Mel-spectrogram features."),
    code(HEADER),
    code("from feature_extraction import get_feature_extractor\n"
         "import soundfile as sf\n"
         "extractor = get_feature_extractor()"),
    md("`get_feature_extractor()` returns a `FeatureExtractor` configured from "
       "`configs/preprocessing.yaml` (16kHz, 13 MFCCs, 40 Mel bins, 512-point FFT, 160-sample hop "
       "= 10ms). `.extract_mfcc` / `.extract_mel_spectrogram` operate on a 1D numpy waveform."),
    md("## Load one real example per class from the processed v1 manifest"),
    code("master = pd.read_csv(ML_ROOT / 'datasets' / 'v1' / 'master_v1.csv', low_memory=False)\n"
         "examples = {}\n"
         "for cls in ['background', 'chainsaw', 'gunshot']:\n"
         "    row = master[master['class'] == cls].iloc[0]\n"
         "    examples[cls] = ML_ROOT / row['processed_path']\n"
         "examples"),
    md("## Extract and visualize MFCC + Mel-spectrogram for each class"),
    code("fig, axes = plt.subplots(3, 2, figsize=(10, 9))\n"
         "for i, (cls, path) in enumerate(examples.items()):\n"
         "    audio, sr = sf.read(path)\n"
         "    mfcc = extractor.extract_mfcc(audio, sr)\n"
         "    mel = extractor.extract_mel_spectrogram(audio, sr)\n"
         "    axes[i,0].imshow(mfcc, aspect='auto', origin='lower'); axes[i,0].set_title(f'{cls} MFCC')\n"
         "    axes[i,1].imshow(mel, aspect='auto', origin='lower'); axes[i,1].set_title(f'{cls} Mel (dB)')\n"
         "plt.tight_layout()\n"
         "plt.savefig(FIG_DIR / '02_features_by_class.png', dpi=120)\n"
         "plt.show()"),
    md("## Digital audio filter: before / after\n\n`apply_filter` (from `preprocessing/audio_filter.py`, the ONE "
       "shared implementation used by preprocessing and documented for the ESP32) applies a causal 2nd-order "
       "Butterworth high-pass (80 Hz) to the continuous 16 kHz mono stream, before 1 s windowing. Below: its "
       "frequency response, then the same frozen-v1 segment without (A) and with (B) the filter "
       "(B comes from `datasets/processed_filtered/`, generated by `preprocessing/run_filtered_preprocess.py`)."),
    code("from audio_filter import design_filter, biquad_coefficients\n"
         "from scipy.signal import sosfreqz\n"
         "print(biquad_coefficients())\n"
         "w, h = sosfreqz(design_filter(), worN=2048, fs=16000)\n"
         "fig, ax = plt.subplots(figsize=(6,3.5))\n"
         "ax.semilogx(w[1:], 20*np.log10(abs(h[1:]))); ax.axvline(80, ls='--', c='gray')\n"
         "ax.set_ylim(-40, 3); ax.set_xlabel('Hz'); ax.set_ylabel('dB'); ax.set_title('High-pass response (2nd-order Butterworth, fc=80 Hz)')\n"
         "plt.tight_layout(); plt.savefig(FIG_DIR/'02_filter_response.png', dpi=120); plt.show()"),
    code("fig, axes = plt.subplots(3, 2, figsize=(11, 9))\n"
         "for i, cls in enumerate(['background', 'chainsaw', 'gunshot']):\n"
         "    row = master[master['class'] == cls].iloc[0]\n"
         "    a, sr = sf.read(ML_ROOT / row['processed_path'])\n"
         "    b, _ = sf.read(ML_ROOT / 'datasets' / 'processed_filtered' / (row['sample_id'] + '.wav'))\n"
         "    t = np.arange(len(a)) / sr\n"
         "    axes[i,0].plot(t, a, lw=.6, label='A no filter'); axes[i,0].plot(t, b, lw=.6, alpha=.8, label='B filtered')\n"
         "    axes[i,0].set_title(f'{cls}: waveform'); axes[i,0].legend(loc='upper right')\n"
         "    for x, lab in [(a,'A'), (b,'B')]:\n"
         "        f = np.fft.rfftfreq(len(x), 1/sr); m = 20*np.log10(np.abs(np.fft.rfft(x*np.hanning(len(x))))+1e-9)\n"
         "        axes[i,1].semilogx(f[1:], m[1:], lw=.7, label=lab)\n"
         "    axes[i,1].set_title(f'{cls}: spectrum (dB)'); axes[i,1].set_xlim(10, 8000); axes[i,1].axvline(80, ls='--', c='gray'); axes[i,1].legend()\n"
         "plt.tight_layout(); plt.savefig(FIG_DIR/'02_filter_before_after.png', dpi=120); plt.show()"),
    md("## Verify feature shapes match config expectations"),
    code("shapes = extractor.get_feature_shapes(1.0, 16000)\n"
         "print('Expected shapes for a 1.0s window at 16kHz:', shapes)"),
    md("## Conclusion\n\nMFCC and Mel-spectrogram features are extracted consistently across classes "
       "with a fixed shape (13, 101) and (40, 101) respectively for every 1.0s / 16kHz segment. These "
       "are the two feature representations compared for baseline vs CNN modeling in notebooks 04-06."),
]

# ---------------- 03: dataset validation ----------------
nb03 = [
    md("# 03 - Dataset Validation (Quality + Leakage Gates)\n\n**Objective:** Run the two quality "
       "gates required before model training: `scripts/audit_dataset.py` (raw file corruption / "
       "sample-rate / clipping checks) and `scripts/validate_leakage.py` (no source recording appears "
       "in more than one of train/validation/test/external_test)."),
    code(HEADER),
    md("## Leakage validation\n\nImports and calls `validate_leakage()` directly from "
       "`scripts/validate_leakage.py` so the pass/fail result printed below is a real, live check "
       "against the frozen `datasets/v1/*.csv` splits, not a copied log."),
    code("import validate_leakage\n"
         "result = validate_leakage.validate_leakage()\n"
         "assert result, 'Leakage validation failed!'"),
    md("## Dataset quality audit summary\n\nThe raw-file audit (`scripts/audit_dataset.py`) was run "
       "separately (it scans all 15,103 raw files and takes several minutes); we load its generated "
       "report here."),
    code("report_path = ML_ROOT / 'reports' / 'dataset_quality_report.md'\n"
         "print(report_path.read_text()[:2000])"),
    md("## Split sizes sanity check"),
    code("for name in ['train','validation','test','external_test']:\n"
         "    d = pd.read_csv(ML_ROOT/'datasets'/'v1'/f'{name}_v1.csv', low_memory=False)\n"
         "    print(name, len(d), 'segments,', d['original_recording_id'].nunique(), 'recordings')\n"
         "    print(d['class'].value_counts().to_dict())"),
    md("## Conclusion\n\nBoth quality gates pass: 0 corrupted/zero-length files in the raw audit, and "
       "0 leaked `original_recording_id`s across train/validation/test/external_test. The frozen v1 "
       "dataset is safe to train on."),
]

# ---------------- 04: baseline training ----------------
nb04 = [
    md("# 04 - Baseline Training (MFCC statistics + Logistic Regression)\n\n**Objective:** Train and "
       "evaluate the MFCC-statistics + Logistic Regression baseline "
       "(`models/baseline/train_baseline.py`) directly in this notebook so the reported metrics come "
       "from a live re-run."),
    code(HEADER),
    code("sys.path.insert(0, str(ML_ROOT/'models'/'baseline'))\n"
         "import numpy as np\n"
         "from sklearn.linear_model import LogisticRegression\n"
         "from sklearn.metrics import accuracy_score, f1_score, classification_report\n"
         "CACHE_DIR = ML_ROOT / 'datasets' / 'features_cache'\n"
         "CLASSES = ['background','chainsaw','gunshot']"),
    md("`mfcc_stats()` reduces each (13, T) MFCC matrix to a 26-dim vector (mean + std per "
       "coefficient over time) — a simple, classic statistical-feature baseline."),
    code("def mfcc_stats(mfcc_arr):\n"
         "    return np.concatenate([mfcc_arr.mean(axis=2), mfcc_arr.std(axis=2)], axis=1)\n\n"
         "def load_split(name):\n"
         "    d = np.load(CACHE_DIR / f'{name}.npz', allow_pickle=True)\n"
         "    return mfcc_stats(d['mfcc']), d['y']\n\n"
         "X_train, y_train = load_split('train')\n"
         "X_val, y_val = load_split('validation')\n"
         "X_test, y_test = load_split('test')\n"
         "print(X_train.shape, X_val.shape, X_test.shape)"),
    code("mean, std = X_train.mean(0), X_train.std(0) + 1e-8\n"
         "model = LogisticRegression(max_iter=2000, class_weight='balanced', random_state=42)\n"
         "model.fit((X_train-mean)/std, y_train)\n"
         "val_pred = model.predict((X_val-mean)/std)\n"
         "test_pred = model.predict((X_test-mean)/std)\n"
         "print('Validation macro-F1:', f1_score(y_val, val_pred, average='macro'))\n"
         "print('Test macro-F1:', f1_score(y_test, test_pred, average='macro'))\n"
         "print(classification_report(y_test, test_pred, target_names=CLASSES, zero_division=0))"),
    md("## Confusion matrix (test)"),
    code("from sklearn.metrics import confusion_matrix\n"
         "cm = confusion_matrix(y_test, test_pred)\n"
         "fig, ax = plt.subplots(figsize=(4,4))\n"
         "ax.imshow(cm, cmap='Blues')\n"
         "for i in range(3):\n"
         "    for j in range(3):\n"
         "        ax.text(j, i, cm[i,j], ha='center', va='center')\n"
         "ax.set_xticks(range(3)); ax.set_xticklabels(CLASSES)\n"
         "ax.set_yticks(range(3)); ax.set_yticklabels(CLASSES)\n"
         "ax.set_xlabel('Predicted'); ax.set_ylabel('True'); ax.set_title('Baseline confusion matrix (test)')\n"
         "plt.tight_layout()\n"
         "plt.savefig(FIG_DIR / '04_baseline_confusion_matrix.png', dpi=120)\n"
         "plt.show()"),
    md("## Conclusion\n\nThe MFCC-statistics + Logistic Regression baseline gives a fast, "
       "interpretable reference point. Full validation/test/external-test metrics (matching this "
       "live run) are saved to `models/baseline/baseline_results.json`."),
]

# ---------------- 05: compact CNN training ----------------
nb05 = [
    md("# 05 - Compact CNN Training (Mel-spectrogram)\n\n**Objective:** Train the small "
       "Conv-BN-ReLU-Pool x2 CNN (`models/train_cnn.py build_compact_cnn`) on Mel-spectrogram "
       "features, reusing the exact model-building and augmentation functions used by the "
       "full training script."),
    code(HEADER),
    code("sys.path.insert(0, str(ML_ROOT/'models'))\n"
         "import tensorflow as tf\n"
         "from tensorflow import keras\n"
         "from train_cnn import build_compact_cnn, load_split, normalize, CLASSES\n"
         "np.random.seed(42); tf.random.set_seed(42)"),
    md("`build_compact_cnn(input_shape, n_classes)` builds Conv(16)->BN->ReLU->Pool -> "
       "Conv(32)->BN->ReLU->Pool -> GlobalAvgPool -> Dense(32) -> Dense(3, softmax) — imported "
       "directly from the training script, not reimplemented here."),
    code("mel_train, y_train = load_split('train')\n"
         "mel_val, y_val = load_split('validation')\n"
         "mean, std = mel_train.mean(), mel_train.std() + 1e-8\n"
         "X_train = normalize(mel_train, mean, std)[..., np.newaxis].astype(np.float32)\n"
         "X_val = normalize(mel_val, mean, std)[..., np.newaxis].astype(np.float32)\n"
         "input_shape = X_train.shape[1:]\n"
         "model = build_compact_cnn(input_shape, len(CLASSES))\n"
         "model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])\n"
         "model.summary()"),
    md("## Short live training run (5 epochs, for notebook demonstration; the full 15-epoch "
       "early-stopped run used for model selection is `models/compact_cnn/`)"),
    code("from sklearn.utils.class_weight import compute_class_weight\n"
         "cw = compute_class_weight('balanced', classes=np.arange(3), y=y_train)\n"
         "class_weight = {i: w for i, w in enumerate(cw)}\n"
         "history = model.fit(X_train, y_train, validation_data=(X_val, y_val), epochs=5,\n"
         "                     batch_size=32, class_weight=class_weight, verbose=2)"),
    code("fig, ax = plt.subplots(figsize=(5,4))\n"
         "ax.plot(history.history['loss'], label='train loss')\n"
         "ax.plot(history.history['val_loss'], label='val loss')\n"
         "ax.legend(); ax.set_title('Compact CNN training curve (this notebook run)')\n"
         "plt.tight_layout()\n"
         "plt.savefig(FIG_DIR / '05_compact_cnn_training_curve.png', dpi=120)\n"
         "plt.show()"),
    md("## Full training run results (models/compact_cnn/compact_cnn_metadata.json)"),
    code("import json\n"
         "meta = json.load(open(ML_ROOT/'models'/'compact_cnn'/'compact_cnn_metadata.json'))\n"
         "print('Params:', meta['n_params'], 'Weights size (bytes):', meta['weights_size_bytes'])\n"
         "print('Validation macro-F1 (full run):', meta['validation_metrics']['macro_f1'])\n"
         "print('Test macro-F1 (full run):', meta['test_metrics']['macro_f1'])"),
    md("## Conclusion\n\nThe compact CNN (6,147 params, ~24KB FP32 weights) trains successfully on "
       "Mel-spectrogram features. Compared against the baseline and the final depthwise-separable "
       "model in notebook 06."),
]

# ---------------- 06: model evaluation / comparison ----------------
nb06 = [
    md("# 06 - Model Evaluation & Comparison\n\n**Objective:** Load the three trained models "
       "(baseline, compact_cnn, final) and compare their validation/test metrics, parameter counts, "
       "and sizes side by side, selecting the final model by VALIDATION metrics only."),
    code(HEADER),
    code("import json\n"
         "baseline = json.load(open(ML_ROOT/'models'/'baseline'/'baseline_results.json'))\n"
         "cnn = json.load(open(ML_ROOT/'models'/'compact_cnn'/'compact_cnn_metadata.json'))\n"
         "final = json.load(open(ML_ROOT/'models'/'final'/'final_metadata.json'))"),
    code("rows = []\n"
         "rows.append(['baseline (LogReg+MFCC)', None, None,\n"
         "             baseline['validation']['macro_f1'], baseline['test']['macro_f1'], baseline['external_test']['macro_f1']])\n"
         "rows.append(['compact_cnn (Mel)', cnn['n_params'], cnn['weights_size_bytes'],\n"
         "             cnn['validation_metrics']['macro_f1'], cnn['test_metrics']['macro_f1'], cnn['external_test_metrics']['macro_f1']])\n"
         "rows.append(['final (depthwise-sep, Mel)', final['n_params'], final['weights_size_bytes'],\n"
         "             final['validation_metrics']['macro_f1'], final['test_metrics']['macro_f1'], final['external_test_metrics']['macro_f1']])\n"
         "comp = pd.DataFrame(rows, columns=['model','params','weights_bytes','val_macroF1','test_macroF1','ext_macroF1'])\n"
         "comp"),
    md("## Model selection\n\nSelection uses **validation macro-F1 only** (test/external-test are "
       "reported once for the record, never used to pick a model)."),
    code("best = comp.loc[comp['val_macroF1'].idxmax()]\n"
         "print('Selected model (highest validation macro-F1):', best['model'])"),
    md("## Per-class F1 / recall for the selected final model (test set)"),
    code("print('Per-class F1:', final['test_metrics']['per_class_f1'])\n"
         "print('Per-class recall:', final['test_metrics']['per_class_recall'])\n"
         "cm = np.array(final['test_metrics']['confusion_matrix'])\n"
         "fig, ax = plt.subplots(figsize=(4,4))\n"
         "ax.imshow(cm, cmap='Greens')\n"
         "CLASSES=['background','chainsaw','gunshot']\n"
         "for i in range(3):\n"
         "    for j in range(3):\n"
         "        ax.text(j, i, cm[i,j], ha='center', va='center')\n"
         "ax.set_xticks(range(3)); ax.set_xticklabels(CLASSES)\n"
         "ax.set_yticks(range(3)); ax.set_yticklabels(CLASSES)\n"
         "ax.set_title('Final model confusion matrix (test)')\n"
         "plt.tight_layout()\n"
         "plt.savefig(FIG_DIR / '06_final_model_confusion_matrix.png', dpi=120)\n"
         "plt.show()"),
    md("## Conclusion\n\nThe final depthwise-separable model has the highest validation macro-F1 "
       "among the three candidates and the smallest footprint (1,315 params, ~5KB FP32 weights), so "
       "it was selected as the deployment candidate for TFLite conversion (notebook 08)."),
]

# ---------------- 07: robustness + external test ----------------
nb07 = [
    md("# 07 - Robustness & External Test Evaluation\n\n**Objective:** Evaluate the final model on "
       "the held-out `external_test_v1` set (different sources than train/val/test) and under "
       "synthetic noise at clean/moderate/strong SNR levels, reusing `models/robustness_eval.py`."),
    code(HEADER),
    code("import json\n"
         "final = json.load(open(ML_ROOT/'models'/'final'/'final_metadata.json'))\n"
         "print('External test metrics (from full training run):')\n"
         "print(json.dumps(final['external_test_metrics']['per_class_f1'], indent=2))\n"
         "print('Macro-F1:', final['external_test_metrics']['macro_f1'])"),
    md("## Noise robustness (from `reports/ROBUSTNESS_REPORT.json`, produced by "
       "`models/robustness_eval.py`, which adds synthetic Gaussian noise to test-set Mel features "
       "at eval time only — the frozen test_v1 files on disk are never modified)"),
    code("robustness = json.load(open(ML_ROOT/'reports'/'ROBUSTNESS_REPORT.json'))\n"
         "rob_df = pd.DataFrame(robustness).T[['accuracy','macro_f1','background_false_alarm_rate']]\n"
         "rob_df"),
    code("fig, ax = plt.subplots(figsize=(5,4))\n"
         "rob_df[['accuracy','macro_f1']].plot(kind='bar', ax=ax)\n"
         "ax.set_title('Final model robustness to synthetic noise')\n"
         "ax.set_xticklabels(rob_df.index, rotation=0)\n"
         "plt.tight_layout()\n"
         "plt.savefig(FIG_DIR / '07_robustness.png', dpi=120)\n"
         "plt.show()"),
    md("## Conclusion\n\nAccuracy degrades as expected under stronger synthetic noise (a compact "
       "1,315-parameter model has limited noise margin). External-test performance (different "
       "sources entirely) is reported honestly alongside in-domain test performance rather than "
       "cherry-picked. Full numbers: `reports/ROBUSTNESS_REPORT.md`."),
]

# ---------------- 08: quantization and tflite ----------------
nb08 = [
    md("# 08 - Quantization & TFLite Conversion\n\n**Objective:** Convert the final FP32 Keras model "
       "to TFLite (numerical-tolerance check) and then INT8 (representative dataset from TRAIN only), "
       "reusing the exact conversion logic in `models/convert_tflite.py`, and inspect the resulting "
       "`.tflite` file."),
    code(HEADER),
    code("import json, tensorflow as tf\n"
         "quant = json.load(open(ML_ROOT/'reports'/'QUANTIZATION_REPORT.json'))\n"
         "print(json.dumps({k:v for k,v in quant.items() if 'classification_report' not in k}, indent=2))"),
    md("## Load and inspect the INT8 .tflite model directly"),
    code("interp = tf.lite.Interpreter(model_path=str(ML_ROOT/'models'/'final'/'forest_acoustic_int8.tflite'))\n"
         "interp.allocate_tensors()\n"
         "print('Input:', interp.get_input_details()[0])\n"
         "print('Output:', interp.get_output_details()[0])"),
    md("## Size comparison"),
    code("sizes = {'FP32 Keras weights (bytes)': quant['fp32_keras_weights_bytes'],\n"
         "         'FP32 .tflite (bytes)': quant['fp32_tflite_bytes'],\n"
         "         'INT8 .tflite (bytes)': quant['int8_tflite_bytes']}\n"
         "fig, ax = plt.subplots(figsize=(5,4))\n"
         "ax.bar(sizes.keys(), sizes.values())\n"
         "ax.set_ylabel('bytes'); ax.set_title('Model size: FP32 vs INT8')\n"
         "plt.xticks(rotation=30, ha='right')\n"
         "plt.tight_layout()\n"
         "plt.savefig(FIG_DIR / '08_model_size_comparison.png', dpi=120)\n"
         "plt.show()"),
    md("## Conclusion\n\nThe final INT8 TFLite model is ~13KB — far under the ~200KB ESP32-S3 flash "
       "budget target — with 98.2% prediction agreement against the FP32 Keras model on the frozen "
       "test set. Full details: `reports/QUANTIZATION_REPORT.md`."),
]

# ---------------- 09: tflite micro validation ----------------
nb09 = [
    md("# 09 - TFLite Micro Compatibility Validation\n\n**Objective:** Cross-check every operator in "
       "the final INT8 `.tflite` model against the TFLite Micro supported-ops list, and validate "
       "the quantized model's predictions against the desktop `tf.lite.Interpreter` as a stand-in "
       "for an embedded TFLite Micro runtime (no physical embedded runtime is available in this "
       "environment)."),
    code(HEADER),
    code("import tensorflow as tf, json\n"
         "TFLM_SUPPORTED_OPS = {'CONV_2D','DEPTHWISE_CONV_2D','FULLY_CONNECTED','AVERAGE_POOL_2D',\n"
         "    'MAX_POOL_2D','SOFTMAX','RESHAPE','QUANTIZE','DEQUANTIZE','MEAN','ADD','MUL','RELU',\n"
         "    'RELU6','PAD','CONCATENATION','LOGISTIC'}\n"
         "interp = tf.lite.Interpreter(\n"
         "    model_path=str(ML_ROOT/'models'/'final'/'forest_acoustic_int8.tflite'),\n"
         "    experimental_op_resolver_type=tf.lite.experimental.OpResolverType.BUILTIN_WITHOUT_DEFAULT_DELEGATES)\n"
         "interp.allocate_tensors()\n"
         "ops_used = {op['op_name'] for op in interp._get_ops_details()}\n"
         "unsupported = ops_used - TFLM_SUPPORTED_OPS\n"
         "print('Ops used:', sorted(ops_used))\n"
         "print('Unsupported TFLM ops:', sorted(unsupported) if unsupported else 'NONE - all ops supported')"),
    md("## Prediction-consistency check against Keras FP32 (test set)\n\nSince no physical ESP32-S3 "
       "is available, `tf.lite.Interpreter` running the exact INT8 operator graph is used as the "
       "stand-in embedded-runtime validator."),
    code("import numpy as np\n"
         "sys.path.insert(0, str(ML_ROOT/'models'))\n"
         "from train_cnn import load_split\n"
         "final_meta = json.load(open(ML_ROOT/'models'/'final'/'final_metadata.json'))\n"
         "mean, std = final_meta['feature_mean'], final_meta['feature_std']\n"
         "mel_test, y_test = load_split('test')\n"
         "X_test = ((mel_test-mean)/std)[..., np.newaxis].astype(np.float32)\n"
         "keras_model = tf.keras.models.load_model(ML_ROOT/'models'/'final'/'final.keras')\n"
         "keras_pred = np.argmax(keras_model.predict(X_test, verbose=0), axis=1)\n"
         "in_d = interp.get_input_details()[0]; out_d = interp.get_output_details()[0]\n"
         "scale, zero = in_d['quantization']\n"
         "int8_pred = []\n"
         "for i in range(len(X_test)):\n"
         "    xq = np.round(X_test[i:i+1]/scale + zero).astype(np.int8)\n"
         "    interp.set_tensor(in_d['index'], xq)\n"
         "    interp.invoke()\n"
         "    int8_pred.append(np.argmax(interp.get_tensor(out_d['index'])[0]))\n"
         "int8_pred = np.array(int8_pred)\n"
         "agreement = (keras_pred == int8_pred).mean()\n"
         "print(f'Keras FP32 vs INT8-TFLite-Interpreter prediction agreement: {agreement:.4f}')"),
    md("## Conclusion\n\nAll operators in the final INT8 model (`CONV_2D`, `DEPTHWISE_CONV_2D`, "
       "`FULLY_CONNECTED`, `MAX_POOL_2D`, `MEAN`, `SOFTMAX`) are in the TFLite Micro commonly-"
       "supported op set — no architecture changes were needed. Desktop-interpreter validation shows "
       "high agreement with the FP32 model, but this is **not** a substitute for running on actual "
       "TFLite Micro / ESP32-S3 hardware, which was not available in this environment (see "
       "'HARDWARE DEPLOYMENT BLOCKED' in `reports/FINAL_MODEL_REPORT.md`)."),
]

# ---------------- 10: audio file demo ----------------
nb10 = [
    md("# 10 - Audio File Demo (software-only, no hardware)\n\n**Objective:** Pick one real example "
       "audio clip per class (gunshot / chainsaw / background) from the dataset, run it through the "
       "final INT8 TFLite model exactly as an embedded device would (feature extraction -> "
       "quantize -> invoke -> dequantize -> argmax), and print the predicted class + confidence."),
    code(HEADER),
    code("import soundfile as sf, tensorflow as tf, json\n"
         "from feature_extraction import get_feature_extractor\n"
         "extractor = get_feature_extractor()\n"
         "final_meta = json.load(open(ML_ROOT/'models'/'final'/'final_metadata.json'))\n"
         "mean, std = final_meta['feature_mean'], final_meta['feature_std']\n"
         "CLASSES = ['background', 'chainsaw', 'gunshot']\n"
         "interp = tf.lite.Interpreter(model_path=str(ML_ROOT/'models'/'final'/'forest_acoustic_int8.tflite'))\n"
         "interp.allocate_tensors()\n"
         "in_d = interp.get_input_details()[0]; out_d = interp.get_output_details()[0]\n"
         "in_scale, in_zero = in_d['quantization']\n"
         "out_scale, out_zero = out_d['quantization']"),
    code("master = pd.read_csv(ML_ROOT/'datasets'/'v1'/'test_v1.csv', low_memory=False)\n"
         "examples = {cls: ML_ROOT / master[master['class']==cls].iloc[0]['processed_path'] for cls in CLASSES}\n"
         "examples"),
    md("## Run inference on each example clip"),
    code("def predict(wav_path):\n"
         "    audio, sr = sf.read(wav_path)\n"
         "    mel = extractor.extract_mel_spectrogram(audio, sr)\n"
         "    T = mel.shape[1]\n"
         "    x = ((mel - mean) / std)[np.newaxis, ..., np.newaxis].astype(np.float32)\n"
         "    xq = np.round(x / in_scale + in_zero).astype(np.int8)\n"
         "    interp.set_tensor(in_d['index'], xq)\n"
         "    interp.invoke()\n"
         "    out_q = interp.get_tensor(out_d['index'])[0]\n"
         "    probs = (out_q.astype(np.float32) - out_zero) * out_scale\n"
         "    probs = np.exp(probs) / np.exp(probs).sum()  # renormalize as a proxy confidence\n"
         "    pred_idx = int(np.argmax(out_q))\n"
         "    return CLASSES[pred_idx], float(probs[pred_idx])\n\n"
         "for cls, path in examples.items():\n"
         "    pred_class, conf = predict(path)\n"
         "    print(f'True: {cls:12s} -> Predicted: {pred_class:12s} (confidence proxy: {conf:.3f})  [{path.name}]')"),
    md("## Conclusion\n\nThis is a pure software demonstration of the end-to-end inference path "
       "(feature extraction -> INT8 quantize -> TFLite invoke -> class prediction) that would run "
       "on-device. No physical ESP32-S3/INMP441 hardware was used or available — real-time I2S "
       "capture and on-device execution are explicitly listed as blocked in "
       "`reports/FINAL_MODEL_REPORT.md`."),
]


nb11 = [
    md("# 11 - Digital Filter A/B Comparison\n\n**Objective:** Compare the unfiltered pipeline (A) with the causal 80 Hz "
       "high-pass pipeline (B) on the SAME frozen v1 splits, same final architecture and hyperparameters, seeds 42/1/2 "
       "(`models/ab_filter_experiment.py`; results in `reports/ab_filter_results.json`). The v1 model in `models/final` is untouched."),
    code(HEADER),
    code("import json\n"
         "res = json.load(open(ML_ROOT/'reports'/'ab_filter_results.json'))\n"
         "C = ['background','chainsaw','gunshot']\n"
         "rows = []\n"
         "for k, r in res.items():\n"
         "    v, seed = k.split('_seed')\n"
         "    for split in ['val','test','external']:\n"
         "        m = r[split]\n"
         "        rows.append(dict(variant=v, seed=int(seed), split=split, macro_f1=m['macro_f1'], bg_f1=m['per_class_f1']['background'],\n"
         "            chainsaw_f1=m['per_class_f1']['chainsaw'], gunshot_f1=m['per_class_f1']['gunshot'],\n"
         "            chainsaw_recall=m['per_class_recall']['chainsaw'], gunshot_recall=m['per_class_recall']['gunshot']))\n"
         "df = pd.DataFrame(rows)\n"
         "df.round(3)"),
    md("## Mean +/- std over seeds"),
    code("summ = df.groupby(['split','variant']).agg(['mean','std']).drop(columns='seed').round(3)\n"
         "summ"),
    code("fig, axes = plt.subplots(1, 3, figsize=(12,3.8))\n"
         "for ax, split in zip(axes, ['val','test','external']):\n"
         "    d = df[df.split==split]\n"
         "    for v, c in [('A','#4C72B0'),('B','#DD8452')]:\n"
         "        x = d[d.variant==v]; ax.scatter([v]*len(x), x.macro_f1, c=c); ax.hlines(x.macro_f1.mean(), -.2 if v=='A' else .8, .2 if v=='A' else 1.2, colors=c)\n"
         "    ax.set_title(f'{split} macro-F1 (per seed)')\n"
         "plt.tight_layout(); plt.savefig(FIG_DIR/'11_filter_ab_macro_f1.png', dpi=120); plt.show()"),
    md("## Robustness (INT8 model, clean / 15 dB / 5 dB feature-domain noise on test_v1)"),
    code("rob = []\n"
         "for k, r in res.items():\n"
         "    v, seed = k.split('_seed')\n"
         "    for lvl, m in r['robustness'].items():\n"
         "        rob.append(dict(variant=v, seed=int(seed), level=lvl, acc=m['accuracy'], macro_f1=m['macro_f1']))\n"
         "rob = pd.DataFrame(rob)\n"
         "rob.groupby(['level','variant'])[['acc','macro_f1']].agg(['mean','std']).round(3)"),
    md("## Conclusion\n\nSee `reports/FILTER_REPORT.md` for the measured verdict. The comparison above is over three seeds per "
       "variant; differences smaller than the seed-to-seed standard deviation should be read as neutral."),
]

NOTEBOOKS = {
    '01_dataset_exploration.ipynb': nb01,
    '02_preprocessing_and_features.ipynb': nb02,
    '03_dataset_validation.ipynb': nb03,
    '04_baseline_training.ipynb': nb04,
    '05_compact_cnn_training.ipynb': nb05,
    '06_model_evaluation.ipynb': nb06,
    '07_robustness_and_external_test.ipynb': nb07,
    '08_quantization_and_tflite.ipynb': nb08,
    '09_tflite_micro_validation.ipynb': nb09,
    '10_audio_file_demo.ipynb': nb10,
    '11_filter_ab_comparison.ipynb': nb11,
}

if __name__ == "__main__":
    for fname, cells in NOTEBOOKS.items():
        build(cells, NB_DIR / fname)
