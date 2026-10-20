#!/usr/bin/env python3
"""Save real captured audio windows from the acoustic node as labeled WAV files.

Build and flash the firmware with -D ACOUSTIC_DUMP_AUDIO=1 first, so each
trigger prints the raw 1 s / 16 kHz / 16-bit window as base64 between
"[AUDIO] BEGIN" / "[AUDIO] END" markers. This script listens on serial, pulls
those windows out, and writes each one to <outdir>/<label>/<label>_NNN.wav.

Usage:
    python3 tools/capture_audio.py /dev/cu.usbmodem5B5E0265961 chainsaw
    python3 tools/capture_audio.py /dev/cu.usbmodem5B5E0265961 background --outdir ../ml/datasets/field_capture

Press Ctrl+C to stop. The label is just a folder name you choose per session
(background / chainsaw / gunshot, or whatever you're recording).
"""
import argparse
import base64
import os
import struct
import sys
import time

import serial

SAMPLE_RATE = 16000
BITS_PER_SAMPLE = 16
CHANNELS = 1


def write_wav(path: str, pcm_bytes: bytes) -> None:
    byte_rate = SAMPLE_RATE * CHANNELS * BITS_PER_SAMPLE // 8
    block_align = CHANNELS * BITS_PER_SAMPLE // 8
    data_size = len(pcm_bytes)
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, CHANNELS, SAMPLE_RATE, byte_rate, block_align, BITS_PER_SAMPLE))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(pcm_bytes)


def next_index(outdir: str, label: str) -> int:
    existing = [fn for fn in os.listdir(outdir) if fn.startswith(label + "_") and fn.endswith(".wav")]
    best = 0
    for fn in existing:
        try:
            best = max(best, int(fn[len(label) + 1 : -4]))
        except ValueError:
            pass
    return best + 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port", help="serial port, e.g. /dev/cu.usbmodem5B5E0265961")
    ap.add_argument("label", help="folder/label name for this session, e.g. background, chainsaw, gunshot")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--outdir", default=os.path.join(os.path.dirname(__file__), "captured_audio"))
    args = ap.parse_args()

    label_dir = os.path.join(args.outdir, args.label)
    os.makedirs(label_dir, exist_ok=True)
    idx = next_index(label_dir, args.label)

    ser = serial.Serial(args.port, args.baud, timeout=1)
    print(f"Listening on {args.port}. Saving to {label_dir}/{args.label}_NNN.wav. Ctrl+C to stop.")

    capturing = False
    b64_lines = []
    saved = 0
    try:
        while True:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode(errors="replace").strip()
            if line == "[AUDIO] BEGIN":
                capturing = True
                b64_lines = []
                continue
            if line == "[AUDIO] END":
                if capturing:
                    try:
                        pcm = base64.b64decode("".join(b64_lines))
                        out_path = os.path.join(label_dir, f"{args.label}_{idx:03d}.wav")
                        write_wav(out_path, pcm)
                        saved += 1
                        idx += 1
                        print(f"[{time.strftime('%H:%M:%S')}] saved {out_path} ({len(pcm)} bytes, "
                              f"{len(pcm) / 2 / SAMPLE_RATE:.2f}s) — total {saved}")
                    except Exception as e:
                        print(f"  (skipped: {e})", file=sys.stderr)
                capturing = False
                continue
            if capturing:
                b64_lines.append(line)
            elif line and not line.startswith(("[LOCAL STORE]", "[RETRY TX]")):
                # pass through other pipeline logs so you can see trigger/class context live
                # (boot replay of the local event store is filtered out - it's just noise here)
                print(line)
    except KeyboardInterrupt:
        print(f"\nStopped. Saved {saved} clip(s) to {label_dir}")
    finally:
        ser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
