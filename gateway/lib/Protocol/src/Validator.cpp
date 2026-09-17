#include "Validator.h"

namespace jalari::protocol
{

    bool Validator::isValid(const Packet &packet)
    {
        if (packet.sourceId == 0U || packet.payloadSize > packet.payload.size())
        {
            return false;
        }

        switch (packet.type)
        {
        case PacketType::Data:
            return true;
        case PacketType::Acknowledgement:
            return packet.payloadSize == constants::kAcknowledgementPayloadSize;
        case PacketType::Unknown:
        default:
            return false;
        }
    }

} // namespace jalari::protocol
