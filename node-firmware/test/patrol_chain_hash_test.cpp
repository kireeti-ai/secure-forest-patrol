// Host test: patrolPayloadDigestHex/computeRecordHashHex checked against real output from
// backend/app/services/crypto.py (captured by actually running it - see comments below).
#include <cstdio>
#include <cstring>

#include "PatrolChainHash.h"

using namespace forest::crypto;
static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s (line %d)\n", msg, __LINE__); ++failures; } } while (0)

int main() {
    char digest[65];
    patrolPayloadDigestHex("CP1", "AABBCC", "VALID", "MATCH", digest);
    // python3 -c "from app.services import crypto; print(crypto.patrol_payload_digest(
    //   checkpoint_id='CP1', officer_id='AABBCC', rfid_result='VALID', fingerprint_result='MATCH'))"
    CHECK(strlen(digest) == 64, "payload digest is 64 hex chars");
    CHECK(!strcmp(digest, "9365be0f7a14d19850ec2692aa203b7a96b244cd59160c119b02daef7f20d8e7"),
          "payload digest matches real backend crypto.py output");

    char recordHashGenesis[65];
    computeRecordHashHex("N01", 1, "2026-01-15T10:30:00+00:00", digest, nullptr, recordHashGenesis);
    CHECK(!strcmp(recordHashGenesis, "960b70f5178b3f08d37dedba72fd5a53952088d94bcb50b5e93e28e3a5b59d20"),
          "genesis record hash matches real backend crypto.py output");

    char recordHash2[65];
    computeRecordHashHex("N01", 2, "2026-01-15T10:31:00+00:00", digest, recordHashGenesis, recordHash2);
    CHECK(!strcmp(recordHash2, "c1d4032e9d7a4afdbdab2adc8adc43ce565c49b5735f69c3867b96f1a2e10df1"),
          "chained (seq 2) record hash matches real backend crypto.py output");

    // empty previous_hash and nullptr previous_hash must behave identically (both -> GENESIS)
    char recordHashEmpty[65];
    computeRecordHashHex("N01", 1, "2026-01-15T10:30:00+00:00", digest, "", recordHashEmpty);
    CHECK(!strcmp(recordHashEmpty, recordHashGenesis), "empty-string previous_hash == nullptr previous_hash");

    printf(failures ? "\nPATROL CHAIN HASH TESTS FAIL (%d)\n" : "\nPATROL CHAIN HASH TESTS PASS\n", failures);
    return failures ? 1 : 0;
}
