#!/usr/bin/env python3
"""
Audio preprocessing pipeline for SECURE FOREST PATROL

Handles per-dataset extraction logic for all 6 real datasets:
  c3gd, fsc22, rodopi, esc50_hf, rfcx_frugalai, sensing_forest

This script:
- Loads raw audio per dataset with dataset-specific labeling logic
- Resamples to 16 kHz mono
- Normalizes amplitude
- Segments into 1.0s windows with 50% overlap
- Runs quality checks (clipping / silence)
- Writes a segment-level master manifest with original_recording_id, class,
  dataset_id, and (where relevant) event/interval provenance for leakage checks
"""

import sys
import json
import yaml
import hashlib
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import soundfile as sf
import librosa
from tqdm import tqdm

warnings.filterwarnings('ignore')

SCRIPT_DIR = Path(__file__).parent
ML_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(ML_ROOT / "scripts"))
from textgrid import parse_textgrid, get_chainsaw_intervals, get_background_intervals  # noqa: E402
sys.path.insert(0, str(SCRIPT_DIR))
from audio_filter import apply_filter  # noqa: E402

CONFIG_PATH = ML_ROOT / "configs" / "preprocessing.yaml"
with open(CONFIG_PATH, 'r') as f:
    CONFIG = yaml.safe_load(f)

RAW_DIR = ML_ROOT / "datasets" / "raw"
PROCESSED_DIR = ML_ROOT / "datasets" / "processed"
INTERIM_DIR = ML_ROOT / "datasets" / "interim"
MANIFESTS_DIR = ML_ROOT / "datasets" / "manifests"
REPORTS_DIR = ML_ROOT / "reports"

# FSC22 Class Name -> our 3-class scheme (or 'discard')
FSC22_LABEL_MAP = {
    "Gunshot": "gunshot",
    "Chainsaw": "chainsaw",
    "BirdChirping": "background",
    "Frog": "background",
    "Insect": "background",
    "Rain": "background",
    "Wind": "background",
    "WaterDrops": "background",
    "Thunderstorm": "background",
    "WolfHowl": "background",
    "Squirrel": "background",
    "WingFlaping": "background",
    "Lion": "background",
    # discard: not forest-ambient / not our target classes / ambiguous
    "Fire": "discard",
    "Clapping": "discard",
    "Footsteps": "discard",
    "Speaking": "discard",
    "Whistling": "discard",
    "WoodChop": "discard",
    "Firework": "discard",
    "Handsaw": "discard",  # acoustically close to chainsaw but not chainsaw -> avoid mislabeling
    "Generator": "discard",
    "Axe": "discard",
    "VehicleEngine": "discard",
    "Helicopter": "discard",
    "TreeFalling": "discard",
    "Silence": "discard",
}

# ESC-50 category -> our scheme
ESC50_CHAINSAW = {"chainsaw"}
ESC50_BACKGROUND = {
    "chirping_birds", "rain", "wind", "crickets", "insects", "water_drops",
    "frog", "crow", "crackling_fire", "footsteps", "thunderstorm", "engine",
}


class AudioPreprocessor:
    def __init__(self, config: Dict, processed_dir: Path = None, manifest_name: str = "master_manifest.csv",
                 keep_ids: Optional[set] = None):
        self.config = config
        # processed_dir / manifest_name let the filtered A/B run write to separate paths.
        # keep_ids: if given, only segments with these sample_ids are written (reproduces a frozen split).
        self.processed_dir = Path(processed_dir) if processed_dir else PROCESSED_DIR
        self.manifest_name = manifest_name
        self.keep_ids = keep_ids
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.target_sr = config['target_sample_rate']
        self.target_channels = config['target_channels']
        self.window_duration = config['window_duration']
        self.hop_duration = config['hop_duration']

        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        INTERIM_DIR.mkdir(parents=True, exist_ok=True)
        MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        self.manifest_data = []
        self.skipped_files = []

    # ---------- generic audio helpers ----------

    def calculate_file_hash(self, filepath: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def load_audio(self, filepath: Path) -> Tuple[Optional[np.ndarray], Optional[int]]:
        try:
            audio, sr = sf.read(filepath, dtype='float32')
            return audio, sr
        except Exception as e:
            self.skipped_files.append((str(filepath), str(e)))
            return None, None

    def resample_audio(self, audio: np.ndarray, original_sr: int) -> np.ndarray:
        if original_sr == self.target_sr:
            return audio
        return librosa.resample(
            audio.astype(np.float32), orig_sr=original_sr, target_sr=self.target_sr,
            res_type=self.config['resample_quality']
        )

    def convert_to_mono(self, audio: np.ndarray) -> np.ndarray:
        if audio.ndim == 1:
            return audio
        elif audio.ndim == 2:
            return np.mean(audio, axis=1)
        raise ValueError(f"Unexpected audio shape: {audio.shape}")

    def normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        if not self.config['normalize_audio']:
            return audio
        method = self.config['normalization_method']
        if method == "peak":
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                target = 10 ** (self.config['target_dB'] / 20)
                audio = audio * (target / max_val)
        elif method == "rms":
            rms = np.sqrt(np.mean(audio ** 2))
            if rms > 0:
                target = 10 ** (self.config['target_dB'] / 20)
                audio = audio * (target / rms)
        return audio

    def filter_audio(self, audio: np.ndarray) -> np.ndarray:
        """Causal high-pass on the continuous stream (config: filter.*). No-op when disabled."""
        return apply_filter(audio, self.target_sr, self.config.get('filter'))

    def segment_audio(self, audio: np.ndarray, sr: int) -> List[np.ndarray]:
        window_samples = int(self.window_duration * sr)
        hop_samples = int(self.hop_duration * sr)
        segments = []

        if len(audio) < window_samples:
            padding_strategy = self.config['padding_strategy']
            if len(audio) == 0:
                return segments
            if padding_strategy == "repeat":
                repeats = int(np.ceil(window_samples / len(audio)))
                segments.append(np.tile(audio, repeats)[:window_samples])
            elif padding_strategy == "zero_pad":
                segments.append(np.pad(audio, (0, window_samples - len(audio)), mode='constant'))
            else:
                segments.append(np.pad(audio, (0, max(0, window_samples - len(audio))), mode='constant')[:window_samples])
        else:
            for start in range(0, len(audio) - window_samples + 1, hop_samples):
                segments.append(audio[start:start + window_samples])
            if segments:
                last_covered = (len(segments) - 1) * hop_samples + window_samples
                if len(audio) - last_covered > window_samples // 2:
                    start = len(audio) - window_samples
                    segments.append(audio[start:start + window_samples])
        return segments

    def quality_check(self, audio: np.ndarray) -> Tuple[bool, str]:
        if len(audio) == 0:
            return False, "empty"
        if self.config['check_clipping']:
            max_val = np.max(np.abs(audio))
            if max_val > self.config['clipping_threshold']:
                return False, f"Clipping detected: {max_val:.3f}"
        if self.config['check_silence']:
            silence_ratio = np.sum(np.abs(audio) < self.config['silence_threshold']) / len(audio)
            if silence_ratio > self.config['silence_ratio_threshold']:
                return False, f"Too much silence: {silence_ratio:.2%}"
        return True, "OK"

    def _write_segments(self, audio: np.ndarray, sr: int, base_id: str, dataset_name: str,
                         class_label: str, original_recording_id: str, extra_meta: Dict) -> int:
        """Segment, quality-check, save wavs, append manifest rows. Returns num segments kept."""
        segments = self.segment_audio(audio, sr)
        kept = 0
        for i, segment in enumerate(segments):
            sample_id = f"{base_id}_{i:04d}"
            if self.keep_ids is not None:
                if sample_id not in self.keep_ids:
                    continue
                ok, msg = True, "OK(frozen-id)"
            else:
                ok, msg = self.quality_check(segment)
                if not ok:
                    continue
            out_path = self.processed_dir / f"{sample_id}.wav"
            sf.write(out_path, segment, sr, subtype='PCM_16')
            row = {
                'sample_id': sample_id,
                'dataset_id': dataset_name,
                'original_recording_id': original_recording_id,
                'class': class_label,
                'segment_index': i,
                'duration': len(segment) / sr,
                'sample_rate': sr,
                'channels': self.target_channels,
                'processed_path': str(out_path.relative_to(ML_ROOT)),
                'quality_status': msg,
            }
            row.update(extra_meta)
            self.manifest_data.append(row)
            kept += 1
        return kept

    def _load_resample_mono_norm(self, filepath: Path) -> Optional[np.ndarray]:
        audio, sr = self.load_audio(filepath)
        if audio is None:
            return None
        audio = self.convert_to_mono(audio)
        audio = self.resample_audio(audio, sr)
        audio = self.filter_audio(audio)
        audio = self.normalize_audio(audio)
        return audio

    # ---------- per-dataset processors ----------

    def process_c3gd(self):
        print("\nProcessing c3gd (subset selection for diversity)...")
        meta_path = RAW_DIR / "c3gd" / "C3GD" / "metadata.csv"
        data_dir = RAW_DIR / "c3gd" / "C3GD" / "data"
        df = pd.read_csv(meta_path)

        subset_size = self.config['datasets']['c3gd'].get('subset_size', 130)
        # Diversity-maximizing stratified sample: group by (event_id, platform_id, cartridge_id, mic_id)
        # combo, then round-robin sample across combos, respecting event grouping.
        rng = np.random.RandomState(self.config['split_seed'])
        df['combo'] = (df['event_id'].astype(str) + "|" + df['platform_id'].astype(str) + "|" +
                        df['cartridge_id'].astype(str) + "|" + df['mic_id'].astype(str))
        combos = df['combo'].unique().tolist()
        rng.shuffle(combos)
        selected_rows = []
        combo_groups = {c: g for c, g in df.groupby('combo')}
        i = 0
        while len(selected_rows) < subset_size and any(len(combo_groups[c]) > 0 for c in combos):
            c = combos[i % len(combos)]
            g = combo_groups[c]
            if len(g) > 0:
                pick = g.sample(1, random_state=rng.randint(0, 1_000_000))
                selected_rows.append(pick)
                combo_groups[c] = g.drop(pick.index)
            i += 1
            if i > subset_size * 50:
                break
        subset = pd.concat(selected_rows) if selected_rows else df.head(0)
        print(f"Selected {len(subset)} c3gd recordings across {subset['event_id'].nunique()} events, "
              f"{subset['platform_id'].nunique()} platforms, {subset['cartridge_id'].nunique()} cartridges, "
              f"{subset['mic_id'].nunique()} mics")

        for _, row in tqdm(subset.iterrows(), total=len(subset)):
            filepath = data_dir / row['filename']
            if not filepath.exists():
                self.skipped_files.append((str(filepath), "not found"))
                continue
            audio = self._load_resample_mono_norm(filepath)
            if audio is None:
                continue
            base_id = f"c3gd_{filepath.stem}"
            self._write_segments(
                audio, self.target_sr, base_id, "c3gd", "gunshot",
                original_recording_id=f"c3gd_{row['event_id']}_{filepath.stem}",
                extra_meta={
                    'event_id': row['event_id'], 'platform_id': row['platform_id'],
                    'cartridge_id': row['cartridge_id'], 'mic_id': row['mic_id'],
                }
            )

    def process_fsc22(self):
        print("\nProcessing fsc22...")
        meta_path = RAW_DIR / "fsc22" / "fsc22_metadata.csv"
        audio_dir = RAW_DIR / "fsc22" / "FSC22_repo" / "Audios"
        df = pd.read_csv(meta_path)
        n_discarded = 0
        for _, row in tqdm(df.iterrows(), total=len(df)):
            cname = str(row['Class Name']).strip()
            label = FSC22_LABEL_MAP.get(cname, "discard")
            if label == "discard":
                n_discarded += 1
                continue
            fname = row['Dataset File Name']
            filepath = audio_dir / fname
            if not filepath.exists():
                self.skipped_files.append((str(filepath), "not found"))
                continue
            audio = self._load_resample_mono_norm(filepath)
            if audio is None:
                continue
            base_id = f"fsc22_{filepath.stem}"
            self._write_segments(
                audio, self.target_sr, base_id, "fsc22", label,
                original_recording_id=f"fsc22_{filepath.stem}",
                extra_meta={'fsc22_class_name': cname}
            )
        print(f"fsc22: discarded {n_discarded} files not in gunshot/chainsaw/background mapping")

    def process_rodopi(self):
        print("\nProcessing rodopi (TextGrid saw-interval extraction)...")
        rodopi_dir = RAW_DIR / "rodopi"
        tg_files = sorted(rodopi_dir.glob("*.TextGrid"))
        for tg_path in tqdm(tg_files):
            wav_path = tg_path.with_suffix(".wav")
            if not wav_path.exists():
                self.skipped_files.append((str(wav_path), "no matching wav"))
                continue
            intervals = parse_textgrid(tg_path)
            chainsaw_ivs = get_chainsaw_intervals(intervals)
            bg_ivs = get_background_intervals(intervals)
            recording_id = f"rodopi_{wav_path.stem}"

            try:
                info = sf.info(wav_path)
            except Exception as e:
                self.skipped_files.append((str(wav_path), str(e)))
                continue
            native_sr = info.samplerate

            def extract_interval(xmin, xmax):
                start_frame = int(xmin * native_sr)
                n_frames = int((xmax - xmin) * native_sr)
                if n_frames <= 0:
                    return None
                audio, sr = sf.read(wav_path, start=start_frame, frames=n_frames, dtype='float32')
                audio = self.convert_to_mono(audio) if audio.ndim > 1 else audio
                audio = self.resample_audio(audio, sr)
                audio = self.filter_audio(audio)
                audio = self.normalize_audio(audio)
                return audio

            for idx, iv in enumerate(chainsaw_ivs):
                audio = extract_interval(iv.xmin, iv.xmax)
                if audio is None:
                    continue
                base_id = f"rodopi_{wav_path.stem}_saw{idx:03d}"
                self._write_segments(
                    audio, self.target_sr, base_id, "rodopi", "chainsaw",
                    original_recording_id=recording_id,
                    extra_meta={'event_interval_id': f"{recording_id}_saw{idx:03d}",
                                'interval_start': iv.xmin, 'interval_end': iv.xmax}
                )

            # Sample a bounded number of background intervals to avoid huge imbalance
            for idx, iv in enumerate(bg_ivs[:30]):
                if iv.xmax - iv.xmin < 0.5:
                    continue
                audio = extract_interval(iv.xmin, iv.xmax)
                if audio is None:
                    continue
                base_id = f"rodopi_{wav_path.stem}_bg{idx:03d}"
                self._write_segments(
                    audio, self.target_sr, base_id, "rodopi", "background",
                    original_recording_id=recording_id,
                    extra_meta={'event_interval_id': f"{recording_id}_bg{idx:03d}",
                                'interval_start': iv.xmin, 'interval_end': iv.xmax}
                )

    def process_esc50_hf(self):
        print("\nProcessing esc50_hf...")
        meta_path = RAW_DIR / "esc50_hf" / "ESC-50-master" / "meta" / "esc50.csv"
        audio_dir = RAW_DIR / "esc50_hf" / "ESC-50-master" / "audio"
        df = pd.read_csv(meta_path)
        for _, row in tqdm(df.iterrows(), total=len(df)):
            category = str(row['category'])
            if category in ESC50_CHAINSAW:
                label = "chainsaw"
            elif category in ESC50_BACKGROUND:
                label = "background"
            else:
                continue
            filepath = audio_dir / row['filename']
            if not filepath.exists():
                # fall back to per-category subfolder layout already present on disk
                filepath = (RAW_DIR / "esc50_hf" / "ESC-50-master" / category /
                            "ESC-50-master" / "audio" / row['filename'])
            if not filepath.exists():
                self.skipped_files.append((str(filepath), "not found"))
                continue
            audio = self._load_resample_mono_norm(filepath)
            if audio is None:
                continue
            base_id = f"esc50hf_{filepath.stem}"
            self._write_segments(
                audio, self.target_sr, base_id, "esc50_hf", label,
                original_recording_id=f"esc50hf_{filepath.stem}",
                extra_meta={'esc50_category': category}
            )

    def process_rfcx_frugalai(self):
        print("\nProcessing rfcx_frugalai...")
        base_dir = RAW_DIR / "rfcx_frugalai" / "audio"
        for sub, label in [("chainsaw", "chainsaw"), ("environment", "background")]:
            folder = base_dir / sub
            if not folder.exists():
                continue
            files = list(folder.glob("*.wav"))
            for filepath in tqdm(files, desc=sub):
                audio = self._load_resample_mono_norm(filepath)  # resample handles 12k->16k
                if audio is None:
                    continue
                base_id = f"rfcx_{filepath.stem}"
                self._write_segments(
                    audio, self.target_sr, base_id, "rfcx_frugalai", label,
                    original_recording_id=f"rfcx_{filepath.stem}",
                    extra_meta={}
                )

    def process_sensing_forest(self):
        print("\nProcessing sensing_forest (all background)...")
        audio_dir = RAW_DIR / "sensing_forest" / "audio"
        files = list(audio_dir.glob("*.wav"))
        for filepath in tqdm(files):
            audio = self._load_resample_mono_norm(filepath)
            if audio is None:
                continue
            base_id = f"sensingforest_{filepath.stem}"
            self._write_segments(
                audio, self.target_sr, base_id, "sensing_forest", "background",
                original_recording_id=f"sensingforest_{filepath.stem}",
                extra_meta={}
            )

    # ---------- orchestration ----------

    def save_manifest(self) -> pd.DataFrame:
        manifest_df = pd.DataFrame(self.manifest_data)
        manifest_path = MANIFESTS_DIR / self.manifest_name
        manifest_df.to_csv(manifest_path, index=False)
        print(f"\nSaved manifest to {manifest_path}")
        print(f"Total segments: {len(manifest_df)}")
        print(manifest_df['class'].value_counts())
        print(f"\nSkipped files: {len(self.skipped_files)}")
        if self.skipped_files:
            with open(MANIFESTS_DIR / "skipped_files.json", "w") as f:
                json.dump(self.skipped_files, f, indent=2)
        return manifest_df

    def run(self, datasets_to_process=None) -> pd.DataFrame:
        print("=" * 70)
        print("AUDIO PREPROCESSING PIPELINE")
        print("=" * 70)

        all_processors = {
            'c3gd': self.process_c3gd,
            'fsc22': self.process_fsc22,
            'rodopi': self.process_rodopi,
            'esc50_hf': self.process_esc50_hf,
            'rfcx_frugalai': self.process_rfcx_frugalai,
            'sensing_forest': self.process_sensing_forest,
        }
        datasets_to_process = datasets_to_process or list(all_processors.keys())
        for name in datasets_to_process:
            all_processors[name]()

        manifest_df = self.save_manifest()
        print("\n" + "=" * 70)
        print("PREPROCESSING COMPLETED")
        print("=" * 70)
        return manifest_df


def main():
    preprocessor = AudioPreprocessor(CONFIG)
    preprocessor.run()


if __name__ == "__main__":
    main()
