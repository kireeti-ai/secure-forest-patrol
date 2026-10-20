#include "GatewayService.h"
#include <Arduino.h>
#include <cstring>

namespace forest::gateway {

GatewayService::GatewayService(logging::ILogger& logger,
                               backend::BackendIngestionClient& backendClient,
                               bool debugMode)
    : logger_(logger),
      backendClient_(backendClient),
      debugMode_(debugMode) {}

void GatewayService::handleReceivedPacket(const lora::RawRadioPacket& packet, lora::ILoRaDriver* radioDriver) {
    Serial.println("--------------------------------");
    Serial.println("Packet Received");
    Serial.printf("Length: %u\n", static_cast<unsigned>(packet.length));
    Serial.printf("RSSI: %d\n", packet.rssiDbm);
    Serial.printf("SNR: %.1f\n", static_cast<double>(packet.snrDb));
    Serial.print("Payload HEX: ");
    for (std::size_t index = 0U; index < packet.length; ++index) {
        Serial.printf("%02X%s", packet.bytes[index],
                      (index + 1U == packet.length) ? "" : " ");
    }
    Serial.println();
    Serial.println("--------------------------------");

    if (debugMode_) {
        const logging::RawRxLogRecord rxLog{packet.length, packet.rssiDbm, packet.snrDb, packet.receivedAtMs, packet.bytes, debugMode_};
        logger_.logRawRx(rxLog);
    }

    forest::protocol::Packet parsed{};
    if (!forest::protocol::Parser::parse(packet.bytes, packet.length, parsed)) {
        logger_.logRxError({"ParseFailed", packet.rssiDbm, packet.snrDb, packet.length});
        return;
    }

    if (!forest::protocol::Validator::isValid(parsed)) {
        logger_.logRxError({"ValidationFailed", packet.rssiDbm, packet.snrDb, packet.length});
        return;
    }

    // Process valid Forest Event
    bool isDuplicate = false;
    
    // We expect DATA packets for forest events
    if (parsed.type == forest::protocol::PacketType::Data) {
        if (parsed.destinationId != 0xFEU && parsed.destinationId != 0xFFU) {
            return; // Not for gateway
        }
        
        deviceRegistry_.registerPacket(
            parsed.sourceId,
            "DATA",
            parsed.sequenceNumber,
            packet.rssiDbm,
            packet.snrDb,
            packet.receivedAtMs
        );
        nodeRegistryService_.handleHeartbeat(
            parsed.sourceId,
            parsed.sequenceNumber,
            packet.rssiDbm,
            packet.snrDb,
            packet.receivedAtMs
        );

        isDuplicate = ackHandler_.processDataPacket(
            parsed.sourceId,
            parsed.destinationId,
            parsed.sequenceNumber,
            packet.rssiDbm,
            packet.snrDb,
            packet.receivedAtMs,
            radioDriver
        );

        if (!isDuplicate) {
            backend::ForestEventEnvelope envelope;
            envelope.sourceId = parsed.sourceId;
            envelope.sequenceNumber = parsed.sequenceNumber;
            envelope.rssiDbm = packet.rssiDbm;
            envelope.snrDb = packet.snrDb;
            envelope.gatewayReceivedAtMs = packet.receivedAtMs;

            if (parsed.payloadSize >= 3 &&
                       parsed.payload[0] == 0x52U &&
                       parsed.payload[1] == 0x01U &&
                       parsed.payload[2] <= 10U &&
                       parsed.payloadSize == static_cast<std::size_t>(3U + parsed.payload[2])) {
                envelope.hasRfid = true;
                envelope.rfidUidLength = parsed.payload[2];
                for (std::size_t index = 0U; index < envelope.rfidUidLength; ++index) {
                    envelope.rfidUid[index] = parsed.payload[3U + index];
                }

                Serial.println("================================");
                Serial.println("RFID PACKET RECEIVED");
                Serial.println("================================");
                Serial.println();
                Serial.println("Type : RFID_SCAN");
                Serial.printf("Node : NODE_%02X\n", parsed.sourceId);
                Serial.print("UID  : ");
                for (std::size_t index = 0U; index < envelope.rfidUidLength; ++index) {
                    Serial.printf("%02X%s", envelope.rfidUid[index], (index == envelope.rfidUidLength - 1) ? "" : ":");
                }
                Serial.println();
                Serial.printf("SEQ  : %u\n", parsed.sequenceNumber);
                Serial.println();
                Serial.printf("RSSI : %d dBm\n", packet.rssiDbm);
                Serial.printf("SNR  : %.1f dB\n", static_cast<double>(packet.snrDb));
                Serial.println();
                Serial.println("Packet validation: SUCCESS");
            } else if (parsed.payloadSize == 6 &&
                       parsed.payload[0] == 0x41U &&
                       parsed.payload[1] == 0x01U &&
                       (parsed.payload[2] == 1U || parsed.payload[2] == 2U)) {
                // Acoustic event: [ 'A', v1, class 1=chainsaw 2=gunshot, confidence u8, trigger RMS u16 LE ]
                envelope.hasAcoustic = true;
                envelope.acousticClass = parsed.payload[2];
                envelope.acousticConfidenceU8 = parsed.payload[3];
                envelope.acousticTriggerRms = static_cast<std::uint16_t>(parsed.payload[4] | (parsed.payload[5] << 8));
                Serial.println("================================");
                Serial.println("ACOUSTIC EVENT RECEIVED");
                Serial.println("================================");
                Serial.printf("Node  : NODE_%02X\n", parsed.sourceId);
                Serial.printf("Class : %s\n", envelope.acousticClass == 2U ? "Gunshot" : "Chainsaw");
                Serial.printf("Conf  : %u/255 (%.0f%%)\n", envelope.acousticConfidenceU8,
                              static_cast<double>(envelope.acousticConfidenceU8) * 100.0 / 255.0);
                Serial.printf("RMS   : %u\n", envelope.acousticTriggerRms);
                Serial.printf("SEQ   : %u\n", parsed.sequenceNumber);
                Serial.printf("RSSI  : %d dBm  SNR: %.1f dB\n", packet.rssiDbm, static_cast<double>(packet.snrDb));
            } else if (parsed.payloadSize >= 14 &&
                       parsed.payload[0] == 0x56U &&
                       parsed.payload[1] == 0x01U &&
                       parsed.payload[2] >= 1U && parsed.payload[2] <= 3U &&
                       parsed.payload[3] <= 10U &&
                       parsed.payloadSize == static_cast<std::size_t>(10U + parsed.payload[3])) {
                // Two-factor verification event: ['V', v1, status, uidLen, uid[uidLen],
                // claimedPageId u16 LE, actualPageId u16 LE, score u16 LE].
                envelope.hasVerification = true;
                envelope.verifyStatus = parsed.payload[2];
                envelope.verifyUidLength = parsed.payload[3];
                std::size_t off = 4U;
                for (std::size_t index = 0U; index < envelope.verifyUidLength; ++index) {
                    envelope.verifyUid[index] = parsed.payload[off + index];
                }
                off += envelope.verifyUidLength;
                envelope.verifyClaimedPageId = static_cast<std::uint16_t>(parsed.payload[off] | (parsed.payload[off + 1] << 8));
                off += 2U;
                envelope.verifyActualPageId = static_cast<std::uint16_t>(parsed.payload[off] | (parsed.payload[off + 1] << 8));
                off += 2U;
                envelope.verifyScore = static_cast<std::uint16_t>(parsed.payload[off] | (parsed.payload[off + 1] << 8));

                const char* statusStr = envelope.verifyStatus == 1 ? "MATCH" : envelope.verifyStatus == 2 ? "MISMATCH" : "TIMEOUT";
                Serial.println("================================");
                Serial.println("VERIFICATION EVENT RECEIVED");
                Serial.println("================================");
                Serial.printf("Node   : NODE_%02X\n", parsed.sourceId);
                Serial.printf("Status : %s\n", statusStr);
                Serial.printf("Claimed page : %u  Actual page : %u  Score : %u\n",
                              envelope.verifyClaimedPageId, envelope.verifyActualPageId, envelope.verifyScore);
                Serial.printf("SEQ    : %u\n", parsed.sequenceNumber);
            } else if (parsed.payloadSize >= 15 && parsed.payload[0] == 0x50U && parsed.payload[1] == 0x01U) {
                // Signed patrol event ['P', v1, sequence u32 LE, epoch u32 LE, rfidResult,
                // fingerprintResult, checkpointIdLen, checkpointId[len], officerUidLen,
                // officerUid[len], previousHash[32], recordHash[32], sigLen, sig[sigLen]].
                // Must match node-firmware/lib/ForestCrypto/src/SignedPatrolPayload.h exactly.
                std::size_t off = 2U;
                const std::uint32_t sequence = static_cast<std::uint32_t>(parsed.payload[off]) |
                    (static_cast<std::uint32_t>(parsed.payload[off + 1]) << 8) |
                    (static_cast<std::uint32_t>(parsed.payload[off + 2]) << 16) |
                    (static_cast<std::uint32_t>(parsed.payload[off + 3]) << 24);
                off += 4U;
                const std::uint32_t epoch = static_cast<std::uint32_t>(parsed.payload[off]) |
                    (static_cast<std::uint32_t>(parsed.payload[off + 1]) << 8) |
                    (static_cast<std::uint32_t>(parsed.payload[off + 2]) << 16) |
                    (static_cast<std::uint32_t>(parsed.payload[off + 3]) << 24);
                off += 4U;
                const std::uint8_t rfidResult = parsed.payload[off++];
                const std::uint8_t fpResult = parsed.payload[off++];
                const std::uint8_t cpLen = parsed.payload[off++];
                const bool cpOk = cpLen <= backend::ForestEventEnvelope::kMaxCheckpointIdLen &&
                                  parsed.payloadSize > off + cpLen;
                if (cpOk) {
                    envelope.hasPatrol = true;
                    envelope.patrolSequence = sequence;
                    envelope.patrolEpoch = epoch;
                    envelope.patrolRfidResult = rfidResult;
                    envelope.patrolFingerprintResult = fpResult;
                    std::memcpy(envelope.patrolCheckpointId, &parsed.payload[off], cpLen);
                    envelope.patrolCheckpointId[cpLen] = '\0';
                    off += cpLen;
                    const std::uint8_t uidLen = parsed.payload[off++];
                    if (uidLen <= backend::ForestEventEnvelope::kMaxUidLength &&
                        parsed.payloadSize >= off + uidLen + backend::ForestEventEnvelope::kPatrolHashBytes * 2U + 1U) {
                        envelope.patrolOfficerUidLength = uidLen;
                        std::memcpy(envelope.patrolOfficerUid, &parsed.payload[off], uidLen);
                        off += uidLen;
                        std::memcpy(envelope.patrolPreviousHash, &parsed.payload[off], backend::ForestEventEnvelope::kPatrolHashBytes);
                        off += backend::ForestEventEnvelope::kPatrolHashBytes;
                        std::memcpy(envelope.patrolRecordHash, &parsed.payload[off], backend::ForestEventEnvelope::kPatrolHashBytes);
                        off += backend::ForestEventEnvelope::kPatrolHashBytes;
                        const std::uint8_t sigLen = parsed.payload[off++];
                        if (sigLen <= backend::ForestEventEnvelope::kMaxSignatureBytes && parsed.payloadSize >= off + sigLen) {
                            envelope.patrolSignatureLength = sigLen;
                            std::memcpy(envelope.patrolSignature, &parsed.payload[off], sigLen);
                            Serial.println("================================");
                            Serial.println("SIGNED PATROL EVENT RECEIVED");
                            Serial.println("================================");
                            Serial.printf("Node  : NODE_%02X\n", parsed.sourceId);
                            Serial.printf("Seq   : %lu  Checkpoint: %s\n", static_cast<unsigned long>(sequence), envelope.patrolCheckpointId);
                        } else {
                            envelope.hasPatrol = false;
                            Serial.println("[SIGNED PATROL] signature length out of range - dropped");
                        }
                    } else {
                        envelope.hasPatrol = false;
                        Serial.println("[SIGNED PATROL] officer UID length out of range - dropped");
                    }
                } else {
                    Serial.println("[SIGNED PATROL] checkpoint_id length out of range - dropped");
                }
            } else if (parsed.payloadSize == 9) {
                envelope.hasRtc = true;
                envelope.rtcYear = 2000 + parsed.payload[0];
                envelope.rtcMonth = parsed.payload[1];
                envelope.rtcDay = parsed.payload[2];
                envelope.rtcHour = parsed.payload[3];
                envelope.rtcMinute = parsed.payload[4];
                envelope.rtcSecond = parsed.payload[5];
                int16_t temp = (static_cast<int16_t>(parsed.payload[6]) << 8) | parsed.payload[7];
                envelope.temperatureC = static_cast<float>(temp) / 100.0f;

                Serial.printf("[FOREST EVENT RX] source: 0x%02X | sequence: %u | RTC: %04u-%02u-%02u %02u:%02u:%02u | Temp: %.2fC\n",
                              parsed.sourceId, parsed.sequenceNumber,
                              envelope.rtcYear, envelope.rtcMonth, envelope.rtcDay,
                              envelope.rtcHour, envelope.rtcMinute, envelope.rtcSecond,
                              envelope.temperatureC);
            } else {
                Serial.printf("[SENSOR DATA RX] source: 0x%02X | sequence: %u | UNKNOWN PAYLOAD (%u bytes)\n",
                              parsed.sourceId, parsed.sequenceNumber,
                              static_cast<unsigned>(parsed.payloadSize));
            }

            backendClient_.enqueue(envelope);
        }

        Serial.println("--------------------------------");
    }
}

void GatewayService::beginBackend() {
    backendClient_.begin();
}

void GatewayService::tick(std::uint32_t currentMs, lora::ILoRaDriver* radioDriver) {
    // Network work runs in BackendIngestionClient's own task; nothing here may block.
    (void)currentMs;
    if (radioDriver != nullptr) backendClient_.dispatchMessages(*radioDriver);
}

}  // namespace forest::gateway
