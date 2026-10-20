#include "GatewayAckHandler.h"
#include <Arduino.h>
#include <cstdio>
#include <array>
#include <ctime>

namespace forest::gateway {

std::uint16_t GatewayAckHandler::computeCrc16_(const std::uint8_t* data, std::size_t length) {
    std::uint16_t crc = 0xFFFFU;
    for (std::size_t i = 0; i < length; ++i) {
        crc ^= static_cast<std::uint16_t>(data[i]) << 8U;
        for (std::uint8_t bit = 0; bit < 8; ++bit) {
            if ((crc & 0x8000U) != 0) {
                crc = static_cast<std::uint16_t>((crc << 1U) ^ 0x1021U);
            } else {
                crc = static_cast<std::uint16_t>(crc << 1U);
            }
        }
    }
    return crc;
}

bool GatewayAckHandler::sendDataAckPacket_(std::uint8_t targetNodeId,
                                           std::uint16_t sequenceNumber,
                                           lora::ILoRaDriver* radioDriver) {
    if (radioDriver == nullptr) {
        return false;
    }

    // Only claim a real time sync if NTP has actually run: a never-synced ESP32 system clock
    // reads near epoch 0, which would otherwise be mistaken by the node for "1970" and corrupt
    // its SoftClock. 1700000000 ~= 2023-11-14; any real sync will be well past that.
    const time_t rawTime = time(nullptr);
    const bool haveRealTime = rawTime > 1700000000;
    const std::size_t payloadSize = haveRealTime ? 6 : 2;
    const std::size_t frameSize = 8 + payloadSize + 2;   // header(8) + payload + crc(2)

    // 8 (header) + payload (2 or 6) + 2 (crc) = up to 16 bytes. Was 14 - a 2-byte stack overflow
    // on every extended (time-carrying) ACK, since frameSize could be 16.
    std::array<std::uint8_t, 16> ackBuf{};
    ackBuf[0] = 0xA5; // preamble
    ackBuf[1] = 0x04; // version
    ackBuf[2] = 0x03; // PacketType::Acknowledgement (3)
    ackBuf[3] = 0xFE; // Gateway ID (Source)
    ackBuf[4] = targetNodeId; // Destination ID
    ackBuf[5] = static_cast<std::uint8_t>(ackSeq_ & 0xFFU);
    ackBuf[6] = static_cast<std::uint8_t>((ackSeq_ >> 8U) & 0xFFU);
    ackSeq_++;
    ackBuf[7] = static_cast<std::uint8_t>(payloadSize);

    ackBuf[8] = static_cast<std::uint8_t>(sequenceNumber & 0xFFU);
    ackBuf[9] = static_cast<std::uint8_t>((sequenceNumber >> 8U) & 0xFFU);
    if (haveRealTime) {
        const std::uint32_t utc = static_cast<std::uint32_t>(rawTime);
        ackBuf[10] = static_cast<std::uint8_t>(utc & 0xFFU);
        ackBuf[11] = static_cast<std::uint8_t>((utc >> 8U) & 0xFFU);
        ackBuf[12] = static_cast<std::uint8_t>((utc >> 16U) & 0xFFU);
        ackBuf[13] = static_cast<std::uint8_t>((utc >> 24U) & 0xFFU);
    }

    const std::uint16_t crc = computeCrc16_(ackBuf.data(), 8 + payloadSize);
    ackBuf[8 + payloadSize] = static_cast<std::uint8_t>(crc & 0xFFU);
    ackBuf[8 + payloadSize + 1] = static_cast<std::uint8_t>((crc >> 8U) & 0xFFU);

    const bool sent = radioDriver->send(ackBuf.data(), frameSize);
    if (!sent) stats_.ackTxFailures++;
    return sent;
}

bool GatewayAckHandler::processDataPacket(std::uint8_t targetNodeId,
                                          std::uint8_t destinationId,
                                          std::uint16_t sequenceNumber,
                                          int rssiDbm,
                                          float snrDb,
                                          std::uint32_t timestampMs,
                                          lora::ILoRaDriver* radioDriver) {
    stats_.rssi = rssiDbm;
    stats_.snr = snrDb;
    stats_.lastSeenMs = timestampMs;

    const DuplicateKey key{targetNodeId, 1U /* PacketType::Data */, sequenceNumber};
    bool duplicate = false;
    for (auto& entry : dataDuplicates_) {
        if (!entry.active) continue;
        if (timestampMs - entry.timestampMs >= duplicateExpiryMs_) { entry.active = false; continue; }
        if (entry.key.sourceId == key.sourceId && entry.key.type == key.type && entry.key.sequenceNumber == key.sequenceNumber) duplicate = true;
    }
    if (duplicate) {
        stats_.duplicatePackets++;
        Serial.printf("--------------------------------\n");
        Serial.printf("Duplicate Data Packet (Seq #%u)\n", sequenceNumber);
        Serial.printf("Node: 0x%02X | RSSI: %d dBm | SNR: %.1f dB\n", targetNodeId, rssiDbm, static_cast<double>(snrDb));
        Serial.printf("Data ACK resent\n");
        Serial.printf("--------------------------------\n");
        Serial.flush();

        if (destinationId == 0xFEU || destinationId == 0xFFU) {
            if (sendDataAckPacket_(targetNodeId, sequenceNumber, radioDriver)) stats_.ackSent++;
        }
        return true;
    }

    auto& dataEntry = dataDuplicates_[nextDataDuplicate_];
    dataEntry.key = key;
    dataEntry.timestampMs = timestampMs;
    dataEntry.active = true;
    nextDataDuplicate_ = (nextDataDuplicate_ + 1U) % dataDuplicates_.size();
    stats_.packetsReceived++;

    Serial.printf("--------------------------------\n");
    Serial.printf("Data Packet received\n");
    Serial.printf("Node: 0x%02X | Seq: %u | RSSI: %d dBm | SNR: %.1f dB\n",
                  targetNodeId, sequenceNumber, rssiDbm, static_cast<double>(snrDb));

    if (destinationId == 0xFEU || destinationId == 0xFFU) {
        if (sendDataAckPacket_(targetNodeId, sequenceNumber, radioDriver)) stats_.ackSent++;
        Serial.printf("Data ACK sent\n");
    }
    Serial.printf("--------------------------------\n");
    Serial.flush();

    return false;
}

}  // namespace forest::gateway
