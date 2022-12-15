import sys

if __name__ == '__main__':  # Warn if trying to run this as a script
    print("\n**********************************************")
    print("   This is not meant to be run as a main script")
    print("   Run log-to-data.py or live-telem.py instead")
    print("**********************************************\n")
    sys.exit(4)

from datetime import datetime
from openpyxl import load_workbook
import struct
import time
from crccheck.crc import Crc16Modbus

configFile: str = './CANConfig.xslx'

#TIME REGION
lastGPSTime = datetime.fromtimestamp(0)
timeFetched = time.time() #Time since time variables were last updated in seconds #round(time.time() * 1000)
def __getTime() -> datetime:
    currentTime = datetime.fromtimestamp(lastGPSTime.timestamp() + (time.time() - timeFetched))
    return currentTime

#CONFIG INIT REGION
#get config from excel config workbook. Check 'CAN data' sheet exists
config = load_workbook(configFile, read_only=True, keep_vba=True) #Config has VBA macros
if not 'CAN data' in config.worksheets: #check CAN data worksheet exists
    print("Missing CAN data worksheet in workbook. Is the config file correct?")
    sys.exit(1)
configSheet = config['CAN data']

#map column labels to column indices
configColumns = dict()
print("Getting column labels")
columnIterator = 1 #first index is 1. Assuming using .cell when getting data from spreadsheet
for column in configSheet.columns:
    print("Column: " + column[0])
    if column[0] in configColumns: #check for duplicates
        print("Column labels must be unique in 'CAN data' worksheet in config")
        sys.exit(3)
    configColumns.update({column[0], columnIterator})
    columnIterator = columnIterator + 1

#TRANSLATE MESSAGE REGION
def translateMsg(msgBytes: bytearray) -> tuple[str, str, dict, datetime, bool]: #Format: ID0 ID1 DLC B0 B1 B2 B3 B4 B5 B6 B7 CRC0 CRC1 (NOTE: end of frame marker not included)
    print("Translating -> " + msgBytes)

    #do a lookup in spreadsheet using can id to work out can message type
    canId = int(msgBytes[0:2], base=16)
    configRow = 1
    while not (str(configSheet.cell(configRow, 1).value) == "END"):
        if configSheet.cell(configRow, __getConfigColumn("CAN_ID (dec)")).value == canId: #column 6 canId
            break
    
    #Translate
    msgItem: str = configSheet.cell(configRow, __getConfigColumn("ItemCC")).value #use camel case formats to avoid issues with storing data
    msgSource: str = configSheet.cell(configRow, __getConfigColumn("SourceCC")).value
    #msgData = struct.unpack(configSheet.cell(configRow, __getConfigColumn("struct unpack code")).value, bytes.fromhex(''.join(str(element) for element in msgBytes[3:12])))
    msgData = struct.unpack(configSheet.cell(configRow, __getConfigColumn("struct unpack code")).value, msgBytes[3:11])
    msgBody: dict = {}
    dataIterator = 0
    for i in range(0, 8):
        fieldName = configSheet.cell(configRow, __getConfigColumn("BYTE_" + i + "CC")).value
        if not (fieldName == '-'): #if byte labelled '-', then is part of a value that spans multiple bytes or is not being used at all
            msgBody.update({fieldName, msgData[dataIterator]})
            dataIterator = dataIterator + 1
    #msgDataType = configSheet.cell(configRow, __getConfigColumn("data type"))


    #if GPS time and fix message, update time
    if canId == 246: #can id for GPS Time and Fix message (hex: 0x0F6)
        lastGPSTime.hour = msgData[0]
        lastGPSTime.minute = msgData[1]
        lastGPSTime.second = msgData[2]
        lastGPSTime.day = msgData[3]
        lastGPSTime.month = msgData[4]
        lastGPSTime.year = 2000 + msgData[5] #msgData only contains last 2 digits of year so have to add 2000
        timeFetched = time.time() # update when data was last fetched
    msgTime = __getTime() #get current time (according to GPS time, not system time)

    #CRC check
    msgCRCStatus = __checkCRC(msgBytes)

    return msgItem, msgSource, msgBody, msgTime, msgCRCStatus
    
def __getConfigColumn(columnLabel: str) -> int: #used to make sure reordering of columns in config spreadsheet does not cause errors in this script
    if columnLabel in configColumns:
        return configColumns[columnLabel]
    else:
        print("Column '" + columnLabel + "' missing in 'CAN data' worksheet in config")
        sys.exit(2)

def __checkCRC(msgBytes: bytearray) -> bool:
    data = msgBytes[0:-2]      # All except the last two
    crc_rcvd = int.from_bytes(msgBytes[-2:], "big")  # Convert received CRC code to int
    crc_calc = Crc16Modbus.calc(data)
    return crc_calc == crc_rcvd
