#pragma once

#include <cstddef>
#include <cstdint>

#include "Packet.h"

namespace forest::protocol
{

    class Parser
    {
    public:
        static bool parse(const std::uint8_t *data, std::size_t size, Packet &outPacket);
    };

} // namespace forest::protocol
