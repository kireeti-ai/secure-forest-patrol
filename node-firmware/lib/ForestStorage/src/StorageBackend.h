#pragma once
// Minimal byte-file interface the event store needs. LittleFsBackend (ESP32 internal flash) implements it
// on the device, an in-memory backend implements it in the host tests.

#include <cstddef>
#include <cstdint>

namespace forest::storage {

class StorageBackend {
public:
    virtual ~StorageBackend() = default;
    virtual bool begin() = 0;
    virtual int64_t size(const char* name) = 0;                                    // -1 if the file does not exist
    virtual bool read(const char* name, size_t offset, uint8_t* buf, size_t n) = 0;
    virtual bool write(const char* name, size_t offset, const uint8_t* buf, size_t n) = 0;   // creates / extends
    virtual bool truncate(const char* name, size_t newSize) = 0;
    virtual bool remove(const char* name) = 0;
};

}  // namespace forest::storage
