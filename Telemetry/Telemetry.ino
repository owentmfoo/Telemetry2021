#include "src/CANApi/CanApiv02.hpp"
#include <SD.h>
#include <Adafruit_GPS.h>

//pins
#define MCP_SS 10 //was 51
#define SD_SS 12 //was 53
#define SLEEP_INT 33
#define FLAG_INT 22

#define XBeeSerial Serial2
#define GPSSerial Serial1
Adafruit_GPS GPS(&GPSSerial);
CANHelper::CanMsgHandler handler(MCP_SS);

#ifdef DEBUG
 #define DEBUG_PRINT(x)  Serial.print (x)
 #define DEBUG_PRINTLN(x)  Serial.println (x)
 #define DEBUG_WRITE(x)  Serial.write (x)
 #define DEBUG_PRINTHEX(x) Serial.print (x, HEX)
#else
 #define DEBUG_PRINT(x)
 #define DEBUG_PRINTLN(x)
 #define DEBUG_WRITE(x)
 #define DEBUG_PRINTHEX(x)
#endif

void setup() {
  Serial.begin(9600);
  XBeeSerial.begin(115200);
  GPS.begin(9600);

  GPS.sendCommand(PMTK_SET_NMEA_OUTPUT_RMCGGA);
  GPS.sendCommand(PMTK_SET_NMEA_UPDATE_1HZ);

  //mcp2515.reset(); //Here to remind myself to add to library

  pinMode(10, OUTPUT); // Default CS pin must be set o/p even if not being used.
  pinMode(SLEEP_INT, INPUT_PULLUP);
  pinMode(FLAG_INT, INPUT_PULLUP);

  

  Serial.println("Setup complete");
}

void loop() {
  Serial.println("Reading...");
  handler.read();

  Serial.println();
  delay(1000);
}

void CANHelper::Messages::processAll(CANHelper::Messages::CANMsg& msg)
{
  Serial.print("processAll function: ");
  Serial.print(msg.metadata.id, HEX);
  Serial.print(" ");
  Serial.println(msg.metadata.dlc, DEC);
}

void CANHelper::Messages::processMessage(CANHelper::Messages::Telemetry::_SystemStatusMessages& msg) {}
