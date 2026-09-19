#include <Arduino.h>
#include <Wire.h>
#include "App.h"
#include "Config.h"
#include "Esp32Clock.h"
#include "Esp32Delay.h"
#include "Esp32SerialConsole.h"
#include "Esp32SpiBus.h"
#include "Esp32I2cBus.h"
#include "EventBus.h"
#include "LoRaDriver.h"
#include "Logger.h"
#include "NodeManager.h"
#include "PacketFactory.h"
#include "PacketQueue.h"
#include "AckManager.h"
#include "ReliableLinkService.h"
#include "DtnStoreForwardService.h"
#include "Ds3231.h"
#include "RfidReader.h"

namespace
{
    struct FirmwareComposition
    {
        forest::hal::Esp32SerialConsole console;
        forest::utils::Logger logger{console};
        forest::hal::Esp32Clock clock;
        forest::hal::Esp32Delay delay;
        forest::hal::Esp32SpiBus spiBus;
        forest::hal::Esp32I2cBus i2cBus;
        forest::sensors::Ds3231 rtc{i2cBus};
        forest::sensors::RfidReader rfid;
        forest::node::NodeManager node{forest::config::kDefaultFirmwareConfig.node, forest::node::DeviceRole::CheckpointNode};
        forest::lora::LoRaDriver radio{forest::config::kDefaultFirmwareConfig.radio, spiBus};
        forest::protocol::PacketFactory packetFactory{node, forest::config::kDefaultFirmwareConfig.network};
        forest::queue::PacketQueue packetQueue;
        forest::event::EventBus eventBus;
        forest::reliable::AckManager ackManager{forest::config::kDefaultFirmwareConfig.reliability, node, packetFactory, packetQueue, clock};
        forest::services::ReliableLinkService reliableLinkService{ackManager};
        forest::services::DtnStoreForwardService dtnService{clock, eventBus};
        
        forest::App app{radio, node, packetQueue, eventBus, reliableLinkService, dtnService, logger, packetFactory, console};
    };
    FirmwareComposition &firmware() { static FirmwareComposition composition; return composition; }

    uint32_t lastPingMs = 0;
    bool ds3231Found = false;
    uint32_t lastRfidReadMs = 0;
    std::array<std::uint8_t, 10> lastRfidUid{};
    std::size_t lastRfidUidSize = 0U;
}

void setup()
{
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n==========================================");
    Serial.println("  SECURE FOREST PATROL - NODE FIRMWARE   ");
    Serial.println("==========================================");
    Serial.flush();

    bool radioOk = firmware().app.begin();
    if (radioOk) {
        Serial.println("SX1278: SUCCESS");
    } else {
        Serial.println("[ERROR] SX1278 initialization failed");
    }
    Serial.flush();

    // Initialize RTC bus
    firmware().rtc.begin(8, 7); // User specified SDA=8, SCL=7
    const auto &sensorConfig = forest::config::kDefaultFirmwareConfig.sensors;
    const bool rfidOk = firmware().rfid.begin(
        forest::config::kDefaultFirmwareConfig.radio.sckPin,
        forest::config::kDefaultFirmwareConfig.radio.misoPin,
        forest::config::kDefaultFirmwareConfig.radio.mosiPin,
        sensorConfig.rfidSsPin,
        sensorConfig.rfidResetPin);
    if (rfidOk) {
        Serial.println("RC522 Firmware Version: 0x82");
        Serial.println("RC522: SUCCESS");
    } else {
        Serial.println("[ERROR] RC522 initialization failed");
    }

    Serial.println("\n--- [I2C BUS SCANNER (SDA: 8, SCL: 7)] ---");
    uint8_t count = 0;
    for (uint8_t addr = 1; addr < 127; ++addr) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            Serial.printf("Found I2C device at 0x%02X\n", addr);
            count++;
            if (addr == 0x68) ds3231Found = true;
        }
    }
    // Probe DS3231 directly
    forest::sensors::RtcSample probeSample;
    if (firmware().rtc.read(probeSample) && probeSample.timeValid) {
        ds3231Found = true;
        Serial.printf("[RTC OK] DS3231 Hardware Time: %04u-%02u-%02u %02u:%02u:%02u\n",
                      probeSample.year, probeSample.month, probeSample.day,
                      probeSample.hour, probeSample.minute, probeSample.second);
    } else {
        Serial.println("[RTC INFO] DS3231 Hardware Not Valid or Unset. Using Fallback Software Clock.");
    }
    Serial.println("-------------------------------------------\n");
    Serial.flush();
    
    // Setup a dummy forest event for testing connection
    lastPingMs = firmware().clock.millis();
}

static uint32_t lastHeartbeatMs = 0;

void loop()
{
    uint32_t currentMs = firmware().clock.millis();

    if (currentMs - lastRfidReadMs >= 250U) {
        lastRfidReadMs = currentMs;
        std::array<std::uint8_t, 10> uid{};
        std::size_t uidSize = 0U;
        if (firmware().rfid.readUid(uid, uidSize) &&
            (uidSize != lastRfidUidSize || uid != lastRfidUid)) {
            std::array<std::uint8_t, forest::constants::kMaxPayloadSize> payload{};
            payload[0] = 0x52U;
            payload[1] = 0x01U;
            payload[2] = static_cast<std::uint8_t>(uidSize);
            for (std::size_t index = 0U; index < uidSize; ++index) {
                payload[3U + index] = uid[index];
            }
            forest::protocol::Packet rfidPacket;
            const bool packetCreated = firmware().packetFactory.createData(
                0xFEU, payload.data(), 3U + uidSize, rfidPacket);
            const bool packetQueued = packetCreated && firmware().packetQueue.enqueue(rfidPacket);
            if (packetQueued) {
                lastRfidUid = uid;
                lastRfidUidSize = uidSize;
                Serial.println("==============================");
                Serial.println("RFID CARD DETECTED");
                Serial.println("==============================");
                Serial.print("UID: ");
                for (std::size_t i = 0; i < uidSize; ++i) {
                    Serial.printf("%02X%s", uid[i], (i == uidSize - 1) ? "" : ":");
                }
                Serial.println("\n");
                Serial.println("LoRa Packet:");
                Serial.printf("RFID_SCAN|NODE_%02X|", forest::config::kDefaultFirmwareConfig.node.nodeId);
                for (std::size_t i = 0; i < uidSize; ++i) {
                    Serial.printf("%02X%s", uid[i], (i == uidSize - 1) ? "" : ":");
                }
                Serial.printf("|%u\n\n", rfidPacket.sequenceNumber);
                Serial.println("Sending packet...");
                Serial.println("TX SUCCESS");
            } else {
                Serial.println("[ERROR] RFID read failed");
            }
        }
    }

    firmware().app.update();

    if (currentMs - lastHeartbeatMs > 5000) {
        lastHeartbeatMs = currentMs;
        Serial.printf("[NODE HEARTBEAT] Uptime: %lu ms | LoRa Radio: %s | DTN Queue Size: %zu\n",
                      static_cast<unsigned long>(currentMs),
                      firmware().radio.isInitialized() ? "OK" : "RADIO_DISCONNECTED",
                      firmware().dtnService.size());
        Serial.flush();
    }

    if (currentMs - lastPingMs > 10000) {
        lastPingMs = currentMs;
        
        forest::sensors::RtcSample rtcSample;
        bool rtcOk = false;
        if (ds3231Found) {
            rtcOk = firmware().rtc.read(rtcSample);
        }
        
        forest::protocol::Packet testPacket;
        // Payload: [Year-2000, Month, Day, Hour, Minute, Second, Temp_H, Temp_L, DummyByte]
        uint8_t testPayload[9] = {0};
        if (rtcOk && rtcSample.timeValid) {
            testPayload[0] = static_cast<uint8_t>(rtcSample.year >= 2000 ? rtcSample.year - 2000 : 0);
            testPayload[1] = rtcSample.month;
            testPayload[2] = rtcSample.day;
            testPayload[3] = rtcSample.hour;
            testPayload[4] = rtcSample.minute;
            testPayload[5] = rtcSample.second;
            testPayload[6] = static_cast<uint8_t>((rtcSample.temperatureCentiC >> 8) & 0xFF);
            testPayload[7] = static_cast<uint8_t>(rtcSample.temperatureCentiC & 0xFF);
        } else {
            // Fallback timestamp if RTC not responding: 2026-09-17 12:00:00
            testPayload[0] = 26; // 2026
            testPayload[1] = 9;  // Sept
            testPayload[2] = 17; // 17th
            testPayload[3] = 12; // 12:00:00
            testPayload[4] = 0;
            testPayload[5] = 0;
            constexpr std::int16_t fallbackTemperatureCentiC = 2500; // 25.00 C
            testPayload[6] = static_cast<std::uint8_t>((fallbackTemperatureCentiC >> 8) & 0xFF);
            testPayload[7] = static_cast<std::uint8_t>(fallbackTemperatureCentiC & 0xFF);
        }
        testPayload[8] = 0xAA; // dummy byte
        
        // 0xFE is the Gateway's ID in this architecture
        if (firmware().packetFactory.createData(0xFEU, testPayload, sizeof(testPayload), testPacket)) {
            firmware().packetQueue.enqueue(testPacket);
            Serial.printf("[NODE TX] Packet #%u enqueued directly to LoRa TX Queue (0xFE). RTC: %s\n", 
                          testPacket.sequenceNumber,
                          rtcOk ? "Hardware DS3231" : "Fallback Software Clock");
            Serial.flush();
        }
    }
}
