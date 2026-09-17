#include "App.h"
#include <Arduino.h>

#include "IRadio.h"
#include "Logger.h"
#include "NodeManager.h"
#include "PacketQueue.h"
#include "Parser.h"
#include "ReliableLinkService.h"
#include "Serializer.h"
#include "Validator.h"
#include "Version.h"
#include "DtnStoreForwardService.h"
#include "PacketFactory.h"

namespace forest
{
    App::App(radio::IRadio &radio, node::NodeManager &node, queue::PacketQueue &packetQueue, event::EventBus &eventBus,
             services::ReliableLinkService &reliableLinkService,
             services::DtnStoreForwardService &dtnService,
             utils::Logger &logger,
             protocol::PacketFactory &packetFactory, hal::IConsole &console)
        : radio_(radio), node_(node), packetQueue_(packetQueue), eventBus_(eventBus),
          reliableLinkService_(reliableLinkService),
          dtnService_(dtnService), logger_(logger),
          packetFactory_(packetFactory), console_(console) {}

    bool App::begin()
    {
        logger_.begin();
        LOG_INFO(logger_, "================================");
        LOG_INFO(logger_, version::kFirmwareName);
        LOG_INFO(logger_, version::kFirmwareVersion);
        LOG_INFO(logger_, "================================");
        if (!eventBus_.subscribe(*this) || !reliableLinkService_.begin(eventBus_))
        {
            LOG_ERROR(logger_, "Event bus subscription failed");
            return false;
        }
        if (!radio_.begin())
        {
            node_.setStatus(node::NodeStatus::Fault);
            eventBus_.publish({event::Type::RadioError});
            return false;
        }
        node_.setStatus(node::NodeStatus::Ready);
        initialized_ = true;
        eventBus_.publish({event::Type::RadioReady});
        return true;
    }

    void App::update()
    {
        if (!initialized_) return;
        processIncoming_();
        processRtcCommand_();
        processTestCommands_();
        reliableLinkService_.update();
        dtnService_.update();

        protocol::Packet dtnPacket;
        if (dtnService_.dequeue(dtnPacket)) {
            packetQueue_.enqueue(dtnPacket);
        }

        transmitQueued_();
    }

    void App::transmitQueued_()
    {
        const protocol::Packet *packet = packetQueue_.peek();
        if (packet == nullptr) return;

        std::array<std::uint8_t, constants::kMaxPacketSize> buffer{};
        std::size_t bufferSize = 0;

        bool serialized = protocol::Validator::isValid(*packet) &&
                          protocol::Serializer::serialize(*packet, buffer, bufferSize);
        bool success = serialized && radio_.send(buffer.data(), bufferSize);

        if (!success)
        {
            LOG_WARN(logger_, "Packet transmission failed");
            protocol::Packet failedPacket;
            (void)packetQueue_.dequeue(failedPacket);
            reliableLinkService_.onTransmissionFailed(failedPacket);
            return;
        }

        protocol::Packet sentPacket;
        (void)packetQueue_.dequeue(sentPacket);
        eventBus_.publish({event::Type::PacketSent, sentPacket});
    }

    void App::processIncoming_()
    {
        radio::ReceivedFrame frame;
        if (!radio_.receive(frame)) return;

        protocol::Packet packet;
        if (!protocol::Parser::parse(frame.bytes.data(), frame.length, packet) || !protocol::Validator::isValid(packet))
        {
            LOG_WARN(logger_, "Received invalid packet");
            return;
        }

        if (packet.sourceId == node_.id())
        {
            return; // Ignore self-echo from radio
        }

        if (packet.type == protocol::PacketType::Data)
        {
            if (!reliableLinkService_.processReceivedData(packet)) return;
        }
        eventBus_.publish({event::Type::PacketReceived, packet, frame.rssi, frame.snr});
    }

    void App::processTestCommands_()
    {
    }

    void App::processRtcCommand_()
    {
    }

    void App::onEvent(const event::Event &event)
    {
        switch (event.type)
        {
        case event::Type::PacketSent:
        case event::Type::PacketReceived:
        {
            char msg[192];
            const char *direction = event.type == event::Type::PacketSent ? "TX" : "RX";
            snprintf(msg, sizeof(msg), "[RF %s] type=%u source=0x%02X destination=0x%02X sequence=%u payloadSize=%u rssi=%d snr=%.2f",
                     direction, static_cast<unsigned>(event.packet.type), event.packet.sourceId,
                     event.packet.destinationId, event.packet.sequenceNumber,
                     static_cast<unsigned>(event.packet.payloadSize),
                     event.rssi, static_cast<double>(event.snr));
            LOG_INFO(logger_, msg);
            break;
        }
        case event::Type::TransmissionFailed:
            LOG_ERROR(logger_, "TX_FAILED");
            break;
        case event::Type::RadioReady: LOG_INFO(logger_, "LoRa ready"); break;
        case event::Type::RadioError: LOG_ERROR(logger_, "LoRa initialization failed"); break;
        default: break;
        }
    }
} // namespace forest
