#ifndef SENDMESSAGE_HEADER
#define SENDMESSAGE_HEADER

#include "src/CANApi/CanApiv03.hpp"

void setupSending();
void sendMessage(CANHelper::Messages::CANMsg& msg);

#endif