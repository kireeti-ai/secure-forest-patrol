#include "Packet.h"

namespace forest::protocol
{

    bool Packet::setPayload(const std::uint8_t *data, std::size_t size)
    {
        if (size > constants::kMaxPayloadSize)
        {
            return false;
        }

        for (std::size_t i = 0; i < size; ++i)
        {
            payload[i] = data[i];
        }

        payloadSize = size;
        return true;
    }



} // namespace forest::protocol
