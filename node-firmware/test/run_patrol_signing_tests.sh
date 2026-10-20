#!/bin/bash
# Host test for the canonical patrol-signing-bytes builder (no hardware, no mbedtls needed -
# pure string formatting, checked against the real backend crypto.py output).
set -euo pipefail
cd "$(dirname "$0")/.."
g++ -std=gnu++17 -O1 -Wall -Ilib/ForestCrypto/src -o /tmp/patrol_signing_test \
    test/patrol_signing_test.cpp lib/ForestCrypto/src/PatrolSigningBytes.cpp
/tmp/patrol_signing_test
