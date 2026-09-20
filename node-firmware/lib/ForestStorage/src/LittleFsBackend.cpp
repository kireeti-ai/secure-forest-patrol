#include "LittleFsBackend.h"

#ifdef ARDUINO
#include <Arduino.h>
#include <LittleFS.h>

namespace forest::storage {

bool LittleFsBackend::begin() { return LittleFS.begin(true); }   // format on the very first mount only

int64_t LittleFsBackend::size(const char* name) {
    File f = LittleFS.open(name, "r");
    if (!f) return -1;
    const int64_t s = static_cast<int64_t>(f.size());
    f.close();
    return s;
}

bool LittleFsBackend::read(const char* name, size_t offset, uint8_t* buf, size_t n) {
    File f = LittleFS.open(name, "r");
    if (!f) return false;
    const bool ok = f.seek(offset) && f.read(buf, n) == n;
    f.close();
    return ok;
}

bool LittleFsBackend::write(const char* name, size_t offset, const uint8_t* buf, size_t n) {
    File f = LittleFS.open(name, LittleFS.exists(name) ? "r+" : "w");
    if (!f) return false;
    const bool ok = f.seek(offset) && f.write(buf, n) == n;
    f.close();   // LittleFS commits atomically on close
    return ok;
}

bool LittleFsBackend::truncate(const char* name, size_t newSize) {
    // The Arduino File API has no truncate: copy the kept prefix to a temp file and rename it over the original
    // (lfs_rename replaces the target atomically).
    File src = LittleFS.open(name, "r");
    if (!src) return newSize == 0;
    if (src.size() == newSize) { src.close(); return true; }
    File dst = LittleFS.open("/trunc.tmp", "w");
    if (!dst) { src.close(); return false; }
    uint8_t chunk[64];
    size_t left = newSize;
    bool ok = true;
    while (left > 0 && ok) {
        const size_t n = left < sizeof(chunk) ? left : sizeof(chunk);
        ok = src.read(chunk, n) == n && dst.write(chunk, n) == n;
        left -= n;
    }
    src.close();
    dst.close();
    return ok && LittleFS.rename("/trunc.tmp", name);
}

bool LittleFsBackend::remove(const char* name) { return !LittleFS.exists(name) || LittleFS.remove(name); }

}  // namespace forest::storage
#endif
