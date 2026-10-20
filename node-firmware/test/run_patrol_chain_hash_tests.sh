#!/bin/bash
# Host test for the patrol hash-chain primitives (payload digest, record hash) - pure SHA-256
# string formatting, checked against real backend crypto.py output.
set -euo pipefail
cd "$(dirname "$0")/.."
g++ -std=gnu++17 -O1 -Wall -Ilib/ForestCrypto/src -o /tmp/patrol_chain_hash_test \
    test/patrol_chain_hash_test.cpp lib/ForestCrypto/src/PatrolChainHash.cpp lib/Utils/src/Sha256.cpp -Ilib/Utils/src
/tmp/patrol_chain_hash_test
