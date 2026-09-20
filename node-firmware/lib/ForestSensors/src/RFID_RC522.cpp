#include "RFID_RC522.h"

#include <Arduino.h>

#include "SensorMath.h"

namespace ForestSensors {
namespace {
// MFRC522 register map (datasheet rev. 3.9, table 20)
constexpr uint8_t CommandReg = 0x01, ComIrqReg = 0x04, ErrorReg = 0x06, FIFODataReg = 0x09, FIFOLevelReg = 0x0A,
                  ControlReg = 0x0C, BitFramingReg = 0x0D, CollReg = 0x0E, ModeReg = 0x11, TxControlReg = 0x14,
                  TxASKReg = 0x15, RFCfgReg = 0x26, TModeReg = 0x2A, TPrescalerReg = 0x2B, TReloadRegH = 0x2C,
                  TReloadRegL = 0x2D, VersionReg = 0x37;
// Commands
constexpr uint8_t CmdIdle = 0x00, CmdTransceive = 0x0C, CmdSoftReset = 0x0F;
// ISO 14443-3 frames
constexpr uint8_t PICC_REQA = 0x26, PICC_SEL_CL1 = 0x93, PICC_SEL_CL2 = 0x95, PICC_HLTA = 0x50, CASCADE_TAG = 0x88;
const SPISettings kSpi(4000000, MSBFIRST, SPI_MODE0);
}  // namespace

// SPI framing: first byte = (address << 1) with bit7 = 1 for read, 0 for write; MSB first, mode 0.
uint8_t RFID_RC522::readReg(uint8_t reg) {
    uint8_t v = 0;
    readRegs(reg, 1, &v);
    return v;
}

void RFID_RC522::readRegs(uint8_t reg, uint8_t count, uint8_t* out) {
    spi_->beginTransaction(kSpi);
    digitalWrite(cs_, LOW);
    // Multi-byte read: the address byte is repeated before every data byte and the last transfer sends
    // 0x00 (datasheet 8.1.2.1). The first transfer only returns a dummy byte.
    const uint8_t addr = static_cast<uint8_t>(0x80 | ((reg << 1) & 0x7E));
    spi_->transfer(addr);
    for (uint8_t i = 0; i < count; ++i) out[i] = spi_->transfer(i + 1 < count ? addr : 0x00);
    digitalWrite(cs_, HIGH);
    spi_->endTransaction();
}

void RFID_RC522::writeReg(uint8_t reg, uint8_t value) { writeRegs(reg, 1, &value); }

void RFID_RC522::writeRegs(uint8_t reg, uint8_t count, const uint8_t* data) {
    spi_->beginTransaction(kSpi);
    digitalWrite(cs_, LOW);
    spi_->transfer(static_cast<uint8_t>((reg << 1) & 0x7E));
    for (uint8_t i = 0; i < count; ++i) spi_->transfer(data[i]);
    digitalWrite(cs_, HIGH);
    spi_->endTransaction();
}

void RFID_RC522::softReset() {
    writeReg(CommandReg, CmdSoftReset);
    for (int i = 0; i < 50; ++i) {   // PowerDown bit (0x10) clears when the oscillator is running again
        delay(5);
        if ((readReg(CommandReg) & 0x10) == 0) break;
    }
}

void RFID_RC522::antennaOn() {
    if ((readReg(TxControlReg) & 0x03) != 0x03) setBits(TxControlReg, 0x03);
}

bool RFID_RC522::begin(SPIClass& spi) {
    spi_ = &spi;
    pinMode(cs_, OUTPUT);
    digitalWrite(cs_, HIGH);
    if (rst_ >= 0) {                       // hardware reset pulse, then wait for the oscillator
        pinMode(rst_, OUTPUT);
        digitalWrite(rst_, LOW);
        delayMicroseconds(5);
        digitalWrite(rst_, HIGH);
        delay(50);
    }
    softReset();
    writeReg(TModeReg, 0x80);              // timer starts automatically at the end of transmission
    writeReg(TPrescalerReg, 0xA9);         // f_timer = 6.78 MHz / (2*169+1) = 40 kHz
    writeReg(TReloadRegH, 0x03);           // reload 1000 ticks -> 25 ms timeout
    writeReg(TReloadRegL, 0xE8);
    writeReg(TxASKReg, 0x40);              // force 100 % ASK modulation
    writeReg(ModeReg, 0x3D);               // CRC preset 0x6363 (ISO 14443-3 CRC_A)
    antennaOn();
    const uint8_t v = version();
    return v != 0x00 && v != 0xFF;
}

uint8_t RFID_RC522::version() { return readReg(VersionReg); }

void RFID_RC522::setAntennaGainMax() { writeReg(RFCfgReg, static_cast<uint8_t>(0x07 << 4)); }

bool RFID_RC522::transceive(const uint8_t* send, uint8_t sendLen, uint8_t* recv, uint8_t* recvLen, uint8_t* validBits) {
    const uint8_t txLastBits = validBits ? *validBits : 0;
    writeReg(CommandReg, CmdIdle);
    writeReg(ComIrqReg, 0x7F);             // clear all interrupt request flags
    writeReg(FIFOLevelReg, 0x80);          // flush FIFO
    writeRegs(FIFODataReg, sendLen, send);
    writeReg(BitFramingReg, txLastBits);
    writeReg(CommandReg, CmdTransceive);
    setBits(BitFramingReg, 0x80);          // StartSend

    bool done = false;
    for (uint32_t i = 0; i < 2000; ++i) {  // ~ up to 36 ms
        const uint8_t irq = readReg(ComIrqReg);
        if (irq & 0x30) { done = true; break; }   // RxIRq | IdleIRq
        if (irq & 0x01) return false;             // TimerIRq: no answer
    }
    if (!done) return false;
    const uint8_t err = readReg(ErrorReg);
    if (err & 0x13) return false;                 // BufferOvfl | ParityErr | ProtocolErr
    const uint8_t n = readReg(FIFOLevelReg);
    if (recv != nullptr && recvLen != nullptr) {
        if (n > *recvLen) return false;
        *recvLen = n;
        readRegs(FIFODataReg, n, recv);
        if (validBits) *validBits = readReg(ControlReg) & 0x07;
    }
    if (err & 0x08) return false;                 // CollErr
    return true;
}

bool RFID_RC522::isCardPresent() {
    clearBits(CollReg, 0x80);                     // all received bits are valid after a collision
    uint8_t atqa[2];
    uint8_t len = sizeof(atqa);
    uint8_t bits = 7;                             // REQA is a 7-bit short frame
    const uint8_t cmd = PICC_REQA;
    if (!transceive(&cmd, 1, atqa, &len, &bits)) return false;
    return len == 2 && bits == 0;
}

bool RFID_RC522::selectLevel(uint8_t sel, const uint8_t uid4[4], uint8_t* sak) {
    uint8_t frame[9] = {sel, 0x70, uid4[0], uid4[1], uid4[2], uid4[3], 0, 0, 0};
    frame[6] = uid4[0] ^ uid4[1] ^ uid4[2] ^ uid4[3];          // BCC
    const uint16_t crc = crcA(frame, 7);
    frame[7] = static_cast<uint8_t>(crc & 0xFF);
    frame[8] = static_cast<uint8_t>(crc >> 8);
    uint8_t resp[3];
    uint8_t len = sizeof(resp);
    if (!transceive(frame, 9, resp, &len) || len != 3) return false;
    const uint16_t rcrc = crcA(resp, 1);
    if (resp[1] != (rcrc & 0xFF) || resp[2] != (rcrc >> 8)) return false;
    *sak = resp[0];
    return true;
}

bool RFID_RC522::readUid(RfidUid& uid) {
    uid = RfidUid{};
    clearBits(CollReg, 0x80);
    uint8_t sel = PICC_SEL_CL1;
    for (int level = 0; level < 2; ++level, sel = PICC_SEL_CL2) {
        // Anti-collision: SEL + NVB(0x20 = no UID bits known yet) -> 4 UID bytes + BCC
        const uint8_t req[2] = {sel, 0x20};
        uint8_t resp[5];
        uint8_t len = sizeof(resp);
        if (!transceive(req, 2, resp, &len) || len != 5) return false;
        if ((resp[0] ^ resp[1] ^ resp[2] ^ resp[3]) != resp[4]) return false;   // BCC check
        uint8_t sak = 0;
        if (!selectLevel(sel, resp, &sak)) return false;
        if (resp[0] == CASCADE_TAG && (sak & 0x04)) {   // 7/10-byte UID continues at the next level
            for (int i = 1; i < 4; ++i) uid.bytes[uid.size++] = resp[i];
            continue;
        }
        for (int i = 0; i < 4; ++i) uid.bytes[uid.size++] = resp[i];
        uid.sak = sak;
        return true;
    }
    return false;   // 10-byte UIDs (three levels) are not needed by this project
}

void RFID_RC522::halt() {
    uint8_t frame[4] = {PICC_HLTA, 0x00, 0, 0};
    const uint16_t crc = crcA(frame, 2);
    frame[2] = static_cast<uint8_t>(crc & 0xFF);
    frame[3] = static_cast<uint8_t>(crc >> 8);
    // A successful HLTA is "no answer": the card stays silent, so the expected outcome is a timeout.
    transceive(frame, 4, nullptr, nullptr);
    clearBits(0x08, 0x08);   // Status2Reg.MFCrypto1On off (nothing was authenticated, kept for parity with the old flow)
}

}  // namespace ForestSensors
