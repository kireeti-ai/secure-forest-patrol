#include "Sx1278LoRaDriver.h"
#include "BuildConfig.h"

#include <Arduino.h>
#include <LoRa.h>
#include <SPI.h>

namespace forest::lora {

namespace {

constexpr int loraSck = 12;
constexpr int loraMiso = 13;
constexpr int loraMosi = 11;
constexpr int loraCs = 10;
constexpr int loraReset = 9;
constexpr int loraDio0 = 14;

std::uint8_t readRegisterDiagnostic(std::uint8_t address) {
    SPI.beginTransaction(SPISettings(200000U, MSBFIRST, SPI_MODE0));
    digitalWrite(loraCs, LOW);
    SPI.transfer(address & 0x7FU);
    const std::uint8_t value = SPI.transfer(0x00U);
    digitalWrite(loraCs, HIGH);
    SPI.endTransaction();
    return value;
}

void printInitializationDiagnostics() {
    Serial.println("[GATEWAY DIAG] LoRa.begin() failure diagnostics");
    Serial.printf("[GATEWAY DIAG] Pins: SCK=%d MISO=%d MOSI=%d CS=%d RST=%d DIO0=%d\n",
                  loraSck, loraMiso, loraMosi, loraCs, loraReset, loraDio0);
    Serial.printf("[GATEWAY DIAG] Pin levels: CS=%d RST=%d DIO0=%d\n",
                  digitalRead(loraCs), digitalRead(loraReset), digitalRead(loraDio0));
    Serial.printf("[GATEWAY DIAG] SX127x REG_VERSION(0x42)=0x%02X (expected 0x12)\n",
                  static_cast<unsigned>(readRegisterDiagnostic(0x42U)));
    Serial.printf("[GATEWAY DIAG] SX127x REG_OP_MODE(0x01)=0x%02X\n",
                  static_cast<unsigned>(readRegisterDiagnostic(0x01U)));
    Serial.printf("[GATEWAY DIAG] SX127x REG_SYNC_WORD(0x39)=0x%02X\n",
                  static_cast<unsigned>(readRegisterDiagnostic(0x39U)));
}

SPIClass loraSpi(FSPI);

std::uint8_t readLoraRegister(std::uint8_t address) {
    loraSpi.beginTransaction(SPISettings(200000U, MSBFIRST, SPI_MODE0));
    digitalWrite(loraCs, LOW);
    loraSpi.transfer(address & 0x7FU);
    const std::uint8_t value = loraSpi.transfer(0x00U);
    digitalWrite(loraCs, HIGH);
    loraSpi.endTransaction();
    return value;
}

}  // namespace

bool Sx1278LoRaDriver::begin() {
    Serial.println("[LoRa] Configuring SX1278");
    Serial.printf("[LoRa] Pins SCK=%d MISO=%d MOSI=%d CS=%d RST=%d DIO0=%d\n",
                  loraSck, loraMiso, loraMosi, loraCs, loraReset, loraDio0);
    Serial.println("[LoRa] Frequency=433000000 SF=7 BW=125000 CR=4/5 Sync=0x12 CRC=ON");
    pinMode(loraCs, OUTPUT);
    digitalWrite(loraCs, HIGH);

    pinMode(loraReset, OUTPUT);
    digitalWrite(loraReset, HIGH);

    loraSpi.begin(loraSck, loraMiso, loraMosi, loraCs);
    LoRa.setSPI(loraSpi);
    LoRa.setPins(loraCs, loraReset, loraDio0);

    if (!configureRadio_()) {
        Serial.println("[GATEWAY ERROR] LoRa.begin() FAILED");
        printInitializationDiagnostics();
        Serial.flush();
        return false;
    }
    lastActivityMs_ = millis();
    Serial.println("[LoRa] RX listening");
    return true;
}

bool Sx1278LoRaDriver::configureRadio_() {
    if (!LoRa.begin(frequencyHz)) return false;
    LoRa.setSpreadingFactor(spreadingFactor);
    LoRa.setSignalBandwidth(signalBandwidthHz);
    LoRa.setCodingRate4(codingRateDenominator);
    LoRa.setSyncWord(syncWord);
    LoRa.enableCrc();
    // Polling mode: no onReceive callback, no SPI-in-ISR hazard.
    // parsePacket() is called every tick from the main loop.
    LoRa.receive();
    return true;
}

void Sx1278LoRaDriver::watchdog_() {
    const std::uint32_t now = millis();
    if (now - lastWatchdogMs_ < 1000U) return;
    lastWatchdogMs_ = now;

    // RegOpMode (0x01): bit7 = LoRa mode, bits 2..0 = mode; 0x85 = LoRa + RX continuous.
    const std::uint8_t opMode = readLoraRegister(0x01U);

    if ((opMode & 0x87U) != 0x85U) {
        ++watchdogRearms_;
        Serial.printf("[LoRa WATCHDOG] receiver not in RX mode (RegOpMode=0x%02X): re-arming (#%lu)\n",
                      static_cast<unsigned>(opMode), static_cast<unsigned long>(watchdogRearms_));
        LoRa.receive();
        return;
    }
    if (now - lastActivityMs_ >= reinitAfterSilenceMs) {
        // A long silence is normal at night, so this only refreshes the radio; it costs a few milliseconds.
        ++watchdogReinits_;
        Serial.printf("[LoRa WATCHDOG] no packets for %lu s: re-initialising the SX1278 (#%lu)\n",
                      static_cast<unsigned long>((now - lastActivityMs_) / 1000U), static_cast<unsigned long>(watchdogReinits_));
        if (!configureRadio_()) Serial.println("[LoRa WATCHDOG] re-initialisation FAILED");
        lastActivityMs_ = now;
    }
}

bool Sx1278LoRaDriver::receive(RawRadioPacket& packet) {
    watchdog_();
    // Stay in true continuous RX. The library's parsePacket() would otherwise flip the chip into
    // single-shot RX on every call (which times out into standby: the receiver is deaf between polls), so
    // it is only called once the chip has flagged a finished reception (RegIrqFlags bit 6, RxDone).
    if ((readLoraRegister(0x12U) & 0x40U) == 0U) {
        return false;
    }
    const int packetSize = LoRa.parsePacket();
    if (packetSize <= 0) {   // RxDone with a payload CRC error: nothing to read, resume listening
        LoRa.receive();
        return false;
    }

    std::size_t bytesRead = 0U;
    while (LoRa.available() && bytesRead < rxBuffer_.size()) {
        const int value = LoRa.read();
        if (value < 0) break;
        rxBuffer_[bytesRead] = static_cast<std::uint8_t>(value);
        ++bytesRead;
    }

    if (bytesRead == 0U) {
        return false;
    }

    packet.bytes = rxBuffer_.data();
    packet.length = bytesRead;
    packet.rssiDbm = LoRa.packetRssi();
    packet.snrDb = LoRa.packetSnr();
    packet.receivedAtMs = millis();

    packetsReceivedCounter_++;
    lastActivityMs_ = millis();
    LoRa.receive();

    return true;
}

bool Sx1278LoRaDriver::send(const std::uint8_t* data, std::size_t length) {
    if (data == nullptr || length == 0) return false;

    LoRa.idle();
    LoRa.beginPacket();
    LoRa.enableCrc();
    const std::size_t written = LoRa.write(data, length);
    if (written != length) {
        LoRa.endPacket();
        LoRa.enableCrc();
        LoRa.receive();
        return false;
    }
    bool res = (LoRa.endPacket() == 1);
    if (res) acksSentCounter_++;

    LoRa.enableCrc();
    LoRa.receive();
    return res;
}

}  // namespace forest::lora
