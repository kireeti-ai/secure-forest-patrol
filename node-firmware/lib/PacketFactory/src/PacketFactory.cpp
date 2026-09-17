#include "PacketFactory.h"
#include "NodeManager.h"
#include "Version.h"
#include <cstdio>

namespace jalari::protocol
{
    PacketFactory::PacketFactory(const node::NodeManager &node, const config::NetworkConfig &networkConfig)
        : node_(node), networkConfig_(networkConfig) {}

    bool PacketFactory::createData(std::uint8_t destinationId, const std::uint8_t *payload,
                                   std::size_t payloadSize, Packet &outPacket)
    {
        if (payload == nullptr && payloadSize != 0U) return false;
        initializePacket_(PacketType::Data, destinationId, outPacket);
        return outPacket.setPayload(payload, payloadSize);
    }

    bool PacketFactory::createAcknowledgement(const Packet &receivedPacket, Packet &outPacket)
    {
        const std::uint8_t payload[] = {
            static_cast<std::uint8_t>(receivedPacket.sequenceNumber & 0xFFU),
            static_cast<std::uint8_t>((receivedPacket.sequenceNumber >> 8U) & 0xFFU),
        };
        // ACK goes to the sender
        initializePacket_(PacketType::Acknowledgement, receivedPacket.sourceId, outPacket);
        return outPacket.setPayload(payload, sizeof(payload));
    }

    void PacketFactory::initializePacket_(PacketType type, std::uint8_t destinationId, Packet &outPacket)
    {
        outPacket = {};
        outPacket.type = type;
        outPacket.sourceId = node_.id();
        outPacket.destinationId = destinationId;
        outPacket.sequenceNumber = nextSequenceNumber_++;
    }
} // namespace jalari::protocol
