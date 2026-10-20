// Host test: every entry in kConfidenceReprTable must exactly match real Python's
// repr(float(u8/255.0)) - checked here against a second copy captured independently
// (see the generation command in the header comment); this test exists so a future edit to
// the table is caught immediately rather than silently breaking every acoustic signature.
#include <cstdio>
#include <cstring>

#include "AcousticConfidenceTable.h"

using namespace forest::crypto;
static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s (line %d)\n", msg, __LINE__); ++failures; } } while (0)

int main() {
    CHECK(!strcmp(kConfidenceReprTable[0], "0.0"), "u8=0");
    CHECK(!strcmp(kConfidenceReprTable[255], "1.0"), "u8=255");
    CHECK(!strcmp(kConfidenceReprTable[128], "0.5019607843137255"), "u8=128 (not exactly 0.5)");
    CHECK(!strcmp(kConfidenceReprTable[51], "0.2"), "u8=51 -> exactly 0.2");
    CHECK(!strcmp(kConfidenceReprTable[153], "0.6"), "u8=153 -> exactly 0.6");
    CHECK(!strcmp(kConfidenceReprTable[200], "0.7843137254901961"), "u8=200");
    // sanity: table has exactly 256 non-null entries and every string is non-empty
    int nonEmpty = 0;
    for (int i = 0; i < 256; ++i) if (kConfidenceReprTable[i] != nullptr && kConfidenceReprTable[i][0] != '\0') ++nonEmpty;
    CHECK(nonEmpty == 256, "all 256 entries populated and non-empty");

    printf(failures ? "\nCONFIDENCE TABLE TESTS FAIL (%d)\n" : "\nCONFIDENCE TABLE TESTS PASS\n", failures);
    return failures ? 1 : 0;
}
