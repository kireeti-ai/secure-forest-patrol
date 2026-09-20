#!/bin/bash
# Host tests for the acoustic library (no hardware needed). The parity test additionally needs
# the local ml/ dataset and python deps (librosa, tensorflow) to generate reference vectors.
set -euo pipefail
cd "$(dirname "$0")/.."
g++ -std=gnu++17 -O1 -Wall -Ilib/Acoustic/src -o /tmp/acoustic_trigger_test \
    test/acoustic_trigger_test.cpp lib/Acoustic/src/AcousticTrigger.cpp lib/Acoustic/src/AudioCapture.cpp
/tmp/acoustic_trigger_test
test/run_acoustic_parity_test.sh
