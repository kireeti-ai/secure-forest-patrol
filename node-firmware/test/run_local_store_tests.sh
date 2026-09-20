#!/bin/bash
# Host tests for the local event store and the portable ForestSensors helpers (no hardware needed).
set -euo pipefail
cd "$(dirname "$0")/.."
g++ -std=gnu++17 -O1 -Wall -Ilib/ForestStorage/src -Ilib/ForestSensors/src -Ilib/Utils/src -o /tmp/local_event_store_test \
    test/local_event_store_test.cpp lib/ForestStorage/src/EventRecord.cpp lib/ForestStorage/src/LocalEventStore.cpp \
    lib/ForestSensors/src/SensorMath.cpp lib/Utils/src/Crc16.cpp
/tmp/local_event_store_test
