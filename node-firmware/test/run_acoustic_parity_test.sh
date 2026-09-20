#!/bin/bash
# Builds and runs the host parity test (needs the local ml/ dataset + python deps: librosa, tensorflow).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/gen_acoustic_testvectors.py >/dev/null
g++ -std=gnu++17 -O2 -Wall -Ilib/Acoustic/src -o /tmp/acoustic_parity_test \
    test/acoustic_parity_test.cpp lib/Acoustic/src/AudioPreprocessor.cpp
/tmp/acoustic_parity_test test/data/vectors.bin
