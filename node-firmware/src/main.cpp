#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>
#include <LoRa.h>

#include "Config.h"
#include "Packet.h"
#include "Serializer.h"
#include "PacketFactory.h"
#include "NodeManager.h"

// RC522 wiring. These can be overridden with PlatformIO build flags when a
// different node board is used.
#ifndef FOREST_RFID_SCK_PIN
#define FOREST_RFID_SCK_PIN 35
#endif
#ifndef FOREST_RFID_MISO_PIN
#define FOREST_RFID_MISO_PIN 37
#endif
#ifndef FOREST_RFID_MOSI_PIN
#define FOREST_RFID_MOSI_PIN 36
#endif
#ifndef FOREST_RFID_SS_PIN
#define FOREST_RFID_SS_PIN 4
#endif
#ifndef FOREST_RFID_RST_PIN
#define FOREST_RFID_RST_PIN 5
#endif

#define SCK_PIN   FOREST_RFID_SCK_PIN
#define MISO_PIN  FOREST_RFID_MISO_PIN
#define MOSI_PIN  FOREST_RFID_MOSI_PIN
#define SS_PIN    FOREST_RFID_SS_PIN
#define RST_PIN   FOREST_RFID_RST_PIN

#define LORA_CS   10
#define LORA_RST  9
#define LORA_DIO0 14

MFRC522 rfid(SS_PIN, RST_PIN);
forest::node::NodeManager nodeManager(forest::config::kDefaultFirmwareConfig.node, forest::node::DeviceRole::CheckpointNode);
forest::protocol::PacketFactory packetFactory(nodeManager, forest::config::kDefaultFirmwareConfig.network);

// The RC522 and SX1278 use different SPI pins on this board.  Both drivers
// use Arduino's SPI object, so select the device's pin mapping before using
// it. Their chip-select lines remain high while the other device is active.
void selectRfidSpi() {
  digitalWrite(LORA_CS, HIGH);
  SPI.end();
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, SS_PIN);
}

void selectLoRaSpi() {
  digitalWrite(SS_PIN, HIGH);
  SPI.end();
  SPI.begin(12, 13, 11, LORA_CS);
  LoRa.setSPI(SPI);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("==========================================");
  Serial.println("  SIMPLE RFID -> LORA NODE SENSOR FIRMWARE");
  Serial.println("==========================================");
  Serial.printf("[PIN] RC522 SCK=%d MISO=%d MOSI=%d SS=%d RST=%d\n",
                SCK_PIN, MISO_PIN, MOSI_PIN, SS_PIN, RST_PIN);
  Serial.printf("[PIN] LoRa  SCK=%d MISO=%d MOSI=%d CS=%d RST=%d DIO0=%d\n",
                12, 13, 11, LORA_CS, LORA_RST, LORA_DIO0);

  pinMode(SS_PIN, OUTPUT);
  digitalWrite(SS_PIN, HIGH);
  pinMode(LORA_CS, OUTPUT);
  digitalWrite(LORA_CS, HIGH);

  // Initialize RC522
  selectRfidSpi();
  rfid.PCD_Init();
  delay(100);
  rfid.PCD_SetAntennaGain(MFRC522::RxGain_max);
  Serial.print("RC522 Firmware: 0x");
  Serial.println(rfid.PCD_ReadRegister(MFRC522::VersionReg), HEX);
  Serial.println("RC522 READY");

  // Initialize LoRa
  selectLoRaSpi();
  LoRa.setPins(LORA_CS, LORA_RST, LORA_DIO0);
  if (LoRa.begin(433000000)) {
    LoRa.setSpreadingFactor(7);
    LoRa.setSignalBandwidth(125000L);
    LoRa.setCodingRate4(5);
    LoRa.setSyncWord(0x12);
    LoRa.enableCrc();
    Serial.println("SX1278 LoRa: READY");
    Serial.println("[LORA] Frequency=433000000 SF=7 BW=125000 CR=4/5 Sync=0x12 CRC=ON");
  } else {
    Serial.println("SX1278 LoRa: FAILED");
    Serial.println("[LORA DIAG] Check SX1278 3.3V, GND, antenna, and pins 12/13/11/10/9/14");
  }

  Serial.println("\nPlace RFID card on reader...");
}

void loop() {
  selectRfidSpi();

  // Wait for new card
  if (!rfid.PICC_IsNewCardPresent()) {
    delay(50);
    return;
  }
  if (!rfid.PICC_ReadCardSerial()) {
    Serial.println("Card detected but UID read failed");
    delay(500);
    return;
  }

  Serial.println();
  Serial.println(">>> CARD DETECTED <<<");
  Serial.print("UID: ");
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) Serial.print("0");
    Serial.print(rfid.uid.uidByte[i], HEX);
    if (i < rfid.uid.size - 1) Serial.print(":");
  }
  Serial.println();

  // Create the payload bytes
  std::array<std::uint8_t, forest::constants::kMaxPayloadSize> payload{};
  payload[0] = 0x52U; // 'R'
  payload[1] = 0x01U; // Version
  payload[2] = rfid.uid.size;
  for (std::size_t i = 0; i < rfid.uid.size; ++i) {
      payload[3 + i] = rfid.uid.uidByte[i];
  }

  // These commands still target the RC522, so finish them before changing
  // the SPI pin mapping for the LoRa transmitter.
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  // Format packet with CRC for the Gateway
  forest::protocol::Packet rfidPacket;
  if (packetFactory.createData(0xFEU, payload.data(), 3 + rfid.uid.size, rfidPacket)) {
      std::array<std::uint8_t, 58> buffer{};
      std::size_t encodedSize = 0;

      // Serialize to binary
      if (forest::protocol::Serializer::serialize(rfidPacket, buffer, encodedSize)) {
          Serial.printf("[NODE TX] DATA source=0x%02X destination=0x%02X sequence=%u bytes=%u payload=%u\n",
                        rfidPacket.sourceId, rfidPacket.destinationId,
                        rfidPacket.sequenceNumber, static_cast<unsigned>(encodedSize),
                        static_cast<unsigned>(rfidPacket.payloadSize));
          Serial.print("[NODE TX] HEX: ");
          for (std::size_t i = 0; i < encodedSize; ++i) {
              Serial.printf("%02X%s", buffer[i], (i + 1U == encodedSize) ? "" : " ");
          }
          Serial.println();

          // Send over LoRa
          selectLoRaSpi();
          LoRa.idle();
          LoRa.beginPacket();
          LoRa.write(buffer.data(), encodedSize);
          if (LoRa.endPacket() == 1) {
              Serial.println("[NODE TX] LoRa endPacket=SUCCESS (radio completed transmission)");
          } else {
              Serial.println("[NODE TX] LoRa endPacket=FAILED");
          }
          LoRa.receive();
      }
      else {
          Serial.println("[NODE TX] Packet serialization FAILED");
      }
  }
  else {
      Serial.println("[NODE TX] RFID packet creation FAILED");
  }

  // Return to the RC522 mapping so it is ready for the next card scan.
  selectRfidSpi();

  delay(1000); // Wait 1 second before allowing next scan
}
