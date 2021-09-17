#include <SPI.h>
#include <mcp2515.h>

struct can_frame canMsg;
struct can_frame canMsgSys;
MCP2515 mcp2515(10);
uint8_t SPICS=10;
int i = 1;

uint32_t mppt_timer = millis();
void setup() {
  
  canMsgSys.can_dlc = 8;
  canMsgSys.data[0] = 0x00;
  canMsgSys.data[1] = 0x00; 
  canMsgSys.data[2] = 0x00; 
  canMsgSys.data[3] = 0x00; 
  canMsgSys.data[4] = 0x00; 
  canMsgSys.data[5] = 0x00; 
  canMsgSys.data[6] = 0x00;
  canMsgSys.data[7] = 0x00;
  
  Serial.begin(115200);

  mcp2515.reset();
  mcp2515.setBitrate(CAN_125KBPS, MCP_8MHZ);
  mcp2515.setNormalMode();
  
  delay(1000);
  
  Serial.println("------- CAN Read ----------");
  Serial.println("ID  DLC   DATA");
  




}

void loop() {



  
  sniffcan();
  pollMPPT();
}
void sniffcan(){
    MCP2515::ERROR rm_error_code = mcp2515.readMessage(&canMsg);
  if (rm_error_code == MCP2515::ERROR_OK) {
    Serial.print(canMsg.can_id, HEX); // print ID
    Serial.print(" "); 
    Serial.print(canMsg.can_dlc, HEX); // print DLC
    Serial.print(" ");
    
    for (int i = 0; i<canMsg.can_dlc; i++)  {  // print the data
      Serial.print(canMsg.data[i],HEX);
      Serial.print(" ");
    }

    Serial.println();      
    //Serial.println("Working?");
  }
}
void pollMPPT() {
    /** Additional data stream template **/
    if (1==1) {
        //DEBUG_PRINTLN("MPPT1 is being read and transmitted."); 
        mppt_timer = millis(); // reset the timer
        
        canMsgSys.can_id = 0x710; // poll the second MPPT
        mcp2515.sendMessage(&canMsgSys);
        
        canMsgSys.can_id = 0x711; // poll the second MPPT
        mcp2515.sendMessage(&canMsgSys);
        
        canMsgSys.can_id = 0x712; // poll the second MPPT
        mcp2515.sendMessage(&canMsgSys);
        /*
        canMsgSys.can_id = 0x713; // poll the second MPPT
        mcp2515.sendMessage(&canMsgSys);
        
        canMsgSys.can_id = 0x714;
        mcp2515.sendMessage(&canMsgSys);
        
        canMsgSys.can_id = 0x715; // poll the second MPPT
        mcp2515.sendMessage(&canMsgSys);
        
        canMsgSys.can_id = 0x716; // poll the second MPPT
        mcp2515.sendMessage(&canMsgSys);
        
        canMsgSys.can_id = 0x717; // poll the second MPPT
        mcp2515.sendMessage(&canMsgSys);
        
        canMsgSys.can_id = 0x718; // poll the second MPPT
        mcp2515.sendMessage(&canMsgSys);
        
        canMsgSys.can_id = 0x719; // poll the second MPPT
        mcp2515.sendMessage(&canMsgSys);
        
        canMsgSys.can_id = 0x71A; // poll the second MPPT
        mcp2515.sendMessage(&canMsgSys);
        
        canMsgSys.can_id = 0x71B; // poll the second MPPT
        mcp2515.sendMessage(&canMsgSys);
        canMsgSys.can_id = 0x71C; // poll the second MPPT
        mcp2515.sendMessage(&canMsgSys);
        canMsgSys.can_id = 0x71D; // poll the second MPPT
        mcp2515.sendMessage(&canMsgSys);
        canMsgSys.can_id = 0x71E; // poll the second MPPT
        mcp2515.sendMessage(&canMsgSys);
        canMsgSys.can_id = 0x71F; // poll the second MPPT
        mcp2515.sendMessage(&canMsgSys);*/
    }
}
