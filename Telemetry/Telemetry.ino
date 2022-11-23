#include "src/CANApi/CanApiv03.hpp"
#include "SD.hpp"
#include <SD.h>
#include "SendMessage.hpp"
#include <Adafruit_GPS.h>
#include "SerialDebugMacros.hpp"
#include "SendMessage.hpp"
#include "StatusMsg.hpp"
#include "SensorInputs.hpp"

//pins
#define MCP_SS 10 //was 51 or 10
#define SLEEP_INT 33
#define FLAG_INT 22

CANHelper::CanMsgHandler CANHandler(MCP_SS);
extern conf config;
extern File dataFile;

void setup() { //dont forget to change bitrate to 50KBPS
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

uint32_t sd_timer = millis();
uint32_t status_timer = millis();
uint32_t gps_timer = millis();
void loop() {
  Serial.println("LOOP START");

  powerStatus();  // Check power status
  flagStatus();   // Check flag
  CANHandler.read();      // Read incoming CAN message and treat accordingly
  //pollSensor();   // Poll additional sensors

  /* Flush SD file at interval defined in config file */
  if ((millis() - sd_timer) > config.sd_update) {
    sd_timer = millis();
    dataFile.flush();
    DEBUG_PRINTLN("SD Flush");
  }

  /* Update GPS */
  readGPS();
  if((millis() - gps_timer) > config.gps_update) {
    gps_timer = millis();
    updateGPS();
  }

  /* Send system status update at desired interval */
  if ((millis() - status_timer) > config.status_update) {
    status_timer = millis();
    updateStatus();
  }

  //Serial.println("Reading...");
  //CANHandler.read();

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
