#include "StatusMsg.hpp"
#include "SendMessage.hpp"

CANHelper::Messages::Telemetry::_SystemStatusMessages sysStatus; //access in all other compilation units

void updateStatus() {
  sendMessage(sysStatus);
}

void setPowerStatus(uint8_t s) {
  sysStatus.data.Power = s;
}
void setWritingSDStatus(uint8_t s) {
  sysStatus.data.WritingToSd = s;
}
void setGPSObtainedStatus(uint8_t s) {
  sysStatus.data.GpsTimeObtained = s;
}
void setLoadedConfigStatus(uint8_t s) {
  sysStatus.data.LoadedConfig = s;
}
void setMarkerFlagStatus(uint8_t s) {
  sysStatus.data.Flag = s;
}
