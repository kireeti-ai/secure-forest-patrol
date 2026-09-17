#pragma once

#include "EventBus.h"

namespace forest
{
    namespace event { class EventBus; }
    namespace node { class NodeManager; }
    namespace radio { class IRadio; }
    namespace queue { class PacketQueue; }
    namespace services { class ReliableLinkService; class DtnStoreForwardService; }
    namespace protocol { class PacketFactory; }
    namespace hal { class IConsole; }
    namespace utils { class Logger; }

    class App final : public event::IEventListener
    {
    public:
        App(radio::IRadio &radio, node::NodeManager &node, queue::PacketQueue &packetQueue, event::EventBus &eventBus,
            services::ReliableLinkService &reliableLinkService,
            services::DtnStoreForwardService &dtnService,
            utils::Logger &logger,
            protocol::PacketFactory &packetFactory, hal::IConsole &console);
        bool begin();
        void update();
        void onEvent(const event::Event &event) override;

    private:
        void transmitQueued_();
        void processIncoming_();
        void processTestCommands_();
        void processRtcCommand_();
        radio::IRadio &radio_;
        node::NodeManager &node_;
        queue::PacketQueue &packetQueue_;
        event::EventBus &eventBus_;
        services::ReliableLinkService &reliableLinkService_;
        services::DtnStoreForwardService &dtnService_;
        utils::Logger &logger_;
        protocol::PacketFactory &packetFactory_;
        hal::IConsole &console_;
        std::uint8_t testDestinationId_ = 0U;
        std::uint16_t testRemainingCount_ = 0U;
        std::size_t testPayloadSize_ = 0U;
        std::uint8_t testPayload_[constants::kMaxPayloadSize]{};
        bool initialized_ = false;
    };
} // namespace forest
