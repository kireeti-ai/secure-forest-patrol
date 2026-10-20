#include "PatrolSigningBytes.h"

#include <cstdio>
#include <cstring>

namespace forest::crypto {

void formatIso8601Utc(uint16_t year, uint8_t month, uint8_t day, uint8_t hour, uint8_t minute,
                       uint8_t second, char* out, size_t outLen) {
    std::snprintf(out, outLen, "%04u-%02u-%02uT%02u:%02u:%02u+00:00",
                  static_cast<unsigned>(year), static_cast<unsigned>(month), static_cast<unsigned>(day),
                  static_cast<unsigned>(hour), static_cast<unsigned>(minute), static_cast<unsigned>(second));
}

size_t buildPatrolSigningBytes(const char* nodeId, uint32_t sequence, const char* eventCreatedAtIso,
                               const char* checkpointId, const char* officerId, const char* rfidResult,
                               const char* fingerprintResult, const char* previousHash,
                               const char* recordHash, char* out, size_t outLen) {
    auto orEmpty = [](const char* s) { return s ? s : ""; };
    const char* prevHash = (previousHash && previousHash[0]) ? previousHash : "GENESIS";
    const int n = std::snprintf(out, outLen, "%s|%lu|%s|%s|%s|%s|%s|%s|%s",
                                orEmpty(nodeId), static_cast<unsigned long>(sequence),
                                orEmpty(eventCreatedAtIso), orEmpty(checkpointId), orEmpty(officerId),
                                orEmpty(rfidResult), orEmpty(fingerprintResult), prevHash, orEmpty(recordHash));
    if (n < 0 || static_cast<size_t>(n) >= outLen) return 0;
    return static_cast<size_t>(n);
}

size_t buildAcousticSigningBytes(const char* nodeId, uint32_t sequence, const char* eventCreatedAtIso,
                                 const char* checkpointId, const char* zoneId, const char* classification,
                                 const char* confidenceRepr, const char* modelVersion,
                                 const char* previousHash, const char* recordHash, char* out, size_t outLen) {
    auto orEmpty = [](const char* s) { return s ? s : ""; };
    const char* prevHash = (previousHash && previousHash[0]) ? previousHash : "GENESIS";
    const int n = std::snprintf(out, outLen, "%s|%lu|%s|%s|%s|%s|%s|%s|%s|%s",
                                orEmpty(nodeId), static_cast<unsigned long>(sequence),
                                orEmpty(eventCreatedAtIso), orEmpty(checkpointId), orEmpty(zoneId),
                                orEmpty(classification), orEmpty(confidenceRepr), orEmpty(modelVersion),
                                prevHash, orEmpty(recordHash));
    if (n < 0 || static_cast<size_t>(n) >= outLen) return 0;
    return static_cast<size_t>(n);
}

}  // namespace forest::crypto
