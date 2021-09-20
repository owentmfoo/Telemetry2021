#include <SoftwareSerial.h>
#include <SPI.h>
#include <SD.h>
#include <Adafruit_GPS.h>
#include <ArduinoJson.h>
#include <mcp2515.h>
#include <util/crc16.h>

#define MCP_SS 10
#define SD_SS 53
#define SLEEP_INT 20
#define FLAG_INT 21
#define GPSSerial Serial1
#define XBeeSL Serial2

#define GPSECHO  false
#define DEBUG false

#define STATUS_OK 0xFF
#define STATUS_NOTOK 0x0A
#define STATUS_UNKNOWN 0x00

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



// Set to false to display time in 12 hour format, or true to use 24 hour:
//#define TIME_24_HOUR  true


/* USEFUL DOCUMENTATION *//*
    > Toggle debug: https://forum.arduino.cc/index.php?topic=46900.0
    > SPI SS usage: http://www.learningaboutelectronics.com/Articles/Multiple-SPI-devices-to-an-arduino-microcontroller.php
    > MCP2515 setup: https://circuitdigest.com/microcontroller-projects/arduino-can-tutorial-interfacing-mcp2515-can-bus-module-with-arduino
    > String/char pointers?: https://www.arduino.cc/reference/en/language/variables/data-types/string/
    > Semi-functional SD logging: https://forum.arduino.cc/index.php?topic=228346.15
    > AVR CRC: http://www.nongnu.org/avr-libc/user-manual/group__util__crc.html#ga37b2f691ebbd917e36e40b096f78d996
*/

// CAN transceiver using pin MCP_SS
MCP2515 mcp2515(MCP_SS);

Adafruit_GPS GPS(&GPSSerial); // GPS connected to GPS_SL serial port

struct can_frame canMsg;    // Where the received CAN message will be stored
struct can_frame canMsgSys; // System generated CAN frames - no need for the different frames, just helps keeping track of data
struct can_frame canMsgStatus; //Reserved for telem system status {power, SD fail, GPS, config, flag, spare1, spare2, spare3}

uint8_t my_bytes[sizeof(float)];    // For conversion of floats to bytes
uint8_t byte_buffer[11];            // For CAN message in byte format to be transmitted without crc. 11 is the max size = 2+1+dlc

//File configFile; /// File containing system settings. If this doesn't exists, make our own?
const char *conf_filename = "config.txt";
//char log_filename[16] = "dataYYMMDD00.txt"; // Filename gets changed in log_start_up
char log_filename[12] = "YYMMDD00.txt";     // Filename is 12 characters long
File dataFile; // Where we log data

// Structure for our configuration info
struct conf {
    unsigned int gps_update;
    unsigned int sd_update;
    long time_fix;
    const char* speedtype;
    int mode;
    unsigned int mppt_update;
    unsigned int status_update;
    double value0; 
    double value1;
};

conf config; //...and the info lives in config

bool car_on; // = !safestate

/*  SOFT FILTER CONFIG OPTIONS
uint32_t canIDs[10];  // Where the CAN IDs are stored (static?)
uint8_t passRate[10]; // Respective pass through rate ie 2 corresponds to 1 for every 2 received
uint8_t countID[10];  // Counter for the above.
/// only set for 10 for now... will get bigger as we append during config
*/

uint32_t timer = millis();
uint32_t sd_timer = millis();
uint32_t mppt_timer = millis();
uint32_t flag_timer = millis();
uint32_t status_timer = millis();


void setup() {
    /* Start the serial ports */
    Serial.begin(115200);
    XBeeSL.begin(115200);
    GPS.begin(9600);
    GPS.sendCommand(PMTK_SET_NMEA_OUTPUT_RMCGGA);
    GPS.sendCommand(PMTK_SET_NMEA_UPDATE_1HZ);


    canMsgStatus.can_id  = 0x111;
    canMsgStatus.can_dlc = 8;
    // Clear buffer
    for (int i = 0; i<sizeof(canMsgStatus.data); i++)  {
        canMsgStatus.data[i] = STATUS_UNKNOWN;
    }

    sendStatus(0, STATUS_OK); // Position 0 is power. Send status that telem power is on (0xFF)

    // make sure that the default chip select pin is set to
    // output, even if you don't use it:
    pinMode(10, OUTPUT);
    
    /* Start the CAN transceivers */
    mcp2515.reset();
    mcp2515.setBitrate(CAN_125KBPS,MCP_8MHZ);
    mcp2515.setNormalMode();

    DEBUG_PRINTLN("Setting up");
    DEBUG_PRINT("Initializing SD card...");



    /* Check current date and time from GPS */ // - this could do with a whole load of squishing
    DEBUG_PRINT("Checking GPS...");
    timer = millis();
    while (1) {
        char c = GPS.read();
        //if (c) DEBUG_PRINT(c);
        if (GPS.newNMEAreceived()) {
            //DEBUG_PRINT(GPS.lastNMEA());
            if (GPS.parse(GPS.lastNMEA())) {
                if (!(GPS.year == 0) && !(GPS.year == 80)) { // Before we think life is good, make sure we've actually go the date right - sometimes will read as 0 even when we have time or get it wrong and send 80
                    DEBUG_PRINTLN(">>> Time acquired <<<");
                    sendStatus(2, STATUS_OK);    // GPS time acquired
                    print_datetimefix();
                    break;
                }
                else {
                    //DEBUG_PRINTLN("Time not yet acquired:");
                    //print_datetimefix();
                    sendStatus(2, STATUS_NOTOK);  //GPS time not aquired
                }
            }
            else {
                DEBUG_PRINTLN("parsing failed");
            }
        }
        if (millis() - timer > config.time_fix) {
            DEBUG_PRINTLN("timeout for time acquisition exceeded.");
            break;
        }
    }
    
    /* Start the SD card */
    if (!SD.begin(SD_SS)) {
        DEBUG_PRINTLN("SD card failed, or not present");
        sendStatus(1, STATUS_NOTOK);    // SD card failed
        // Need to move on
        /// Perhaps try again later?
        /// Set a status LED on dashboard so we know what's happened?
        // Use some defaults
        set_defaults(config);
    }
    else if (SD.begin(SD_SS)){
        DEBUG_PRINTLN("SD card initialised"); //do not send writing to SD card status untill actually writing to it in log_start_up
        // Load mode and pop it in config
        load_config(conf_filename, config); 
        log_start_up(log_filename); // Create new file with. log_filename will be modified accordingly. File is dataFile
    }
    
    //attachInterrupt(digitalPinToInterrupt(SLEEP_INT), shut_down, FALLING); // Do this now so we don't try and close a file which doesn't exist
    attachInterrupt(digitalPinToInterrupt(FLAG_INT), flag_status, FALLING);
    pinMode(SLEEP_INT, INPUT_PULLUP);
    pinMode(FLAG_INT, INPUT_PULLUP);
  
    /*DEBUG_PRINTLN("------- CAN Read ----------");
    DEBUG_PRINTLN("ID  DLC   DATA");
    DEBUG_PRINTLN("Using XBeeSL.write() ie. sending *BYTES* as opposed to ASCII");*/
}

void loop() {
    /* If SLEEP_INT pin is pulled low, we tidy things up */
    if (!digitalRead(SLEEP_INT)) {
        shut_down();
        // We return here if SLEEP_INT goes high; we'll exit the loop
        DEBUG_PRINTLN("We're back");
    }
    if (!digitalRead(FLAG_INT)) {
        flag_status();
    }
    /* Read incoming CAN message and treat accordingly */
    readCAN();

    /* Update GPS */
    doGPS();
    
    /* Poll additional sensors */
    pollSensor();

    /* Flush SD file at interval defined in config file */
    if ((millis() - sd_timer) > config.sd_update) {
        sd_timer = millis();
        dataFile.flush();
        DEBUG_PRINTLN("<<<<<<<< FLUSH >>>>>>>>");
    }
    /* send update*/
    if ((millis() - status_timer) > config.status_update) {
        status_timer = millis();
        sendStatus(0,STATUS_OK);
        DEBUG_PRINTLN("SEND STATUS");
    }
    /* send empty can to MPPT to request data */
    if (millis() - mppt_timer > config.mppt_update) {
        mppt_timer = millis();
        pollMPPT();
        DEBUG_PRINTLN("POLL MPPT");
    }
}

void readCAN () {
    /* This is using the poll read method.
     * Interrupt method is available: https://github.com/autowp/arduino-mcp2515#receive-data
     * However, on the UNO, available interrupt pins are 2 and 3 which are being used by XBeeSL
     * 
     * It seems the MCP2515 stores the previous CAN messages in onboard buffers until the information is read. */
    if (mcp2515.readMessage(&canMsg) == MCP2515::ERROR_OK) {
        sendMessage(canMsg);
        /*
        if (softFilter(canMsg.can_id)) { /// | !config.pass_all
            doCAN(canMsg);
        }
        */
    }
}

void sendStatus(int pos, uint8_t val) { // Could preserve a separate system status CAN message which gets sent periodically/upon change.
    // Update desired value
    canMsgStatus.data[pos] = val;
    if (!(GPS.year == 0) && !(GPS.year == 80)) { // Before we think life is good, make sure we've actually go the date right - sometimes will read as 0 even when we have time or get it wrong and send 80
    canMsgStatus.data[2] = STATUS_OK;// GPS time acquired
    }else{
    canMsgStatus.data[2] = STATUS_NOTOK;
    }
    sendMessage(canMsgStatus);
}

void sendMessage(struct can_frame msg) {
    /* Sends CAN style message to XBee and logs to SD card.
     * By having in one function means we can be sure everything is robust to lack of SD card for example. */
    
    // Escape character delimter to spot the data
    out_byte(0x7E);
    
    // Split CAN ID into 2 bytes in order to .write()
    uint8_t can_id_b0 = (msg.can_id >> 8) & 0xFF;   // Remember, 11 bit CAN ID so 2047 is the max (0x7FF)
    uint8_t can_id_b1 = msg.can_id & 0xFF;
    
    out_byte(can_id_b0);
    out_byte(can_id_b1);
    out_byte(msg.can_dlc);

    // Add CAN ID to byte_buffer for later use in CRC calculation
    byte_buffer[0] = can_id_b0;
    byte_buffer[1] = can_id_b1;
    byte_buffer[2] = msg.can_dlc;

    //DEBUG_PRINTLN(msg.can_dlc);

    // Send data to XBee plus add to byte_buffer
    for (int i = 0; i<msg.can_dlc; i++)  {
        out_byte(msg.data[i]);
        byte_buffer[i+3] = msg.data[i];
    }

    int16_t crc = gencrc(msg.can_dlc);
    //int16_t crc = 0x6564;
    // Clear array?

    out_byte((crc >> 8) & 0xFF);    // Bit shift and transmit CRC
    out_byte(crc & 0xFF);
    
    DEBUG_PRINTLN();
    dataFile.println();
}

void out_byte(uint8_t b) {
    XBeeSL.write(b);
    DEBUG_PRINTHEX(b);
    DEBUG_PRINT(" ");
    if (dataFile) {
        dataFile.print(b, HEX);
        dataFile.print(" ");
    }
    else {
        // SD broken flag eg LED?
    }
}

int gencrc(unsigned char dlc) {
    uint16_t crc = 0, i;
    for (i = 0; i < dlc+2; i++) {
        crc = _crc16_update(crc, byte_buffer[i]);
    }
    return crc;
}

void doGPS() {
    char c = GPS.read();
    if (millis() - timer > 2000) {//config.gps_update
        //DEBUG_PRINTLN("The time has come..."); 
        timer = millis(); // reset the timer
        if (GPS.newNMEAreceived() && GPS.parse(GPS.lastNMEA())) {
            //DEBUG_PRINTLN("Do Stuff");
            //print_datetimefix();
            //print_location();
            gps2canMsgs();
        }
        else {
            //DEBUG_PRINTLN("Don't Do Stuff"); 
        }
    }
}

void gps2canMsgs() {
    // Time + fix
    canMsgSys.can_id  = 0x0F6;  /// Maybe configure address from SD card?
    canMsgSys.can_dlc = 8;

    canMsgSys.data[0] = GPS.hour;
    canMsgSys.data[1] = GPS.minute;
    canMsgSys.data[2] = GPS.seconds;
    canMsgSys.data[3] = GPS.year;
    canMsgSys.data[4] = GPS.month;
    canMsgSys.data[5] = GPS.day;
    canMsgSys.data[6] = GPS.fix;
    canMsgSys.data[7] = GPS.fixquality;
    sendMessage(canMsgSys);
    //delay(100);

    // Speed + angle
    canMsgSys.can_id  = 0x0F7;
    canMsgSys.can_dlc = 8;

    *(float*)(my_bytes) = GPS.speed;    // Convert GPS.speed from float to four bytes
    canMsgSys.data[0] = my_bytes[3];    // Add each byte to the CAN message
    canMsgSys.data[1] = my_bytes[2];
    canMsgSys.data[2] = my_bytes[1];
    canMsgSys.data[3] = my_bytes[0];
    
    *(float*)(my_bytes) = GPS.angle;
    canMsgSys.data[4] = my_bytes[3];
    canMsgSys.data[5] = my_bytes[2];
    canMsgSys.data[6] = my_bytes[1];
    canMsgSys.data[7] = my_bytes[0];

    sendMessage(canMsgSys);
    //delay(100);

    // Latitude
    canMsgSys.can_id  = 0x0F8;
    canMsgSys.can_dlc = 5;

    *(float*)(my_bytes) = GPS.latitude;
    canMsgSys.data[0] = my_bytes[3];
    canMsgSys.data[1] = my_bytes[2];
    canMsgSys.data[2] = my_bytes[1];
    canMsgSys.data[3] = my_bytes[0];
    canMsgSys.data[4] = GPS.lat;
    
    sendMessage(canMsgSys);
    //delay(100);

    // Longitude
    canMsgSys.can_id  = 0x0F9;
    canMsgSys.can_dlc = 5;

    *(float*)(my_bytes) = GPS.longitude;
    canMsgSys.data[0] = my_bytes[3];
    canMsgSys.data[1] = my_bytes[2];
    canMsgSys.data[2] = my_bytes[1];
    canMsgSys.data[3] = my_bytes[0];
    canMsgSys.data[4] = GPS.lon;
    
    sendMessage(canMsgSys);
    //delay(100);

    // Altitude + satellites
    canMsgSys.can_id  = 0x0FA;
    canMsgSys.can_dlc = 5;

    *(float*)(my_bytes) = GPS.altitude;
    canMsgSys.data[0] = my_bytes[3];
    canMsgSys.data[1] = my_bytes[2];
    canMsgSys.data[2] = my_bytes[1];
    canMsgSys.data[3] = my_bytes[0];
    canMsgSys.data[4] = GPS.satellites;
    
    sendMessage(canMsgSys);
    //delay(100);

}



void pollMPPT() {
  /** Additional data stream template **/
    canMsgSys.can_id = 0x711; // poll the second MPPT
    canMsgSys.can_dlc = 8;
    // Clear buffer
    for (int i = 0; i<sizeof(canMsgSys.data); i++)  {
        canMsgSys.data[i] = 0x00;
    }
    mcp2515.sendMessage(&canMsgSys);
    canMsgSys.can_id = 0x771; // poll the second MPPT
    mcp2515.sendMessage(&canMsgSys);
    readCAN();


    canMsgSys.can_id = 0x712; // poll the second MPPT
    mcp2515.sendMessage(&canMsgSys);
    canMsgSys.can_id = 0x772; // poll the second MPPT
    mcp2515.sendMessage(&canMsgSys);
    readCAN();
}
void pollSensor() {
    /** Additional data stream template **//*
    if (millis() - timer > config.ds1_ud) {
        DEBUG_PRINTLN("Data stream group 1 is being read and transmitted."); 
        ds1_timer = millis(); // reset the timer
        int ds1val_a;
        ds1val_a = obtain_ds1val_a();
        canMsg.can_id = 0x123;
        canMsg.can_dlc = sizeof(ds1val_a);
        canMsg.data[0] = (ds1val_a >> 32) & 0xFF;
        canMsg.data[1] = (ds1val_a >> 16) & 0xFF; 
        canMsg.data[2] = (ds1val_a >> 8) & 0xFF; 
        canMsg.data[3] = (ds1val_a >> 0) & 0xFF; 
    }

    if (millis() - timer > config.ds2_ud) { // Currently both use canMsg - be careful we don't overwrite
        DEBUG_PRINTLN("Data stream group 2 is being read and transmitted."); 
        ds2_timer = millis(); // reset the timer
        int ds2val_a;
        ds2val_a = obtain_ds2val_a();
        canMsg.can_id = 0x124;
        canMsg.can_dlc = sizeof(ds2val_a);
        canMsg.data[0] = (ds2val_a >> 32) & 0xFF;
        canMsg.data[1] = (ds2val_a >> 16) & 0xFF; 
        canMsg.data[2] = (ds2val_a >> 8) & 0xFF; 
        canMsg.data[3] = (ds2val_a >> 0) & 0xFF; 
    }
    */
}

/*
int softFilter(uint32_t canID) {
    int index = findIndex(canIDs, sizeof(canIDs), canID);
    if (index == -1) {
        return 1;   // If CAN ID is not present, pass through message
        //return config.inv_id_case; ///maybe config so optional to do this
    }
    if (passRate[index] == 0) {
        return 0;   // Set to zero for no pass rate
    }
    if (countID[index] < passRate[index]) {
        countID[index]++;
        return 0;
    }
    else {
        countID[index] = 0;
        return 1;
    }
}

int findIndex(uint32_t IDs[], uint8_t N, uint32_t to_find) {
    for (int i = 0; i < N; i++) {
        if (IDs[i] == to_find) {
            return i;   // Returns the value of the index if present.
        }
    }
    return -1;
}
*/

void load_config(const char *filename, conf &config) {
    // Open file for reading
    File configFile = SD.open(filename);
    DEBUG_PRINT("Opening: ");
    DEBUG_PRINTLN(filename);
    //char configFile[] = "{\"speedtype\":\"kmh\",\"mode\":1,\"somevalues\":[1.1,1.23456]}";

    // Size of the stuff
    DynamicJsonDocument doc(192); // Tool to calculate this value: https://arduinojson.org/v6/assistant/

    // Parse the file
    DeserializationError error = deserializeJson(doc, configFile);

    if (error) {
        // Cry if we have an error
        DEBUG_PRINT(F("deserializeJson() failed: "));
        DEBUG_PRINTLN(error.f_str());
        // But also do what we can and use some defaults
        set_defaults(config);
        sendStatus(3, STATUS_NOTOK);
        return;
    }

    // Put the read values into our config structure
    config.gps_update = doc["gps_update"];  DEBUG_PRINT("GPS UPDATE:\t");   DEBUG_PRINTLN(config.gps_update);
    config.time_fix = doc["time_fix"];      DEBUG_PRINT("TIME FIX:\t");     DEBUG_PRINTLN(config.time_fix);
    config.sd_update = doc["sd_update"];    DEBUG_PRINT("SD UPDATE:\t");    DEBUG_PRINTLN(config.sd_update);
    config.speedtype = doc["speedtype"];    DEBUG_PRINT("SPEEDTYPE:\t");    DEBUG_PRINTLN(config.speedtype);
    config.mode = doc["mode"];              DEBUG_PRINT("MODE:\t");         DEBUG_PRINTLN(config.mode);
    config.gps_update = doc["mppt_update"]; DEBUG_PRINT("mppt UPDATE:\t");  DEBUG_PRINTLN(config.mppt_update);
    config.gps_update = doc["status_update"]; DEBUG_PRINT("status UPDATE:\t");  DEBUG_PRINTLN(config.status_update);
    config.value0 = doc["somevalues"][0];   DEBUG_PRINT("VAL0:\t");         DEBUG_PRINTLN(config.value0);
    config.value1 = doc["somevalues"][1];   DEBUG_PRINT("VAL1:\t");         DEBUG_PRINTLN(config.value1);

    DEBUG_PRINTLN("Configuration set from SD, closing file");
    // Close the file; we can only have one open at a time
    configFile.close();

    // CAN Message configuration file
    // This is big so can't just do at once: https://arduinojson.org/v6/how-to/deserialize-a-very-large-document/
    // Cycle through and extract present CAN IDs and frequency rates. Append each to separate array
    sendStatus(3, STATUS_OK);
}

void save_config(const char *filename, conf &config) { // We might want to
    // Save current config
    // https://arduinojson.org/v5/example/config/
}

void set_defaults(conf &config) {
    /* We run this is for whatever reason we can't read config.yml
        a)  Either can't initialise SD card, or
        b)  can't find file or deserialize it.
        c)  At the moment if a field doesn't exist, it's incorrectly read as zero.     */
    config.gps_update = 2000; // 2000ms update on position and time
    config.sd_update = 2000;
    config.time_fix = 10000;
    config.speedtype = "kmh";
    config.mode = 1;
    config.mppt_update = 1000;
    config.status_update = 1000;
    config.value0 = -1;
    config.value1 = -1;
    DEBUG_PRINTLN("Using defaults");
    /// Actually probably better to set these at the start and overwrite IF we can. ie if we can't we just use the original value
}

void shut_down() { // If called by an interrupt, not sure how much of this we works since some timers are affected
    /* Shut down sequence */
    // Have this triggered by an interupt on the safestate line or similar

    // Get time
    GPS.read();
    // Send signal to XBee saying system going down (with location?)
    DEBUG_PRINT("I've gone to sleep");
    // Log final info to sd card
    // Close and terminate SD card file
    DEBUG_PRINT("Closing SD card...");
    dataFile.close();
    DEBUG_PRINTLN("closed");

    DEBUG_PRINT("Car entered safesafe at: ");
    if (GPS.hour < 10) { Serial.print('0'); }
    Serial.print(GPS.hour, DEC); Serial.print(':');
    if (GPS.minute < 10) { Serial.print('0'); }
    Serial.print(GPS.minute, DEC); Serial.print(':');
    if (GPS.seconds < 10) { Serial.print('0'); }
    Serial.println(GPS.seconds, DEC);

    while (1){ /// Have this controlled by safestate instead
        DEBUG_PRINTLN("Hi, I'm asleep");
        if (digitalRead(SLEEP_INT)){
            // Leave and start fresh (this assumes that the Arduino doesn't need a complete restart)
            log_start_up(log_filename);
            return;
        }
        delay(5000); // Don't use delay() if we are using a interrupt, it doesn't work.
    }
}

void flag_status(){
  if (millis() - flag_timer > 500) {
    flag_timer = millis();
    sendStatus(4, STATUS_OK);
    canMsgStatus.data[4] = STATUS_NOTOK; //lower the flag again so
  } 
}

void sd_info(){
    // Check number of files on SD card and storage usage: https://www.arduino.cc/en/Tutorial/LibraryExamples/CardInfo
    /*SdVolume volume;
    SdFile root;
    if (!volume.init(card)) {
        DEBUG_PRINTLN("Could not find FAT16/FAT32 partition.\nMake sure you've formatted the card");
        return;
    }
    uint32_t volumesize;
    volumesize = volume.blocksPerCluster();    // clusters are collections of blocks
    volumesize *= volume.clusterCount();       // we'll have a lot of clusters
    volumesize /= 2;                           // SD card blocks are always 512 bytes (2 blocks are 1KB)*/
    // Report these via XBee and DEBUG_SERIAL if DEBUG==1
}

void log_start_up(char *filename){
    // filename is "dataYYMMDD00.csv"
    // https://learn.adafruit.com/adafruit-data-logger-shield/using-the-real-time-clock-3

    // Get date. If GPS signal is not available this will default to 00/00/00
    int8_t YY = GPS.year;
    int8_t MM = GPS.month;
    int8_t DD = GPS.day;

    // Replace YYMMDD with date
    filename[4-4] = YY/10 + '0';
    filename[5-4] = YY%10 + '0';
    filename[6-4] = MM/10 + '0';
    filename[7-4] = MM%10 + '0';
    filename[8-4] = DD/10 + '0';
    filename[9-4] = DD%10 + '0';

    // If we've already recorded today, +1 to trailing number
    for (uint8_t i = 0; i < 100; i++) {
        filename[10-4] = i/10 + '0';
        filename[11-4] = i%10 + '0';
        if (! SD.exists(filename)) {
            dataFile = SD.open(filename, FILE_WRITE); // Only create a new file which doesn't exist
             if (dataFile) {
                DEBUG_PRINT("Opening file: ");
                DEBUG_PRINTLN(filename);
                // Log our current configuration in some form
                //dataFile.println("Logging to file");
                dataFile.println("ESC ID0 ID1 DLC B0 B1 B2 B3 B4 B5 B6 B7 CRC0 CRC1");
                dataFile.println("");
                //dataFile.flush();
                sendStatus(1, 100+i);    // writing to SD card
            }
            // if the file isn't open, pop up an error:
            else {
                DEBUG_PRINT("Could not open file: ");
                DEBUG_PRINTLN(filename);
                /// Some sort of backup filename here?
                // will only log in loop if dataFile==True
                sendStatus(1, STATUS_NOTOK);   // notwriting to SD card
            }
            return;
        }
    }
}

void print_datetimefix() {
    Serial.print("\tDate: ");
    Serial.print(GPS.day, DEC); Serial.print('/');
    Serial.print(GPS.month, DEC); Serial.print("/20");
    Serial.println(GPS.year, DEC);
    // Time
    Serial.print("\tTime: ");
    if (GPS.hour < 10) { Serial.print('0'); }
    Serial.print(GPS.hour, DEC); Serial.print(':');
    if (GPS.minute < 10) { Serial.print('0'); }
    Serial.print(GPS.minute, DEC); Serial.print(':');
    if (GPS.seconds < 10) { Serial.print('0'); }
    Serial.println(GPS.seconds, DEC);
    // Fix information
    Serial.print("\tFix: "); Serial.print((int)GPS.fix);
    Serial.print(" quality: "); Serial.println((int)GPS.fixquality);
}

void print_location() {
    Serial.print("Location: ");
    Serial.print(GPS.latitude, 4); Serial.print(GPS.lat);
    Serial.print(", ");
    Serial.print(GPS.longitude, 4); Serial.println(GPS.lon);

    Serial.print("Speed (knots): "); Serial.println(GPS.speed);
    Serial.print("Angle: "); Serial.println(GPS.angle);
    Serial.print("Altitude: "); Serial.println(GPS.altitude);
    Serial.print("Satellites: "); Serial.println((int)GPS.satellites);
}
