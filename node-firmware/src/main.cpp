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

namespace
{
    struct FirmwareComposition
    {
        jalari::hal::Esp32SerialConsole console;
        jalari::utils::Logger logger{console};
        jalari::hal::Esp32Clock clock;
        jalari::hal::Esp32Delay delay;
        jalari::hal::Esp32SpiBus spiBus;
        jalari::hal::Esp32I2cBus i2cBus;
        jalari::sensors::Ds3231 rtc{i2cBus};
        jalari::node::NodeManager node{jalari::config::kDefaultFirmwareConfig.node, jalari::node::DeviceRole::BoatNode};
        jalari::lora::LoRaDriver radio{jalari::config::kDefaultFirmwareConfig.radio, spiBus};
        jalari::protocol::PacketFactory packetFactory{node, jalari::config::kDefaultFirmwareConfig.network};
        jalari::queue::PacketQueue packetQueue;
        jalari::event::EventBus eventBus;
        jalari::reliable::AckManager ackManager{jalari::config::kDefaultFirmwareConfig.reliability, node, packetFactory, packetQueue, clock};
        jalari::services::ReliableLinkService reliableLinkService{ackManager};
        jalari::services::DtnStoreForwardService dtnService{clock, eventBus};
        
        jalari::App app{radio, node, packetQueue, eventBus, reliableLinkService, dtnService, logger, packetFactory, console};
    };
    FirmwareComposition &firmware() { static FirmwareComposition composition; return composition; }

    uint32_t lastPingMs = 0;
    bool ds3231Found = false;
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
    Serial.printf("[LORA DIAGNOSTIC] Radio Init: %s (Freq: 433MHz | SCK: 12 | MISO: 13 | MOSI: 11 | NSS: 10 | RST: 9 | DIO0: 14)\n", 
                  radioOk ? "SUCCESS (SX1278 Connected)" : "FAILED (SX1278 Not Responding - Check SPI Wiring!)");
    Serial.flush();

    // Initialize RTC bus
    firmware().rtc.begin(8, 7); // User specified SDA=8, SCL=7

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
    jalari::sensors::RtcSample probeSample;
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
    firmware().app.update();

    uint32_t currentMs = firmware().clock.millis();

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
        
        jalari::sensors::RtcSample rtcSample;
        bool rtcOk = false;
        if (ds3231Found) {
            rtcOk = firmware().rtc.read(rtcSample);
        }
        
        jalari::protocol::Packet testPacket;
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
            testPayload[6] = 0;
            testPayload[7] = 25; // 25 C
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
