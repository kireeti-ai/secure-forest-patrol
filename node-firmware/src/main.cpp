#include <Arduino.h>
#include <SPI.h>
#include "LittleFsBackend.h"
#include "LocalEventStore.h"
#include "DS3231.h"
#include "RFID_RC522.h"   // our own RC522 SPI driver (lib/ForestSensors), no MFRC522 library
#include <LoRa.h>

#include "Config.h"
#include "Packet.h"
#include "Serializer.h"
#include "PacketFactory.h"
#include "Parser.h"
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
#ifndef FOREST_I2C_SDA_PIN
#define FOREST_I2C_SDA_PIN 21
#endif
#ifndef FOREST_I2C_SCL_PIN
#define FOREST_I2C_SCL_PIN 20
#endif
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
bool isCardAllowed(const ForestSensors::RfidUid &uid) {
  for (const AllowedCard &card : kAllowedCards) {
    if (card.size == uid.size && memcmp(card.uid, uid.bytes, uid.size) == 0) {
      return true;
    }
  }
  return false;
}

ForestSensors::RFID_RC522 rfid(SS_PIN, RST_PIN);
ForestSensors::RfidUid cardUid;

// Local event store on the internal flash (LittleFS). Every RFID / acoustic event is written here as
// PENDING_SYNC BEFORE it is transmitted and marked SYNCED once the radio completes the transmission.
forest::storage::LittleFsBackend flashBackend;
forest::storage::LocalEventStore eventStore(flashBackend, 512);
bool storeReady = false;
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

enum class TxResult { Failed, SentNoAck, Acked };

// The gateway answers every DATA packet with an Acknowledgement packet whose payload is the acknowledged
// 16-bit sequence number (gateway/src/Gateway/GatewayAckHandler.cpp). The radio is already in receive mode.
static bool waitForGatewayAck(std::uint16_t sentSequence, std::uint32_t timeoutMs) {
  const std::uint32_t start = millis();
  while (millis() - start < timeoutMs) {
    if (LoRa.parsePacket() > 0) {
      std::array<std::uint8_t, 64> rx{};
      std::size_t len = 0;
      while (LoRa.available() && len < rx.size()) rx[len++] = static_cast<std::uint8_t>(LoRa.read());
      forest::protocol::Packet ack;
      if (forest::protocol::Parser::parse(rx.data(), len, ack) &&
          ack.type == forest::protocol::PacketType::Acknowledgement && ack.destinationId == nodeManager.id() &&
          ack.payloadSize >= 2 &&
          static_cast<std::uint16_t>(ack.payload[0] | (ack.payload[1] << 8)) == sentSequence) {
        return true;
      }
    }
    delay(5);
  }
  return false;
}

// Wraps `payload` in a Forest DATA packet, sends it over LoRa, then waits for the gateway's acknowledgement of
// that packet. Acked = the gateway received it; SentNoAck = the radio finished but nobody confirmed (gateway
// off / out of range / deaf). Runs from loop() only: loop() owns the SPI bus (RC522 <-> LoRa re-pinning).
static TxResult transmitPayload(const std::uint8_t* payload, std::size_t len, const char* tag, bool hexDump) {
  forest::protocol::Packet packet;
  std::array<std::uint8_t, 58> buffer{};
  std::size_t encodedSize = 0;
  if (!packetFactory.createData(0xFEU, payload, len, packet) ||
      !forest::protocol::Serializer::serialize(packet, buffer, encodedSize)) {
    Serial.printf("[%s] packet creation/serialization FAILED\n", tag);
    return TxResult::Failed;
  }
  Serial.printf("[%s] DATA source=0x%02X destination=0x%02X sequence=%u bytes=%u payload=%u\n", tag, packet.sourceId,
                packet.destinationId, packet.sequenceNumber, static_cast<unsigned>(encodedSize),
                static_cast<unsigned>(packet.payloadSize));
  if (hexDump) {
    Serial.printf("[%s] HEX: ", tag);
    for (std::size_t i = 0; i < encodedSize; ++i) Serial.printf("%02X%s", buffer[i], (i + 1U == encodedSize) ? "" : " ");
    Serial.println();
  }
  selectLoRaSpi();
  LoRa.idle();
  LoRa.beginPacket();
  LoRa.write(buffer.data(), encodedSize);
  const bool ok = LoRa.endPacket() == 1;
  Serial.printf(ok ? "[%s] LoRa endPacket=SUCCESS (radio completed transmission)\n" : "[%s] LoRa endPacket=FAILED\n", tag);
  LoRa.receive();
  TxResult result = ok ? TxResult::SentNoAck : TxResult::Failed;
  if (ok) {
    if (waitForGatewayAck(packet.sequenceNumber, 1500)) {
      result = TxResult::Acked;
      Serial.printf("[%s] Gateway ACK received for sequence %u\n", tag, packet.sequenceNumber);
    } else {
      Serial.printf("[%s] NO gateway ACK within 1500 ms for sequence %u\n", tag, packet.sequenceNumber);
    }
  }
  selectRfidSpi();
  return result;
}

// ---- Local event store glue --------------------------------------------------------------------
static void printRecord(const forest::storage::EventRecord& r) {
  char id[24];
  forest::storage::formatEventId(r, id, sizeof id);
  Serial.printf("[LOCAL STORE]   %-19s type=%-8s status=%-12s boot=%lu uptime=%lums attempts=%u payload=", id,
                forest::storage::typeName(r.type), forest::storage::statusName(r.status), (unsigned long)r.bootCount,
                (unsigned long)r.uptimeMs, r.attempts);
  for (std::uint8_t i = 0; i < r.payloadLen; ++i) Serial.printf("%02X", r.payload[i]);
  Serial.println();
}

static void printStore(const char* heading) {
  const auto& st = eventStore.stats();
  Serial.printf("[LOCAL STORE] %s: records=%lu pending=%lu synced=%lu (capacity %u, boot #%lu)\n", heading,
                (unsigned long)st.records, (unsigned long)st.pending, (unsigned long)st.synced,
                static_cast<unsigned>(eventStore.capacity()), (unsigned long)st.bootCount);
  for (std::size_t i = 0; i < eventStore.slotCount(); ++i) {
    forest::storage::EventRecord r;
    if (eventStore.readAt(i, r)) printRecord(r);
  }
}

// Persist the event first; returns false (event still sent) if the store is unavailable.
static bool storeEvent(forest::storage::EventType type, const std::uint8_t* payload, std::size_t len,
                       forest::storage::EventRecord& out) {
  if (!storeReady || !eventStore.append(type, static_cast<std::uint8_t>(FOREST_NODE_ID), payload, len, millis(), &out)) {
    Serial.println("[LOCAL STORE] write FAILED - sending without local copy");
    return false;
  }
  char id[24];
  forest::storage::formatEventId(out, id, sizeof id);
  Serial.printf("[LOCAL STORE] Event written\n[LOCAL STORE] Event ID = %s\n[LOCAL STORE] Status = PENDING_SYNC\n", id);
  return true;
}

static void finishStoredEvent(const forest::storage::EventRecord& rec, TxResult result) {
  char id[24];
  forest::storage::formatEventId(rec, id, sizeof id);
  if (result == TxResult::Acked && eventStore.markSynced(rec.localId)) {
    Serial.printf("[LOCAL STORE] %s -> SYNCED (gateway acknowledged)\n", id);
  } else {
    eventStore.markAttempt(rec.localId);
    Serial.printf("[LOCAL STORE] %s stays PENDING_SYNC (no gateway ACK, will be retried)\n", id);
  }
}

// A pending event whose transmission failed (or was cut short by a reset) is retried here, oldest first.
static void retryPendingEvent() {
  static std::uint32_t lastTryMs = 0;
  if (!storeReady || millis() - lastTryMs < 15000) return;
  lastTryMs = millis();
  forest::storage::EventRecord rec;
  if (!eventStore.oldestPending(rec)) return;   // TEST events are never transmitted
  Serial.print("[LOCAL STORE] Retrying pending event\n");
  printRecord(rec);
  finishStoredEvent(rec, transmitPayload(rec.payload, rec.payloadLen, "RETRY TX", false));
}

// Storage demo, typed into the serial monitor: w = write TEST event, l = list, m = mark oldest pending
// synced, r = reboot, x = erase, ? = help.
static void handleSerialCommand() {
  while (Serial.available() > 0) {
    const int c = Serial.read();
    if (c == '\n' || c == '\r' || c == ' ') continue;
    switch (c) {
      case 'w': {
        const std::uint8_t testPayload[2] = {'T', 0x01};
        forest::storage::EventRecord r;
        Serial.println("[LOCAL STORE] Writing test event...");
        if (storeEvent(forest::storage::EventType::Test, testPayload, 2, r)) Serial.println("[LOCAL STORE] Write OK");
        break;
      }
      case 'l': printStore("Contents"); break;
      case 't': {   // custom driver check: RC522 registers over SPI, DS3231 over I2C (SDA 21 / SCL 20)
        Serial.printf("[DRIVER] RC522 (SPI, ForestSensors::RFID_RC522): VersionReg=0x%02X TxControlReg=0x%02X\n", rfid.version(),
                      rfid.readReg(0x14));
        ForestSensors::DS3231 rtc;
        ForestSensors::DateTime now;
        if (rtc.begin(FOREST_I2C_SDA_PIN, FOREST_I2C_SCL_PIN) && rtc.readDateTime(now)) {
          int16_t tc = 0;
          rtc.readTemperatureCentiC(tc);
          Serial.printf("[DRIVER] DS3231 (I2C, ForestSensors::DS3231): %04u-%02u-%02u %02u:%02u:%02u  temp=%d.%02d C%s\n", now.year, now.month,
                        now.day, now.hour, now.minute, now.second, tc / 100, abs(tc % 100), rtc.lostPower() ? "  (oscillator was stopped: time NOT valid)" : "");
        } else {
          Serial.println("[DRIVER] DS3231 (I2C): no device answered at 0x68 (not connected)");
        }
        break;
      }
      case 'm': {
        forest::storage::EventRecord r;
        if (eventStore.oldestPending(r, true) && eventStore.markSynced(r.localId)) {
          char id[24];
          forest::storage::formatEventId(r, id, sizeof id);
          Serial.printf("[LOCAL STORE] Marking %s synced\n[LOCAL STORE] Status = SYNCED\n", id);
        } else {
          Serial.println("[LOCAL STORE] Nothing pending");
        }
        break;
      }
      case 'r': Serial.println("[LOCAL STORE] Rebooting..."); Serial.flush(); delay(100); ESP.restart(); break;
      case 'x': Serial.println(eventStore.clear() ? "[LOCAL STORE] Log erased" : "[LOCAL STORE] erase FAILED"); break;
      default:
        Serial.println("[LOCAL STORE] commands: w=write TEST event  l=list  m=mark oldest pending synced  r=reboot  x=erase  t=driver check (RC522/RTC)");
    }
  }
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

  Serial.printf("[ACOUSTIC TX] class=%u conf=%u/255 rms=%u\n", ev.classIndex, payload[3], ev.triggerRms);
  forest::storage::EventRecord stored;
  const bool haveRec = storeEvent(forest::storage::EventType::Acoustic, payload.data(), 6, stored);
  setStatusLed(kLedLevel, kLedLevel);  // amber flash: acoustic event
  const TxResult sent = transmitPayload(payload.data(), 6, "ACOUSTIC TX", false);
  if (haveRec) finishStoredEvent(stored, sent);
  delay(200);
  setStatusLed(0, 0);
}
#endif

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("==========================================");
  Serial.println("  SECURE OFFLINE PATROL VERIFICATION - NODE");
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
  const bool rfidOk = rfid.begin(SPI);
  delay(100);
  rfid.setAntennaGainMax();
  Serial.print("RC522 Firmware: 0x");
  Serial.println(rfid.version(), HEX);
  Serial.println(rfidOk ? "RC522 READY (ForestSensors custom SPI driver)" : "RC522 NOT FOUND (check wiring)");

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

  // Local event store (internal flash). A failure here must never stop the RFID node.
  storeReady = eventStore.begin();
  if (storeReady) {
    const auto& st = eventStore.stats();
    Serial.printf("[LOCAL STORE] Initialized (LittleFS, capacity %u records, boot #%lu)\n",
                  static_cast<unsigned>(eventStore.capacity()), (unsigned long)st.bootCount);
    Serial.printf("[LOCAL STORE] Recovered %lu events (%lu pending, %lu synced)\n", (unsigned long)st.records,
                  (unsigned long)st.pending, (unsigned long)st.synced);
    if (st.corruptSkipped || st.duplicatesSkipped || st.tornTailBytes)
      Serial.printf("[LOCAL STORE] Repaired log: %lu corrupt, %lu duplicate, %lu torn bytes\n", (unsigned long)st.corruptSkipped,
                    (unsigned long)st.duplicatesSkipped, (unsigned long)st.tornTailBytes);
    printStore("Recovered");
    Serial.println("[LOCAL STORE] Serial commands: w=write TEST event  l=list  m=mark synced  r=reboot  x=erase");
  } else {
    Serial.println("[LOCAL STORE] Initialization FAILED - events will not be persisted");
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
  handleSerialCommand();
  retryPendingEvent();

  // Wait for new card
  if (!rfid.isCardPresent()) {
    delay(50);
    return;
  }
  if (!rfid.readUid(cardUid)) {
    Serial.println("Card detected but UID read failed");
    delay(500);
    return;
  }

  Serial.println();
  Serial.println(">>> CARD DETECTED <<<");
  Serial.print("UID: ");
  for (byte i = 0; i < cardUid.size; i++) {
    if (cardUid.bytes[i] < 0x10) Serial.print("0");
    Serial.print(cardUid.bytes[i], HEX);
    if (i < cardUid.size - 1) Serial.print(":");
  }
  Serial.println();

  const bool cardValid = isCardAllowed(cardUid);
  setStatusLed(cardValid ? 0 : kLedLevel, cardValid ? kLedLevel : 0);
  Serial.println(cardValid ? "[CARD] VALID -> green light" : "[CARD] INVALID -> red light");

  // Create the payload bytes
  std::array<std::uint8_t, forest::constants::kMaxPayloadSize> payload{};
  payload[0] = 0x52U; // 'R'
  payload[1] = 0x01U; // Version
  payload[2] = cardUid.size;
  for (std::size_t i = 0; i < cardUid.size; ++i) {
      payload[3 + i] = cardUid.bytes[i];
  }

  // Persist first, then transmit. The halt command still targets the RC522, so finish it before the SPI bus
  // is switched to the LoRa transmitter.
  forest::storage::EventRecord stored;
  const std::size_t payloadLen = 3 + cardUid.size;
  const bool haveRec = storeEvent(forest::storage::EventType::Rfid, payload.data(), payloadLen, stored);
  rfid.halt();
  const TxResult sent = transmitPayload(payload.data(), payloadLen, "NODE TX", true);
  if (haveRec) finishStoredEvent(stored, sent);

  // Return to the RC522 mapping so it is ready for the next card scan.
  selectRfidSpi();

  delay(1000); // Wait 1 second before allowing next scan
  setStatusLed(0, 0);
}
