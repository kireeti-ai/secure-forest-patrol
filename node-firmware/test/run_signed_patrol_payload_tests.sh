#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
g++ -std=gnu++17 -O1 -Wall -Ilib/ForestCrypto/src -o /tmp/signed_patrol_payload_test \
    test/signed_patrol_payload_test.cpp lib/ForestCrypto/src/SignedPatrolPayload.cpp
/tmp/signed_patrol_payload_test
