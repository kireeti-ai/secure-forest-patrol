#include <Arduino.h>
#include <SPI.h>
#include "LittleFsBackend.h"
#include "LocalEventStore.h"
#include "DS3231.h"
#include "NodeIdentity.h"
#include "PatrolSigningBytes.h"
#include "PatrolChainHash.h"
#include "PatrolChainState.h"
#include "SignedPatrolPayload.h"
#include "LoRaCipher.h"
#include "SoftClock.h"
#include "Hex.h"
#include <base64.h>
#include "RFID_RC522.h"   // our own RC522 SPI driver (lib/ForestSensors), no MFRC522 library
#include "R307Fingerprint.h"
#include <LoRa.h>

#include "Config.h"
#include "Packet.h"
#include "Serializer.h"
#include "PacketFactory.h"
#include "Parser.h"
#include "NodeManager.h"

#if FOREST_ACOUSTIC
#include "AcousticPipeline.h"
#include "AcousticConfig.h"
#include "AcousticChainState.h"
#include "AcousticConfidenceTable.h"
#include "SignedAcousticPayload.h"
#endif

// 1 = normal verbose local-store logging (boot replay dump, per-retry chatter).
// 0 = quiet: skips the full history dump at boot and the "[LOCAL STORE] Retrying
// pending event" lines on every background retry -- handy during bench testing
// when a large backlog of unACKed events (no gateway attached) floods the console.
#ifndef FOREST_VERBOSE_STORE
#define FOREST_VERBOSE_STORE 1
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

#ifndef FOREST_FINGER_RX_PIN
#define FOREST_FINGER_RX_PIN 16
#endif
#ifndef FOREST_FINGER_TX_PIN
#define FOREST_FINGER_TX_PIN 17
#endif
#ifndef FOREST_FINGER_BAUD
#define FOREST_FINGER_BAUD 57600
#endif

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

// RFID/fingerprint use red/green/amber; acoustic gets its own blue channel so a chainsaw/gunshot
// flash can never be confused with (or stomp on) the "awaiting fingerprint" amber held by the
// two-factor window -- see sendAcousticEvent(), which must restore amber afterward if still awaiting.
void setStatusLed(std::uint8_t red, std::uint8_t green, std::uint8_t blue = 0) {
  neopixelWrite(FOREST_RGB_LED_PIN, red, green, blue);
}

// Cards accepted by this node: the officers assigned to the checkpoint this node
// is attached to (NODE_01 = CP-01: OFF001-OFF003). Cards not listed light red,
// including officers assigned to other checkpoints. Keep in sync with the
// checkpoint assignments in the dashboard; the LED cannot ask the backend.
// Add a card as {0xAA, 0xBB, 0xCC, 0xDD} using the UID printed on the monitor.
// fingerprintPageId is that officer's enrolled R307S template slot (see
// fingerprint_enroll_diagnostic.cpp) -- this is the second factor: a card tap
// only arms the verification window, it never completes a visit by itself.
struct AllowedCard {
  std::uint8_t size;
  std::uint8_t uid[10];
  std::uint16_t fingerprintPageId;
  const char* officerLabel;
};
const AllowedCard kAllowedCards[] = {
    {4, {0x30, 0xBD, 0x57, 0x58}, 1, "OFF001"},
    {4, {0xCD, 0x4E, 0x32, 0x40}, 2, "OFF002"},
    {4, {0x0D, 0x46, 0x91, 0x43}, 3, "OFF003"},
    // OFF004 BD:8C:6D:19 and OFF005 10:2C:E6:5C belong to CP-02 -> red here
};
// Every known officer card system-wide, for identification/logging only (bench labeling,
// "whose card is this") -- NOT used for the LED decision. A card can be known here but still
// light red because it is not in kAllowedCards (wrong checkpoint for this node).
const AllowedCard kKnownCards[] = {
    {4, {0x30, 0xBD, 0x57, 0x58}, 1, "OFF001"},
    {4, {0xCD, 0x4E, 0x32, 0x40}, 2, "OFF002"},
    {4, {0x0D, 0x46, 0x91, 0x43}, 3, "OFF003"},
    {4, {0xBD, 0x8C, 0x6D, 0x19}, 4, "OFF004"},
    {4, {0x10, 0x2C, 0xE6, 0x5C}, 5, "OFF005"},
};
const char* findKnownCardLabel(const ForestSensors::RfidUid &uid) {
  for (const AllowedCard &card : kKnownCards) {
    if (card.size == uid.size && memcmp(card.uid, uid.bytes, uid.size) == 0) {
      return card.officerLabel;
    }
  }
  return nullptr;
}
const AllowedCard* findAllowedCard(const ForestSensors::RfidUid &uid) {
  for (const AllowedCard &card : kAllowedCards) {
    if (card.size == uid.size && memcmp(card.uid, uid.bytes, uid.size) == 0) {
      return &card;
    }
  }
  return nullptr;
}

// ---- Two-factor verification state (card tap -> fingerprint within kVerifyWindowMs) ------------
enum class VerifyState { Idle, AwaitingFingerprint };
enum class VerifyStatus : std::uint8_t { Match = 1, Mismatch = 2, Timeout = 3 };
constexpr std::uint16_t kNoPageId = 0xFFFFU;
constexpr std::uint32_t kVerifyWindowMs = 10000U;
VerifyState verifyState = VerifyState::Idle;
std::uint32_t verifyDeadlineMs = 0;
ForestSensors::RfidUid pendingUid;
std::uint16_t pendingExpectedPageId = 0;
const char* pendingOfficerLabel = "";

ForestSensors::RFID_RC522 rfid(SS_PIN, RST_PIN);
ForestSensors::RfidUid cardUid;
HardwareSerial fingerprintSerial(2);
ForestSensors::R307Fingerprint fingerprint(fingerprintSerial, FOREST_FINGER_RX_PIN,
                                            FOREST_FINGER_TX_PIN, FOREST_FINGER_BAUD);
// Local event store on the internal flash (LittleFS). Every RFID / acoustic event is written here as
// PENDING_SYNC BEFORE it is transmitted and marked SYNCED once the radio completes the transmission.
forest::storage::LittleFsBackend flashBackend;
forest::storage::LocalEventStore eventStore(flashBackend, 512);
bool storeReady = false;

// Per-node ECDSA P-256 identity (Phase 2, docs/TAMPER_EVIDENCE_SECURITY_PLAN.md). Generated once
// on first boot, persisted in NVS; signSha256() not yet wired into the RFID/acoustic event path
// (that needs real timestamps/checkpoint/officer fields first) - 'k' is a bench command to
// exercise and cross-verify the primitive itself against backend/app/services/crypto.py.
forest::crypto::NodeIdentity nodeIdentity;
bool identityReady = false;

// No RTC chip on this board: real UTC time is learned opportunistically from the gateway's ACK
// (see Constants.h::kAcknowledgementPayloadSizeWithTime) and estimated from millis() drift
// between syncs. See lib/ForestTime/src/SoftClock.h for the accuracy/limitations tradeoff.
forest::time::SoftClock softClock;
// Hash-chain state for the backend-verified signed patrol event stream (distinct from Phase 1's
// local tamper-evidence chain in LocalEventStore - see PatrolChainState.h for why there are two).
forest::crypto::PatrolChainState patrolChain;
#if FOREST_ACOUSTIC
// Separate hash-chain state for signed acoustic events - see AcousticChainState.h for why this
// is not the same counter/chain as patrolChain.
forest::crypto::AcousticChainState acousticChain;
#endif
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
        if (ack.payloadSize >= forest::constants::kAcknowledgementPayloadSizeWithTime) {
          const uint32_t gatewayUtc = static_cast<uint32_t>(ack.payload[2]) | (static_cast<uint32_t>(ack.payload[3]) << 8) |
                                      (static_cast<uint32_t>(ack.payload[4]) << 16) | (static_cast<uint32_t>(ack.payload[5]) << 24);
          softClock.onSync(gatewayUtc);
        }
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
  std::array<std::uint8_t, forest::constants::kMaxPacketSize> buffer{};
  std::size_t encodedSize = 0;
  if (!packetFactory.createData(0xFEU, payload, len, packet)) {
    Serial.printf("[%s] packet creation FAILED\n", tag);
    return TxResult::Failed;
  }

  // Phase 4 (docs/TAMPER_EVIDENCE_SECURITY_PLAN.md): encrypt the application payload in place
  // before serialization. The outer header (type/source/dest/sequence) packetFactory just
  // assigned stays in clear - the gateway needs it to route/ACK/CRC-check before it can even
  // attempt a decrypt - and is bound into the ciphertext as AAD, so a captured ciphertext can't
  // be replayed under a different header.
  static const std::uint8_t kLoRaAesKey[forest::crypto::kGcmKeyBytes] = FOREST_LORA_AES_KEY;
  const forest::crypto::PacketAad aad{static_cast<std::uint8_t>(packet.type), packet.sourceId,
                                      packet.destinationId, packet.sequenceNumber};
  std::array<std::uint8_t, forest::constants::kMaxPayloadSize> encrypted{};
  std::size_t encryptedLen = 0;
  if (!forest::crypto::loRaEncrypt(kLoRaAesKey, aad, packet.payload.data(), packet.payloadSize, encrypted.data(),
                                   encrypted.size(), encryptedLen) ||
      !packet.setPayload(encrypted.data(), encryptedLen)) {
    Serial.printf("[%s] LoRa payload encryption FAILED\n", tag);
    return TxResult::Failed;
  }

  if (!forest::protocol::Serializer::serialize(packet, buffer, encodedSize)) {
    Serial.printf("[%s] packet serialization FAILED\n", tag);
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
#if FOREST_VERBOSE_STORE
  Serial.print("[LOCAL STORE] Retrying pending event\n");
  printRecord(rec);
#endif
  finishStoredEvent(rec, transmitPayload(rec.payload, rec.payloadLen, "RETRY TX", false));
}

// Combined two-factor result, sent once the verification window resolves. Payload (<=24 bytes,
// see EventRecord.h): ['V', ver, status, uidLen, uid[uidLen], claimedPageId u16 LE, actualPageId
// u16 LE (kNoPageId if none), score u16 LE (0 for TIMEOUT)].
static void sendVerificationEvent(VerifyStatus status, const ForestSensors::RfidUid& uid,
                                  std::uint16_t claimedPageId, std::uint16_t actualPageId,
                                  std::uint16_t score) {
  std::array<std::uint8_t, forest::constants::kMaxPayloadSize> payload{};
  payload[0] = 0x56U;  // 'V'
  payload[1] = 0x01U;
  payload[2] = static_cast<std::uint8_t>(status);
  payload[3] = uid.size;
  for (std::size_t i = 0; i < uid.size; ++i) payload[4 + i] = uid.bytes[i];
  std::size_t off = 4U + uid.size;
  payload[off++] = static_cast<std::uint8_t>(claimedPageId & 0xFFU);
  payload[off++] = static_cast<std::uint8_t>(claimedPageId >> 8U);
  payload[off++] = static_cast<std::uint8_t>(actualPageId & 0xFFU);
  payload[off++] = static_cast<std::uint8_t>(actualPageId >> 8U);
  payload[off++] = static_cast<std::uint8_t>(score & 0xFFU);
  payload[off++] = static_cast<std::uint8_t>(score >> 8U);

  const char* statusName = status == VerifyStatus::Match ? "MATCH" : status == VerifyStatus::Mismatch ? "MISMATCH" : "TIMEOUT";
  Serial.printf("[VERIFY] %s claimedPage=%u actualPage=%u score=%u\n", statusName, claimedPageId, actualPageId, score);

  forest::storage::EventRecord stored;
  const bool haveRec = storeEvent(forest::storage::EventType::Verification, payload.data(), off, stored);
  setStatusLed(status == VerifyStatus::Match ? 0 : kLedLevel, status == VerifyStatus::Match ? kLedLevel : 0);

  // Phase 2 (docs/TAMPER_EVIDENCE_SECURITY_PLAN.md): the signed, hash-chained patrol event is a
  // strict superset of the legacy unsigned 'V' one (same rfid/fingerprint result, plus a
  // signature and chain link) and nothing forwards the legacy topic on the backend side
  // anymore (the EMQX rule that used to was repurposed to the signed one) - sending both wastes
  // airtime for no reason. So: try the signed send first; only fall back to the legacy
  // transmission if identity/clock aren't ready yet (e.g. this boot hasn't synced time with the
  // gateway). LocalEventStore's sync marking follows whichever one actually went out, since
  // that's the real transmission attempt for this event now.
  bool signedPathUsed = false;
  TxResult sentResult = TxResult::Failed;
  char eventIso[32];
  if (identityReady && softClock.nowIso8601Utc(eventIso, sizeof eventIso)) {
    char nodeIdStr[16];
    snprintf(nodeIdStr, sizeof nodeIdStr, "NODE_%02X", static_cast<unsigned>(FOREST_NODE_ID));
    char officerUidHex[forest::crypto::kMaxOfficerUidLen * 2 + 1];
    forest::utils::bytesToHex(uid.bytes, uid.size, officerUidHex);
    const uint8_t rfidCode = 1;   // VALID - this function only runs for a card that already matched
    const uint8_t fpCode = status == VerifyStatus::Match ? 1 : 2;   // MATCH : NO_MATCH
    const char* rfidStr = "VALID";
    const char* fpStr = fpCode == 1 ? "MATCH" : "NO_MATCH";

    char payloadDigest[65];
    forest::crypto::patrolPayloadDigestHex(FOREST_CHECKPOINT_ID, officerUidHex, rfidStr, fpStr, payloadDigest);
    const uint32_t seq = patrolChain.nextSequence();
    char recordHashHex[65];
    forest::crypto::computeRecordHashHex(nodeIdStr, seq, eventIso, payloadDigest, patrolChain.previousHashHex(), recordHashHex);

    uint8_t prevHashRaw[32] = {0}, recHashRaw[32];
    if (patrolChain.previousHashHex()[0]) forest::utils::hexToBytes(patrolChain.previousHashHex(), 32, prevHashRaw);
    forest::utils::hexToBytes(recordHashHex, 32, recHashRaw);

    char canonical[512];
    forest::crypto::buildPatrolSigningBytes(nodeIdStr, seq, eventIso, FOREST_CHECKPOINT_ID, officerUidHex,
                                            rfidStr, fpStr, patrolChain.previousHashHex(), recordHashHex,
                                            canonical, sizeof canonical);
    uint8_t sig[forest::crypto::kMaxSignatureBytes];
    size_t sigLen = 0;
    if (nodeIdentity.signSha256(reinterpret_cast<const uint8_t*>(canonical), strlen(canonical), sig, sigLen)) {
      uint32_t epoch = 0;
      softClock.nowEpoch(epoch);
      std::array<std::uint8_t, forest::constants::kMaxPayloadSize> signedPayload{};
      const size_t len = forest::crypto::encodeSignedPatrolPayload(
          seq, epoch, rfidCode, fpCode, FOREST_CHECKPOINT_ID, strlen(FOREST_CHECKPOINT_ID),
          uid.bytes, uid.size, prevHashRaw, recHashRaw, sig, sigLen, signedPayload.data(), signedPayload.size());
      if (len > 0) {
        patrolChain.commit(recordHashHex);
        sentResult = transmitPayload(signedPayload.data(), len, "SIGNED PATROL TX", false);
        signedPathUsed = true;
        Serial.printf("[SIGNED PATROL] seq=%lu record_hash=%s tx=%s\n", static_cast<unsigned long>(seq),
                      recordHashHex, sentResult == TxResult::Failed ? "FAILED" : "SENT");
      } else {
        Serial.println("[SIGNED PATROL] encode FAILED (payload too large?) - not sent, sequence not advanced");
      }
    } else {
      Serial.println("[SIGNED PATROL] sign FAILED - not sent");
    }
  }
  if (!signedPathUsed) {
    // Fallback: no identity/synced clock yet, so there is no signed event to send - use the
    // legacy unsigned payload instead rather than transmitting nothing at all.
    sentResult = transmitPayload(payload.data(), off, "VERIFY TX", true);
  }
  if (haveRec) finishStoredEvent(stored, sentResult);

  delay(status == VerifyStatus::Match ? 200 : 500);  // mismatch/timeout gets a longer, visible red
  setStatusLed(0, 0);
}

static void pollFingerprint() {
  static std::uint32_t lastPollMs = 0;
  static std::uint32_t lastCountdownMs = 0;

  // Nothing pending: don't touch the sensor at all. fingerprint.poll() is a blocking
  // UART round-trip (up to ~1.9s worst case once a finger is actually resting on the
  // sensor) -- calling it on every loop pass regardless of state stalled RFID polling,
  // serial commands and the LoRa watchdog whenever a finger happened to be on the sensor
  // outside a verification window.
  if (verifyState != VerifyState::AwaitingFingerprint) return;

  if (millis() - lastCountdownMs >= 1000U) {
    lastCountdownMs = millis();
    const std::int32_t remainingMs = static_cast<std::int32_t>(verifyDeadlineMs - millis());
    if (remainingMs > 0) {
      const std::uint32_t secondsLeft = (remainingMs + 999) / 1000;
      Serial.printf(">>> PLACE FINGER NOW -- %lu s left <<<\n", (unsigned long)secondsLeft);
    }
  }

  // Checked unconditionally (not gated behind fingerprint.ready()/the poll interval below)
  // so the window always expires on time even if the sensor is unresponsive.
  if (millis() > verifyDeadlineMs) {
    Serial.println("[VERIFY] window expired, no fingerprint presented");
    sendVerificationEvent(VerifyStatus::Timeout, pendingUid, pendingExpectedPageId, kNoPageId, 0U);
    verifyState = VerifyState::Idle;
    return;
  }

  if (!fingerprint.ready() || millis() - lastPollMs < 150U) return;
  lastPollMs = millis();

  ForestSensors::FingerprintMatch match;
  const ForestSensors::FingerprintScanResult result = fingerprint.poll(match);
  if (result == ForestSensors::FingerprintScanResult::NoFinger) return;

  const std::uint16_t actualPageId = (result == ForestSensors::FingerprintScanResult::Matched) ? match.pageId : kNoPageId;
  const std::uint16_t score = (result == ForestSensors::FingerprintScanResult::Matched) ? match.score : 0U;
  const VerifyStatus status = (result == ForestSensors::FingerprintScanResult::Matched && match.pageId == pendingExpectedPageId)
                                   ? VerifyStatus::Match
                                   : VerifyStatus::Mismatch;
  sendVerificationEvent(status, pendingUid, pendingExpectedPageId, actualPageId, score);
  verifyState = VerifyState::Idle;
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
      case 'k': {   // bench: print pubkey + sign a demo canonical patrol message (Phase 2 identity)
        if (!identityReady) { Serial.println("[IDENTITY] not ready"); break; }
        char pubHex[forest::crypto::kPublicKeyBytes * 2 + 1];
        nodeIdentity.publicKeyHex(pubHex, sizeof pubHex);
        char iso[32];
        if (!softClock.nowIso8601Utc(iso, sizeof iso)) {
          Serial.println("[IDENTITY] no synced time yet (no gateway ACK with a time field received this boot) "
                         "- using a placeholder timestamp for this demo signature only");
          forest::crypto::formatIso8601Utc(2026, 1, 15, 10, 30, 0, iso, sizeof iso);
        }
        char canonical[256];
        forest::crypto::buildPatrolSigningBytes("N01", 7, iso, "CP1", "OFF9", "VALID", "MATCH", "",
                                                 "deadbeef", canonical, sizeof canonical);
        uint8_t sig[forest::crypto::kMaxSignatureBytes];
        size_t sigLen = 0;
        if (!nodeIdentity.signSha256(reinterpret_cast<const uint8_t*>(canonical), strlen(canonical), sig, sigLen)) {
          Serial.println("[IDENTITY] sign FAILED");
          break;
        }
        Serial.printf("[IDENTITY] pubkey_hex=%s\n", pubHex);
        Serial.printf("[IDENTITY] canonical=%s\n", canonical);
        Serial.printf("[IDENTITY] signature_b64=%s\n", base64::encode(sig, sigLen).c_str());
        Serial.println("[IDENTITY] cross-verify with: python3 node-firmware/tools/verify_node_signature.py "
                       "<pubkey_hex> '<canonical>' <signature_b64>");
        break;
      }
      case 'v': {   // verify the on-flash hash chain (Phase 1 tamper evidence, see EventRecord.h)
        const auto res = eventStore.verifyChain();
        if (res.ok) {
          Serial.printf("[LOCAL STORE] Chain verify OK (%u records checked)\n", static_cast<unsigned>(res.recordsChecked));
        } else {
          Serial.printf("[LOCAL STORE] Chain verify FAILED at slot %u (local id %lu) - possible tampering\n",
                        static_cast<unsigned>(res.breakAtSlot), static_cast<unsigned long>(res.breakAtLocalId));
        }
        break;
      }
      case 'y': {   // self-test LoRaCipher (Phase 4 AES-GCM) against a known-good reference vector
        uint8_t key[16], nonce[12], aad[5], pt[21], expectCt[21], expectTag[16];
        auto fromHex = [](const char* hex, uint8_t* out) {
          for (size_t i = 0; hex[i] && hex[i + 1]; i += 2) {
            unsigned v;
            sscanf(hex + i, "%2hhx", &out[i / 2]);
            (void)v;
          }
        };
        fromHex("000102030405060708090a0b0c0d0e0f", key);
        fromHex("101112131415161718191a1b", nonce);
        fromHex("0102fe0900", aad);
        fromHex("48656c6c6f2c20466f7265737420506174726f6c21", pt);           // "Hello, Forest Patrol!"
        fromHex("8c4b6fc3606396a978af3886b307bb5f4ece1beb17", expectCt);
        fromHex("f08d27cf3229f991dc83126c126c2629", expectTag);

        forest::crypto::PacketAad aadStruct{0x01, 0x02, 0xFE, 0x0009};
        uint8_t wrapped[12 + sizeof(pt) + 16];
        memcpy(wrapped, nonce, 12);
        memcpy(wrapped + 12, expectCt, sizeof(expectCt));
        memcpy(wrapped + 12 + sizeof(expectCt), expectTag, 16);
        uint8_t decrypted[sizeof(pt)];
        size_t decryptedLen = 0;
        const bool refOk = forest::crypto::loRaDecrypt(key, aadStruct, wrapped, sizeof(wrapped), decrypted,
                                                        sizeof(decrypted), decryptedLen) &&
                           decryptedLen == sizeof(pt) && memcmp(decrypted, pt, sizeof(pt)) == 0;
        Serial.printf("[LORA CIPHER] decrypt known-good reference vector: %s\n", refOk ? "PASS" : "FAIL");

        uint8_t encrypted[sizeof(pt) + forest::crypto::kGcmOverheadBytes];
        size_t encryptedLen = 0;
        const bool encOk = forest::crypto::loRaEncrypt(key, aadStruct, pt, sizeof(pt), encrypted,
                                                        sizeof(encrypted), encryptedLen);
        uint8_t roundTrip[sizeof(pt)];
        size_t roundTripLen = 0;
        const bool rtOk = encOk &&
                         forest::crypto::loRaDecrypt(key, aadStruct, encrypted, encryptedLen, roundTrip,
                                                      sizeof(roundTrip), roundTripLen) &&
                         roundTripLen == sizeof(pt) && memcmp(roundTrip, pt, sizeof(pt)) == 0;
        Serial.printf("[LORA CIPHER] random-nonce encrypt/decrypt round-trip: %s\n", rtOk ? "PASS" : "FAIL");

        uint8_t tampered[sizeof(wrapped)];
        memcpy(tampered, wrapped, sizeof(wrapped));
        tampered[12] ^= 0x01U;
        uint8_t tamperOut[sizeof(pt)];
        size_t tamperOutLen = 0;
        const bool tamperRejected = !forest::crypto::loRaDecrypt(key, aadStruct, tampered, sizeof(tampered),
                                                                  tamperOut, sizeof(tamperOut), tamperOutLen);
        Serial.printf("[LORA CIPHER] tampered ciphertext correctly rejected: %s\n", tamperRejected ? "PASS" : "FAIL");
        break;
      }
      case 'e': {   // enroll a fingerprint onto the R307 at an operator-given page id (bench only;
                    // never runs during a live card scan -- see the verifyState guard below).
        if (verifyState != VerifyState::Idle) {
          Serial.println("[ENROLL] refused: a card verification window is in progress");
          break;
        }
        Serial.print("[ENROLL] page id (match kAllowedCards/kKnownCards, e.g. 2 for OFF002), then Enter: ");
        Serial.setTimeout(15000);
        const long pageIdLong = Serial.parseInt();
        if (pageIdLong <= 0 || pageIdLong > 0xFFFF) {
          Serial.println("\n[ENROLL] FAILED (invalid or no page id entered)");
          break;
        }
        const uint16_t pageId = static_cast<uint16_t>(pageIdLong);
        Serial.printf("\n[ENROLL] page=%u -- place finger on the sensor (scan 1 of 2)...\n", static_cast<unsigned>(pageId));
        if (!fingerprint.waitForFinger(15000)) { Serial.println("[ENROLL] FAILED (no finger presented)"); break; }
        if (!fingerprint.captureToBuffer(1)) { Serial.println("[ENROLL] FAILED (capture 1)"); break; }
        Serial.println("[ENROLL] lift finger...");
        fingerprint.waitForFingerLifted(5000);
        Serial.println("[ENROLL] place the SAME finger again (scan 2 of 2)...");
        if (!fingerprint.waitForFinger(15000)) { Serial.println("[ENROLL] FAILED (no finger presented)"); break; }
        if (!fingerprint.captureToBuffer(2)) { Serial.println("[ENROLL] FAILED (capture 2 -- lift and try again)"); break; }
        if (!fingerprint.createModel()) { Serial.println("[ENROLL] FAILED (createModel -- the two scans did not match well enough)"); break; }
        if (!fingerprint.storeModel(pageId)) { Serial.println("[ENROLL] FAILED (store)"); break; }
        Serial.printf("[ENROLL] OK page=%u\n", static_cast<unsigned>(pageId));
        fingerprint.rearm();
        break;
      }
      default:
        Serial.println("[LOCAL STORE] commands: w=write TEST event  l=list  m=mark oldest pending synced  r=reboot  x=erase  t=driver check (RC522/RTC)  y=LoRaCipher self-test  e=enroll fingerprint");
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
  if (verifyState == VerifyState::AwaitingFingerprint) {
    // Never steal loop() time (blocking TX + up to 1500ms ACK wait) or the amber "awaiting
    // fingerprint" LED from an active two-factor window. retryPendingEvent() sends this once
    // the window resolves, same as the deferred RFID card event.
    Serial.println("[ACOUSTIC TX] deferred until fingerprint verification resolves");
    return;
  }
  setStatusLed(0, 0, kLedLevel);  // blue flash: acoustic event (distinct from RFID red/green/amber)

  // Phase 2 extension: prefer the signed, hash-chained acoustic event (same rationale as
  // sendVerificationEvent - it's a strict superset of the unsigned one), falling back to the
  // legacy unsigned payload only when identity/clock aren't ready yet.
  bool signedPathUsed = false;
  TxResult sent = TxResult::Failed;
  char acEventIso[32];
  if (identityReady && softClock.nowIso8601Utc(acEventIso, sizeof acEventIso)) {
    char nodeIdStr[16];
    snprintf(nodeIdStr, sizeof nodeIdStr, "NODE_%02X", static_cast<unsigned>(FOREST_NODE_ID));
    const uint8_t confidenceByte = payload[3];
    const char* classification = ev.classIndex == 2 ? "Gunshot" : "Chainsaw";
    const char* confidenceRepr = forest::crypto::kConfidenceReprTable[confidenceByte];

    char payloadDigest[65];
    forest::crypto::acousticPayloadDigestHex(classification, confidenceRepr, ACOUSTIC_MODEL_VERSION, payloadDigest);
    const uint32_t seq = acousticChain.nextSequence();
    char recordHashHex[65];
    forest::crypto::computeRecordHashHex(nodeIdStr, seq, acEventIso, payloadDigest,
                                         acousticChain.previousHashHex(), recordHashHex);

    uint8_t prevHashRaw[32] = {0}, recHashRaw[32];
    if (acousticChain.previousHashHex()[0]) forest::utils::hexToBytes(acousticChain.previousHashHex(), 32, prevHashRaw);
    forest::utils::hexToBytes(recordHashHex, 32, recHashRaw);

    char canonical[512];
    forest::crypto::buildAcousticSigningBytes(nodeIdStr, seq, acEventIso, FOREST_CHECKPOINT_ID, "",
                                              classification, confidenceRepr, ACOUSTIC_MODEL_VERSION,
                                              acousticChain.previousHashHex(), recordHashHex, canonical, sizeof canonical);
    uint8_t sig[forest::crypto::kMaxSignatureBytes];
    size_t sigLen = 0;
    if (nodeIdentity.signSha256(reinterpret_cast<const uint8_t*>(canonical), strlen(canonical), sig, sigLen)) {
      uint32_t epoch = 0;
      softClock.nowEpoch(epoch);
      std::array<std::uint8_t, forest::constants::kMaxPayloadSize> signedPayload{};
      const size_t len = forest::crypto::encodeSignedAcousticPayload(
          seq, epoch, ev.classIndex, confidenceByte, FOREST_CHECKPOINT_ID, strlen(FOREST_CHECKPOINT_ID),
          "", 0, prevHashRaw, recHashRaw, sig, sigLen, signedPayload.data(), signedPayload.size());
      if (len > 0) {
        acousticChain.commit(recordHashHex);
        sent = transmitPayload(signedPayload.data(), len, "SIGNED ACOUSTIC TX", false);
        signedPathUsed = true;
        Serial.printf("[SIGNED ACOUSTIC] seq=%lu record_hash=%s tx=%s\n", static_cast<unsigned long>(seq),
                      recordHashHex, sent == TxResult::Failed ? "FAILED" : "SENT");
      } else {
        Serial.println("[SIGNED ACOUSTIC] encode FAILED - not sent, sequence not advanced");
      }
    } else {
      Serial.println("[SIGNED ACOUSTIC] sign FAILED - not sent");
    }
  }
  if (!signedPathUsed) {
    sent = transmitPayload(payload.data(), 6, "ACOUSTIC TX", false);
  }
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
  Serial.printf("[PIN] R307S RX=%d TX=%d baud=%u\n", FOREST_FINGER_RX_PIN, FOREST_FINGER_TX_PIN,
                FOREST_FINGER_BAUD);

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

  const bool fingerprintOk = fingerprint.begin();
  Serial.println(fingerprintOk ? "R307S fingerprint: READY" : "R307S fingerprint: NOT FOUND (check UART wiring/power/password)");

  // Node identity (ECDSA P-256, generated once / loaded from NVS). A failure here must never
  // stop the RFID node either - it only disables the 'k' bench-signing command for this boot.
  identityReady = nodeIdentity.begin();
  Serial.println(identityReady ? "[IDENTITY] ECDSA P-256 key ready" : "[IDENTITY] key init FAILED");
  softClock.begin();
  Serial.println(softClock.hasSynced() ? "[CLOCK] loaded last known UTC time from NVS (not yet re-synced this boot)"
                                       : "[CLOCK] no time yet - waiting for a gateway ACK to sync");
  patrolChain.begin();
#if FOREST_ACOUSTIC
  acousticChain.begin();
#endif

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
#if FOREST_VERBOSE_STORE
    printStore("Recovered");
#endif
    Serial.println("[LOCAL STORE] Serial commands: w=write TEST event  l=list  m=mark synced  v=verify chain  k=identity/sign demo  r=reboot  x=erase");
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
  // Background retry does a blocking LoRa TX + up-to-1500ms ACK wait; never let it compete
  // with the time-sensitive fingerprint window for loop() time.
  if (verifyState == VerifyState::Idle) retryPendingEvent();
  pollFingerprint();

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

  const AllowedCard* card = findAllowedCard(cardUid);
  if (card != nullptr) {
    // Known card: arm the fingerprint window instead of lighting green outright --
    // the visit is not verified until the matching finger is presented too.
    verifyState = VerifyState::AwaitingFingerprint;
    verifyDeadlineMs = millis() + kVerifyWindowMs;
    pendingUid = cardUid;
    pendingExpectedPageId = card->fingerprintPageId;
    pendingOfficerLabel = card->officerLabel;
    // A finger left resting on the sensor from a previous attempt (no clean lift-off since)
    // would otherwise be silently ignored by the driver's debounce -- force a fresh capture.
    fingerprint.rearm();
    setStatusLed(kLedLevel, kLedLevel);  // amber: awaiting second factor
    Serial.printf("[CARD] %s VALID -> amber light, awaiting fingerprint (expects page %u)\n",
                  card->officerLabel, card->fingerprintPageId);
  } else {
    setStatusLed(kLedLevel, 0);
    const char* knownLabel = findKnownCardLabel(cardUid);
    if (knownLabel != nullptr) {
      Serial.printf("[CARD] %s known, but NOT assigned to this checkpoint -> red light\n", knownLabel);
    } else {
      Serial.println("[CARD] UNKNOWN card (not registered to any officer) -> red light");
    }
  }

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
  if (verifyState == VerifyState::AwaitingFingerprint) {
    // A valid card just armed the fingerprint window -- the blocking LoRa TX + up-to-1500ms
    // ACK wait would eat into that window. Leave this event PENDING_SYNC; retryPendingEvent()
    // sends it once the window resolves (loop() only calls it while verifyState == Idle).
    Serial.println("[NODE TX] deferred until fingerprint verification resolves");
  } else if (haveRec) {
    finishStoredEvent(stored, transmitPayload(payload.data(), payloadLen, "NODE TX", true));
  } else {
    transmitPayload(payload.data(), payloadLen, "NODE TX", true);
  }

  // Return to the RC522 mapping so it is ready for the next card scan.
  selectRfidSpi();

  if (verifyState == VerifyState::AwaitingFingerprint) {
    // Leave the amber "awaiting fingerprint" LED lit; pollFingerprint() in the next
    // loop() iterations resolves it to green/red (or times out) and takes over the LED.
    delay(100);
  } else {
    delay(1000);  // invalid card: brief red, then back to idle before allowing the next scan
    setStatusLed(0, 0);
  }
}
