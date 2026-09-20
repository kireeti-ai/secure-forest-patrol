#!/bin/bash
# Compiles the firmware's TFLite Micro library + our custom kernel for the HOST and compares its INT8
# outputs with Python TFLite on real ml/ test-set windows. Needs: `pio pkg install -e esp32-s3-acoustic`,
# python3 with tensorflow/librosa, and the local ml/ dataset.   Usage: tools/tflm_host_parity/run.sh [N per class]
set -euo pipefail
FW="$(cd "$(dirname "$0")/../.." && pwd)"; ROOT="$(cd "$FW/.." && pwd)"
LIB="$FW/.pio/libdeps/esp32-s3-acoustic/TensorFlowLite_ESP32/src"; K="$FW/lib/Acoustic/src"
OUT="${TMPDIR:-/tmp}/tflm_host_parity"; mkdir -p "$OUT/obj"
INC="-I$LIB -I$LIB/third_party -I$LIB/third_party/gemmlowp -I$LIB/third_party/flatbuffers/include -I$LIB/third_party/ruy -I$K"
cd "$LIB"
for f in $(find tensorflow -name "*.cpp" | grep -viE "test|arduino|/esp|ethos|cmsis|xtensa|hexagon|riscv|ceva|debug_log|system_setup|signal|flexbuffers|microfrontend|all_ops_resolver|mock_|fake_|recording_|kernel_runner"); do
  o="$OUT/obj/$(echo "$f" | tr '/' '_').o"; [ -f "$o" ] || g++ -std=gnu++17 -O1 -w -DTF_LITE_STATIC_MEMORY $INC -c "$f" -o "$o"
done
g++ -std=gnu++17 -O1 -w -DTF_LITE_STATIC_MEMORY $INC "$FW/tools/tflm_host_parity/harness.cpp" "$K/AcousticKernels.cpp" "$OUT"/obj/*.o -o "$OUT/harness"
cd "$ROOT" && python3 "$FW/tools/tflm_host_parity/compare.py" "$OUT/harness" "${1:-150}"
