#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
g++ -std=gnu++17 -O1 -Wall -Ilib/ForestCrypto/src -o /tmp/signed_acoustic_payload_test \
    test/signed_acoustic_payload_test.cpp lib/ForestCrypto/src/SignedAcousticPayload.cpp
/tmp/signed_acoustic_payload_test
