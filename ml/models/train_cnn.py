#!/usr/bin/env python3
"""
Train a Keras CNN (compact_cnn or final depthwise-separable variant) on cached
Mel-spectrogram features. Reproducible: fixed seed=42, documented optimizer/
LR/batch/epochs, class weighting, early stopping on val loss, simple
training-only augmentation (ml/models/augment.py).

Usage: python train_cnn.py --variant compact_cnn|final --epochs 15
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow import keras
from sklearn.metrics import (accuracy_score, f1_score, precision_score, recall_score,
                              balanced_accuracy_score, confusion_matrix, classification_report)
from sklearn.utils.class_weight import compute_class_weight

ML_ROOT = Path(__file__).parent.parent
CACHE_DIR = ML_ROOT / "datasets" / "features_cache"
CLASSES = ["background", "chainsaw", "gunshot"]
BACKGROUND_IDX = CLASSES.index("background")
SEED = 42  # default; override with --seed

sys.path.insert(0, str(Path(__file__).parent))
from augment import augment_batch  # noqa: E402

def load_split(name, cache_dir=None):
    d = np.load((Path(cache_dir) if cache_dir else CACHE_DIR) / f"{name}.npz", allow_pickle=True)
    return d['mel'], d['y']


def normalize(mel, mean, std):
    return (mel - mean) / std


def build_compact_cnn(input_shape, n_classes):
    inputs = keras.Input(shape=input_shape)
    x = keras.layers.Conv2D(16, 3, padding='same')(inputs)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.ReLU()(x)
    x = keras.layers.MaxPool2D(2)(x)

    x = keras.layers.Conv2D(32, 3, padding='same')(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.ReLU()(x)
    x = keras.layers.MaxPool2D(2)(x)

    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.Dense(32, activation='relu')(x)
    outputs = keras.layers.Dense(n_classes, activation='softmax')(x)
    return keras.Model(inputs, outputs, name="compact_cnn")


def build_final_model(input_shape, n_classes):
    """Depthwise-separable compact model sized for ESP32-S3 / INT8 <200KB target."""
    inputs = keras.Input(shape=input_shape)
    x = keras.layers.Conv2D(8, 3, strides=2, padding='same')(inputs)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.ReLU()(x)

    x = keras.layers.DepthwiseConv2D(3, padding='same')(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.ReLU()(x)
    x = keras.layers.Conv2D(16, 1, padding='same')(x)  # pointwise
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.ReLU()(x)
    x = keras.layers.MaxPool2D(2)(x)

    x = keras.layers.DepthwiseConv2D(3, padding='same')(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.ReLU()(x)
    x = keras.layers.Conv2D(16, 1, padding='same')(x)  # pointwise
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.ReLU()(x)

    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.Dense(16, activation='relu')(x)
    outputs = keras.layers.Dense(n_classes, activation='softmax')(x)
    return keras.Model(inputs, outputs, name="forest_acoustic_final")


def evaluate(model, X, y, name):
    probs = model.predict(X, verbose=0)
    pred = np.argmax(probs, axis=1)
    metrics = {
        'accuracy': float(accuracy_score(y, pred)),
        'balanced_accuracy': float(balanced_accuracy_score(y, pred)),
        'macro_f1': float(f1_score(y, pred, average='macro')),
        'macro_precision': float(precision_score(y, pred, average='macro', zero_division=0)),
        'macro_recall': float(recall_score(y, pred, average='macro', zero_division=0)),
        'per_class_f1': dict(zip(CLASSES, f1_score(y, pred, average=None, labels=[0, 1, 2], zero_division=0).tolist())),
        'per_class_recall': dict(zip(CLASSES, recall_score(y, pred, average=None, labels=[0, 1, 2], zero_division=0).tolist())),
        'confusion_matrix': confusion_matrix(y, pred, labels=[0, 1, 2]).tolist(),
        'classification_report': classification_report(y, pred, labels=[0, 1, 2], target_names=CLASSES, zero_division=0),
    }
    print(f"\n=== {name} ===")
    print(f"Accuracy: {metrics['accuracy']:.4f}  Macro-F1: {metrics['macro_f1']:.4f}")
    print(metrics['classification_report'])
    return metrics


class AugmentedSequence(keras.utils.Sequence):
    def __init__(self, mel, y, batch_size, mean, std, augment=True, seed=42):
        self.mel = mel
        self.y = y
        self.batch_size = batch_size
        self.mean, self.std = mean, std
        self.augment = augment
        self.rng = np.random.RandomState(seed)
        self.indices = np.arange(len(mel))

    def __len__(self):
        return int(np.ceil(len(self.mel) / self.batch_size))

    def on_epoch_end(self):
        self.rng.shuffle(self.indices)

    def __getitem__(self, idx):
        batch_idx = self.indices[idx * self.batch_size:(idx + 1) * self.batch_size]
        mel_batch = self.mel[batch_idx]
        y_batch = self.y[batch_idx]
        if self.augment:
            mel_batch = augment_batch(mel_batch, y_batch, BACKGROUND_IDX, self.rng, prob=0.5)
        mel_batch = normalize(mel_batch, self.mean, self.std)
        X = mel_batch[..., np.newaxis].astype(np.float32)
        return X, y_batch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=['compact_cnn', 'final'], required=True)
    parser.add_argument('--epochs', type=int, default=15)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--cache-dir', default=None, help='feature cache dir (default: datasets/features_cache)')
    parser.add_argument('--out-dir', default=None, help='output dir (default: models/<variant>)')
    args = parser.parse_args()
    global SEED
    SEED = args.seed
    np.random.seed(SEED)
    tf.random.set_seed(SEED)

    mel_train, y_train = load_split("train", args.cache_dir)
    mel_val, y_val = load_split("validation", args.cache_dir)
    mel_test, y_test = load_split("test", args.cache_dir)
    mel_ext, y_ext = load_split("external_test", args.cache_dir)

    mean, std = mel_train.mean(), mel_train.std() + 1e-8

    n_mels, T = mel_train.shape[1], mel_train.shape[2]
    input_shape = (n_mels, T, 1)
    n_classes = len(CLASSES)

    class_weights_arr = compute_class_weight('balanced', classes=np.arange(n_classes), y=y_train)
    class_weight = {i: w for i, w in enumerate(class_weights_arr)}
    print("Class weights:", class_weight)

    if args.variant == 'compact_cnn':
        model = build_compact_cnn(input_shape, n_classes)
        out_dir = ML_ROOT / "models" / "compact_cnn"
    else:
        model = build_final_model(input_shape, n_classes)
        out_dir = ML_ROOT / "models" / "final"
    if args.out_dir:
        out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model.compile(optimizer=keras.optimizers.Adam(learning_rate=args.lr),
                  loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    model.summary()
    n_params = model.count_params()

    train_seq = AugmentedSequence(mel_train, y_train, args.batch_size, mean, std, augment=True, seed=SEED)
    X_val = normalize(mel_val, mean, std)[..., np.newaxis].astype(np.float32)
    X_test = normalize(mel_test, mean, std)[..., np.newaxis].astype(np.float32)
    X_ext = normalize(mel_ext, mean, std)[..., np.newaxis].astype(np.float32)

    early_stop = keras.callbacks.EarlyStopping(monitor='val_loss', patience=4, restore_best_weights=True)

    t0 = time.time()
    history = model.fit(train_seq, validation_data=(X_val, y_val), epochs=args.epochs,
                         class_weight=class_weight, callbacks=[early_stop], verbose=2)
    train_time_s = time.time() - t0

    val_metrics = evaluate(model, X_val, y_val, "validation")
    test_metrics = evaluate(model, X_test, y_test, "test")
    ext_metrics = evaluate(model, X_ext, y_ext, "external_test")

    model.save(out_dir / f"{args.variant}.keras")
    weights_size_bytes = sum(w.numpy().nbytes for w in model.weights)

    metadata = {
        'variant': args.variant,
        'architecture': model.to_json(),
        'input_shape': list(input_shape),
        'classes': CLASSES,
        'n_params': int(n_params),
        'weights_size_bytes': int(weights_size_bytes),
        'seed': SEED,
        'optimizer': 'Adam', 'lr': args.lr, 'batch_size': args.batch_size,
        'epochs_requested': args.epochs, 'epochs_ran': len(history.history['loss']),
        'train_time_s': train_time_s,
        'feature_mean': float(mean), 'feature_std': float(std),
        'class_weight': {str(k): float(v) for k, v in class_weight.items()},
        'history': {k: [float(x) for x in v] for k, v in history.history.items()},
        'validation_metrics': val_metrics,
        'test_metrics': test_metrics,
        'external_test_metrics': ext_metrics,
    }
    with open(out_dir / f"{args.variant}_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(f"\nSaved {args.variant} model + metadata to {out_dir}")
    print(f"Params: {n_params}, Weights size: {weights_size_bytes/1024:.1f} KB, Train time: {train_time_s:.1f}s")


if __name__ == "__main__":
    main()
