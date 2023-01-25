#include "SendMessage.hpp"
#include "HardwareSerial.h" //for Serial class
#include <SD.h>
#include "util/crc16.h"
#include "SerialDebugMacros.hpp"
#include "StatusMsg.hpp"
#include "src/CANApi/CanApiv03.hpp"

#define LOG_TO_SERIAL //Now a copy of SD stream and radio stream will be logged to serial output.

//buffer structure: ID0 ID1 DLC D[1]...D[DLC] CRC0 CRC1
uint8_t byte_buffer[13]; // For CAN message in byte format to be transmitted (includes crc). 13 is the max size = 2+1+dlc+2
extern CANHelper::Messages::Telemetry::_SystemStatusMessages sysStatus; //reference to sysStatus in StatusMsg.hpp

#define XBeeSerial Serial2
extern CANHelper::CanMsgHandler CANHandler;
extern File dataFile;

void setupSending()
{
  //Serial.begin(230400);
  XBeeSerial.begin(115200);
}

void out_byte(uint8_t b) {
    /* Send and log byte. Send to serial if set in config file */

    //Send over radio
    XBeeSerial.write(b);

#ifdef LOG_TO_SERIAL
    Serial.print(b, HEX);
    Serial.print(" ");
#endif
    if(dataFile) {
      dataFile.write(b);
      //dataFile.print(b, HEX);
      //dataFile.print(" ");
    }
    /*if (dataFile) {
        dataFile.print(b, HEX);
        dataFile.print(" ");
        if (sysStatus.data[1] == STAT_BAD) {
            updateStatus(1, STAT_GOOD);
            sendMessage(sysStatus);
        }
    }
    else if (sysStatus.data[1] == STAT_GOOD) {
        updateStatus(1, STAT_BAD);
        sendMessage(sysStatus);
    }*/ //will come back to this
}

//int gencrc(unsigned char dlc) {
void gencrc() {
    uint16_t crc = 0xFFFF, i;
    //for (i = 0; i < dlc+3; i++) {
    for(i = 0; i < byte_buffer[2] + 3; i++) {
        crc = _crc16_update(crc, byte_buffer[i]);
    }
    byte_buffer[byte_buffer[2] + 3] = (crc >> 8) & 0xFF; // Bit shift. print most significant byte first, then least.
    byte_buffer[byte_buffer[2] + 4] = crc & 0xFF;
    //return crc;
}

//Sending Data
void sendMessage(CANHelper::Messages::CANMsg& msg) {
    /* Sends CAN style message to XBee and logs to SD card.
     * By having in one function means we can be sure everything is robust to lack of SD card for example.
     */
    /*Serial.print("RECIEVED: ");
    Serial.println(msg.can_id, HEX);*/
    //Serial.println(msg.metadata.id, HEX);
    //Serial.println(msg.metadata.dlc);

    // Escape character delimter to spot the data
    //out_byte(0x7E); //moved to end of frame
    
    // Split CAN ID into 2 bytes in order to .write()
    uint8_t can_id_b0 = (msg.metadata.id >> 8) & 0xFF;   // Remember, 11 bit CAN ID so 2047 is the max (0x7FF)
    uint8_t can_id_b1 = msg.metadata.id & 0xFF;
    
    //out_byte(can_id_b0);
    //out_byte(can_id_b1);
    //out_byte(msg.metadata.dlc);

    // Add CAN ID to byte_buffer for later use in CRC calculation
    byte_buffer[0] = can_id_b0;
    byte_buffer[1] = can_id_b1;
    byte_buffer[2] = msg.metadata.dlc;

    // Add data to byte buffer
    can_frame& castMsg = (can_frame&)msg;
    for (int i = 0; i < msg.metadata.dlc; i++)  {
        byte_buffer[i+3] = castMsg.data[i];
    }

    //int16_t crc = gencrc(msg.metadata.dlc);
    gencrc(); //regen CRC with new data in byte buffer

    //Send bytes
    for(int i = 0; i < byte_buffer[2] + 5; i++) { //byte_buffer[2] is the dlc
      out_byte(byte_buffer[i]);
    }

    out_byte(0x7E); //End Of Frame marker

    //Add LF characters at end of lines for SD and Serial streams. Dont do this. Using binary now
    //dataFile.println();
#ifdef LOG_TO_SERIAL
    Serial.println();
#endif

    //out_byte((crc >> 8) & 0xFF);    // Bit shift and transmit CRC
    //out_byte(crc & 0xFF);
    
    /*if (config.serialCanMsg == 1) {
        Serial.println("");
    }*///?
    //dataFile.println();
}

void sendMessage(can_frame& msg) {
  sendMessage((CANHelper::Messages::CANMsg&) msg);
}
