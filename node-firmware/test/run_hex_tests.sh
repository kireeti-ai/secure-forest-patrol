#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
g++ -std=gnu++17 -O1 -Wall -Ilib/Utils/src -o /tmp/hex_test test/hex_test.cpp lib/Utils/src/Hex.cpp
/tmp/hex_test
