#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>
#include <LoRa.h>

#include "Config.h"
#include "Packet.h"
#include "Serializer.h"
#include "PacketFactory.h"
#include "NodeManager.h"

#if FOREST_ACOUSTIC
#include "AcousticPipeline.h"
#endif

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

// Status light: the on-board RGB LED. Green = card on the whitelist, red =
// unknown card. ESP32-S3-DevKitM-1 wires its WS2812 to GPIO 48; override with
// -D FOREST_RGB_LED_PIN=x for boards that differ (e.g. 38 on DevKitC-1 v1.1).
#ifndef FOREST_RGB_LED_PIN
#define FOREST_RGB_LED_PIN 48
#endif
constexpr std::uint8_t kLedLevel = 64;  // 0-255 brightness
void setStatusLed(std::uint8_t red, std::uint8_t green) {
  neopixelWrite(FOREST_RGB_LED_PIN, red, green, 0);
}

// Cards accepted by this node: the officers assigned to the checkpoint this node
// is attached to (NODE_01 = CP-01: OFF001-OFF003). Cards not listed light red,
// including officers assigned to other checkpoints. Keep in sync with the
// checkpoint assignments in the dashboard; the LED cannot ask the backend.
// Add a card as {0xAA, 0xBB, 0xCC, 0xDD} using the UID printed on the monitor.
struct AllowedCard {
  std::uint8_t size;
  std::uint8_t uid[10];
};
const AllowedCard kAllowedCards[] = {
    {4, {0x30, 0xBD, 0x57, 0x58}},  // OFF001
    {4, {0xCD, 0x4E, 0x32, 0x40}},  // OFF002
    {4, {0x0D, 0x46, 0x91, 0x43}},  // OFF003
    // OFF004 BD:8C:6D:19 and OFF005 10:2C:E6:5C belong to CP-02 -> red here
};
bool isCardAllowed(const MFRC522::Uid &uid) {
  for (const AllowedCard &card : kAllowedCards) {
    if (card.size == uid.size && memcmp(card.uid, uid.uidByte, uid.size) == 0) {
      return true;
    }
  }
  return false;
}

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

#if FOREST_ACOUSTIC
// ---- Acoustic events (MAX4466-triggered TinyML, see docs/ACOUSTIC_NODE.md) ---------------------
// Compact payload (6 bytes): 'A', version, class index (1=chainsaw, 2=gunshot),
// confidence as u8 (p*255), trigger RMS u16 little-endian. No raw audio is ever sent.
// Runs from loop() only: loop() owns the SPI bus (RC522 <-> LoRa re-pinning).
static void sendAcousticEvent(const forest::acoustic::AcousticEvent& ev) {
  std::array<std::uint8_t, forest::constants::kMaxPayloadSize> payload{};
  payload[0] = 0x41U;  // 'A'
  payload[1] = 0x01U;  // version
  payload[2] = ev.classIndex;
  payload[3] = static_cast<std::uint8_t>(ev.confidence >= 1.0f ? 255.0f : ev.confidence * 255.0f + 0.5f);
  payload[4] = static_cast<std::uint8_t>(ev.triggerRms & 0xFFU);
  payload[5] = static_cast<std::uint8_t>((ev.triggerRms >> 8U) & 0xFFU);

  forest::protocol::Packet packet;
  std::array<std::uint8_t, 58> buffer{};
  std::size_t encodedSize = 0;
  if (!packetFactory.createData(0xFEU, payload.data(), 6, packet) ||
      !forest::protocol::Serializer::serialize(packet, buffer, encodedSize)) {
    Serial.println("[ACOUSTIC TX] packet creation/serialization FAILED");
    return;
  }
  Serial.printf("[ACOUSTIC TX] class=%u conf=%u/255 rms=%u sequence=%u bytes=%u\n", ev.classIndex, payload[3],
                ev.triggerRms, packet.sequenceNumber, static_cast<unsigned>(encodedSize));
  setStatusLed(kLedLevel, kLedLevel);  // amber flash: acoustic event
  selectLoRaSpi();
  LoRa.idle();
  LoRa.beginPacket();
  LoRa.write(buffer.data(), encodedSize);
  Serial.println(LoRa.endPacket() == 1 ? "[ACOUSTIC TX] LoRa endPacket=SUCCESS" : "[ACOUSTIC TX] LoRa endPacket=FAILED");
  LoRa.receive();
  selectRfidSpi();
  delay(200);
  setStatusLed(0, 0);
}
#endif

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
  setStatusLed(0, 0);

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

#if FOREST_ACOUSTIC
  // Acoustic tasks run on core 0; a failure here must never stop the RFID node.
  forest::acoustic::AcousticPipeline::begin();
#endif

  Serial.println("\nPlace RFID card on reader...");
}

void loop() {
#if FOREST_ACOUSTIC
  {
    forest::acoustic::AcousticEvent acousticEvent;
    while (forest::acoustic::AcousticPipeline::pollEvent(acousticEvent)) sendAcousticEvent(acousticEvent);
  }
#endif
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

  const bool cardValid = isCardAllowed(rfid.uid);
  setStatusLed(cardValid ? 0 : kLedLevel, cardValid ? kLedLevel : 0);
  Serial.println(cardValid ? "[CARD] VALID -> green light" : "[CARD] INVALID -> red light");

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
  setStatusLed(0, 0);
}
