#include "src/CANApi/CanApiv03.hpp"
#include "SD.hpp"
#include "SendMessage.hpp"
#include <Adafruit_GPS.h>
#include "SerialDebugMacros.hpp"
#include "SendMessage.hpp"
#include "StatusMsg.hpp"
#include "SensorInputs.hpp"

//pins
#define MCP_SS 10 //was 51
#define SLEEP_INT 33
#define FLAG_INT 22

CANHelper::CanMsgHandler CANHandler(MCP_SS);
extern conf config;

void setup() { //dont forget to change bitrate to 50KBPS
  Serial.begin(9600);
  setupSensorInputs();
  setupSD(); //must be done after sensor inputs because this needs GPS
  setupSending();

  //mcp2515.reset(); //Here to remind myself to add to library

  pinMode(10, OUTPUT); // Default CS pin must be set o/p even if not being used.
  pinMode(SLEEP_INT, INPUT_PULLUP);
  pinMode(FLAG_INT, INPUT_PULLUP);

  setPowerStatus(STAT_GOOD);  // Position 0 is power. Send status that setup is happening.
  updateStatus();

  Serial.println("Setup complete");
}

void loop() {
  Serial.println("Reading...");
  CANHandler.read();

  Serial.println();
  delay(1000);
}

//Just relays all CAN messages over radio
void CANHelper::Messages::processAll(CANHelper::Messages::CANMsg& msg)
{
  sendMessage(msg);

  //if 0xXX1, its a status message. See updateStatus below
  /*if(msg.metadata.is & 1) {

  }*/
}

/*void updateStatus(int pos, uint8_t val) { //wandering if worth adding to library. Then all IDs in format 0xXX1 could be status IDs. Can then log them in status logs
    // Have as a function so we can add functionality like LEDs.
    sysStatus.data[pos] = val;
}*/

void CANHelper::Messages::processMessage(CANHelper::Messages::Telemetry::_SystemStatusMessages& msg) {}
void CANHelper::Messages::processMessage(CANHelper::Messages::Telemetry::_TimeAndFix& msg) {}
void CANHelper::Messages::processMessage(CANHelper::Messages::Telemetry::_SpeedAndAngle& msg) {}
void CANHelper::Messages::processMessage(CANHelper::Messages::Telemetry::_AltitudeAndSatellites& msg) {}
void CANHelper::Messages::processMessage(CANHelper::Messages::Telemetry::_Latitude& msg) {}
void CANHelper::Messages::processMessage(CANHelper::Messages::Telemetry::_Longitude& msg) {}
