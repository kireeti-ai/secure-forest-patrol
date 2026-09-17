#include "FirmwareComposition.h"
#include "BuildConfig.h"

namespace forest {

FirmwareComposition::FirmwareComposition()
    : logger_(),
      loraDriver_(),
      backendClient_({BackendBuildConfig::wifiSsid,
                      BackendBuildConfig::wifiPassword,
                      BackendBuildConfig::baseUrl,
                      BackendBuildConfig::ingestionKey,
                      BackendBuildConfig::gatewayId,
                      BackendBuildConfig::mqttBrokerHost,
                      BackendBuildConfig::mqttBrokerPort,
                      BackendBuildConfig::mqttTls,
                      BackendBuildConfig::mqttUsername,
                      BackendBuildConfig::mqttPassword}),
      gatewayService_(logger_, backendClient_),
      app_(loraDriver_, gatewayService_, logger_) {
    backendClient_.setLogger(&logger_);
}

App& FirmwareComposition::app() {
    return app_;
}

}  // namespace forest
