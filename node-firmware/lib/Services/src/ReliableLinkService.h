#pragma once

#include "Packet.h"

namespace forest::event { class EventBus; }
namespace forest::reliable { class AckManager; }

namespace forest::services
{
    class ReliableLinkService
    {
    public:
        explicit ReliableLinkService(reliable::AckManager &ackManager);
        bool begin(event::EventBus &eventBus);
        void update();
        bool processReceivedData(const protocol::Packet &packet);
        void onTransmissionFailed(const protocol::Packet &packet);
        bool readyForTestPacket() const;

    private:
        reliable::AckManager &ackManager_;
    };
} // namespace forest::services
