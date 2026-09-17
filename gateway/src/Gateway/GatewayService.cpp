#include "GatewayService.h"
#include <Arduino.h>

namespace jalri::gateway {

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
    Serial.println("--------------------------------");

    if (debugMode_) {
        const logging::RawRxLogRecord rxLog{packet.length, packet.rssiDbm, packet.snrDb, packet.receivedAtMs, packet.bytes, debugMode_};
        logger_.logRawRx(rxLog);
    }

    jalari::protocol::Packet parsed{};
    if (!jalari::protocol::Parser::parse(packet.bytes, packet.length, parsed)) {
        logger_.logRxError({"ParseFailed", packet.rssiDbm, packet.snrDb, packet.length});
        return;
    }

    if (!jalari::protocol::Validator::isValid(parsed)) {
        logger_.logRxError({"ValidationFailed", packet.rssiDbm, packet.snrDb, packet.length});
        return;
    }

    // Process valid Forest Event
    bool isDuplicate = false;
    
    // We expect DATA packets for forest events
    if (parsed.type == jalari::protocol::PacketType::Data) {
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

            if (parsed.payloadSize == 9) {
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
                Serial.printf("[FOREST EVENT RX] source: 0x%02X | sequence: %u | NO RTC\n", parsed.sourceId, parsed.sequenceNumber);
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
    backendClient_.tick(currentMs);
    if (radioDriver != nullptr) backendClient_.dispatchMessages(*radioDriver);
}

}  // namespace jalri::gateway
