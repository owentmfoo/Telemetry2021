#include <stdint.h>
#ifndef STATUSMSG_HEADER
#define STATUSMSG_HEADER

//status CAN message definitions
#define STAT_GOOD       0xFF //power on, writing to SD, GPS time obtained, loaded config
#define STAT_BAD        0xAA //config not loaded, not writing to SD
#define STAT_DEFAULTS   0xBB //not writing to SD
#define STAT_UNKNOWN    0x00

//void setupStatusMsg();
void updateStatus(); //run this periodically (on a timer)

void setPowerStatus(uint8_t);
void setWritingSDStatus(uint8_t);
void setGPSObtainedStatus(uint8_t);
void setLoadedConfigStatus(uint8_t);
void setMarkerFlagStatus(uint8_t);

#endif
