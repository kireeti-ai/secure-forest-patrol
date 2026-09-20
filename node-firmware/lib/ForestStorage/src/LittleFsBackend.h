#pragma once
// StorageBackend on the ESP32 internal flash: LittleFS (part of the Arduino-ESP32 framework) on the
// "spiffs" data partition.

#ifdef ARDUINO
#include "StorageBackend.h"

namespace forest::storage {

class LittleFsBackend final : public StorageBackend {
public:
    bool begin() override;
    int64_t size(const char* name) override;
    bool read(const char* name, size_t offset, uint8_t* buf, size_t n) override;
    bool write(const char* name, size_t offset, const uint8_t* buf, size_t n) override;
    bool truncate(const char* name, size_t newSize) override;
    bool remove(const char* name) override;
};

}  // namespace forest::storage
#endif
