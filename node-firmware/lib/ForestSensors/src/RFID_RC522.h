#pragma once
// Custom driver for the NXP MFRC522 (RC522) RFID reader over SPI. Written from the MFRC522 datasheet and
// ISO/IEC 14443-3: register access, initialisation, REQA, anti-collision + select (cascade levels 1-2,
// 4/7-byte UIDs) and HLTA. It does NOT use the MFRC522 third-party library; only the Arduino-ESP32 SPI HAL.
//
//   application -> ForestSensors::RFID_RC522 -> SPIClass (ESP32 HAL) -> RC522
//
// The caller owns the SPI pin mapping (this node re-pins the same SPI bus between the RC522 and the SX1278),
// so call SPI.begin(sck, miso, mosi, ss) before using the driver.

#include <SPI.h>

#include <cstdint>

namespace ForestSensors {

struct RfidUid {
    uint8_t size = 0;          // 4, 7 or 10
    uint8_t bytes[10] = {0};
    uint8_t sak = 0;
};

class RFID_RC522 {
public:
    // csPin: chip select (SDA/SS), rstPin: hardware reset (-1 if not wired).
    RFID_RC522(int csPin, int rstPin) : cs_(csPin), rst_(rstPin) {}

    // Reset, configure the timer/modulation and switch the antenna on. Returns false if the chip does not
    // answer (VersionReg reads 0x00 / 0xFF).
    bool begin(SPIClass& spi = SPI);
    uint8_t version();                              // VersionReg: 0x91 = v1.0, 0x92 = v2.0 (clones: 0x82 ...)
    void setAntennaGainMax();

    // True when a card in the field answers REQA (it must be in IDLE state, i.e. not the halted card).
    bool isCardPresent();
    // Anti-collision + select. Fills uid; false on collision / CRC / BCC error.
    bool readUid(RfidUid& uid);
    void halt();                                    // HLTA: the card ignores REQA until it leaves the field

    // Register level access (exposed for the driver demo / diagnostics).
    uint8_t readReg(uint8_t reg);
    void writeReg(uint8_t reg, uint8_t value);

private:
    void readRegs(uint8_t reg, uint8_t count, uint8_t* out);
    void writeRegs(uint8_t reg, uint8_t count, const uint8_t* data);
    void setBits(uint8_t reg, uint8_t mask) { writeReg(reg, readReg(reg) | mask); }
    void clearBits(uint8_t reg, uint8_t mask) { writeReg(reg, readReg(reg) & static_cast<uint8_t>(~mask)); }
    void softReset();
    void antennaOn();
    // Send `sendLen` bytes and wait for the answer. `validBits` in: bits of the last TX byte (0 = all),
    // out: valid bits of the last RX byte. Returns false on timeout / protocol / parity / collision error.
    bool transceive(const uint8_t* send, uint8_t sendLen, uint8_t* recv, uint8_t* recvLen, uint8_t* validBits = nullptr);
    bool selectLevel(uint8_t sel, const uint8_t uid4[4], uint8_t* sak);

    SPIClass* spi_ = &SPI;
    int cs_;
    int rst_;
};

}  // namespace ForestSensors
