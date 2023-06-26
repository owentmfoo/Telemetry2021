#ifndef SENDMESSAGE_HEADER
#define SENDMESSAGE_HEADER

#include "src/CANApi/CanApiv04.hpp"

struct GPSData {
  CANHelper::Messages::Telemetry::_SpeedAndAngle speedAngle;
  CANHelper::Messages::Telemetry::_Latitude latitude;
  CANHelper::Messages::Telemetry::_Longitude longitude;
  CANHelper::Messages::Telemetry::_AltitudeAndSatellites altitudeSatellites;
};

void setupSending();
void sendMessage(CANHelper::Messages::CANMsg& msg);
void sendMessage(can_frame& msg);

#endif