// Host test: the canonical patrol signing-bytes builder must be byte-for-byte identical to
// backend/app/services/crypto.py::patrol_signing_bytes for the same logical inputs. The expected
// string below was captured by actually running that Python function (see the comment), not
// hand-derived - this is the real interop contract, not a guess at it.
#include <cstdio>
#include <cstring>

#include "PatrolSigningBytes.h"

using namespace forest::crypto;
static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s (line %d)\n", msg, __LINE__); ++failures; } } while (0)

int main() {
    char iso[32];
    formatIso8601Utc(2026, 1, 15, 10, 30, 0, iso, sizeof iso);
    CHECK(!strcmp(iso, "2026-01-15T10:30:00+00:00"), "ISO 8601 UTC format matches Python's isoformat()");

    char out[256];
    size_t n = buildPatrolSigningBytes("N01", 7, iso, "CP1", "OFF9", "VALID", "MATCH", "", "deadbeef", out, sizeof out);
    // Captured by running: python3 -c "from datetime import datetime, timezone; from app.services.crypto
    // import patrol_signing_bytes; print(patrol_signing_bytes(node_id='N01', sequence=7,
    // event_created_at=datetime(2026,1,15,10,30,0,tzinfo=timezone.utc), checkpoint_id='CP1',
    // officer_id='OFF9', rfid_result='VALID', fingerprint_result='MATCH', previous_hash='',
    // record_hash='deadbeef').decode())"
    const char* expected = "N01|7|2026-01-15T10:30:00+00:00|CP1|OFF9|VALID|MATCH|GENESIS|deadbeef";
    CHECK(n == strlen(expected) && !strcmp(out, expected), "matches real backend crypto.py output exactly");

    // empty optional fields render as "" (Python's `x or ""`), not "null" or garbage
    n = buildPatrolSigningBytes("N02", 1, iso, nullptr, nullptr, nullptr, nullptr, "priorhash", "rechash", out, sizeof out);
    CHECK(!strcmp(out, "N02|1|2026-01-15T10:30:00+00:00|||||priorhash|rechash"), "null optional fields render empty");

    // non-empty previous_hash is passed through verbatim (only empty/null becomes GENESIS)
    n = buildPatrolSigningBytes("N03", 2, iso, "", "", "", "", "abc123", "def456", out, sizeof out);
    CHECK(!!strstr(out, "|abc123|def456"), "non-empty previous_hash is not replaced with GENESIS");

    // acoustic: captured by running backend/app/services/crypto.py::acoustic_signing_bytes directly
    n = buildAcousticSigningBytes("N01", 1, iso, "CP-01", "", "Chainsaw", "0.6509803921568628",
                                  "forest-acoustic-v1", "",
                                  "ff676a1b9c73a4b0ac56b6c5ec659e39792faaf727cb6a4e3b182ebb500474d7", out, sizeof out);
    const char* expectedAcoustic = "N01|1|2026-01-15T10:30:00+00:00|CP-01||Chainsaw|0.6509803921568628|"
                                   "forest-acoustic-v1|GENESIS|ff676a1b9c73a4b0ac56b6c5ec659e39792faaf727cb6a4e3b182ebb500474d7";
    CHECK(n == strlen(expectedAcoustic) && !strcmp(out, expectedAcoustic),
          "acoustic signing bytes match real backend crypto.py output");

    printf(failures ? "\nPATROL SIGNING TESTS FAIL (%d)\n" : "\nPATROL SIGNING TESTS PASS\n", failures);
    return failures ? 1 : 0;
}
