#pragma once

#include "Packet.h"

namespace forest::protocol
{

    class Validator
    {
    public:
        static bool isValid(const Packet &packet);
    };

} // namespace forest::protocol
