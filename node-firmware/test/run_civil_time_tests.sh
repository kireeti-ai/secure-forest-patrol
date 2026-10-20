#!/bin/bash
# Host test for epoch<->civil-UTC conversion (pure math, no hardware).
set -euo pipefail
cd "$(dirname "$0")/.."
g++ -std=gnu++17 -O1 -Wall -Ilib/ForestTime/src -o /tmp/civil_time_test \
    test/civil_time_test.cpp lib/ForestTime/src/CivilTime.cpp
/tmp/civil_time_test
