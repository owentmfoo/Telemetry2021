import sys

if __name__ == '__main__':  # Warn if trying to run this as a script
    print("\n**********************************************")
    print("   This is not meant to be run as a main script")
    print("   Run log-to-data.py or live-telem.py instead")
    print("**********************************************\n")
    sys.exit(4)

from datetime import datetime, timezone, timedelta
from openpyxl import load_workbook
from os.path import exists as fileExists
import struct
import time
from crccheck.crc import Crc16Modbus
from binascii import hexlify
from csv import DictReader as csvAsDictReader

#configFile: str = './CANConfig.xslx' #raspberrypi
configFile: str = '../../CANTranslator/config/CANBusData(saved201022)Modified.xlsm' #testing with windows

#TIME REGION
lastGPSTime: datetime = datetime(1970, 1, 1, 3, 0, 0) #Excel does not support timezones tzinfo=timezone.utc
timeFetched: int = 0 #Time since time variables were last updated in seconds #round(time.time() * 1000)
def __getTime(recievedMillis: int) -> datetime:
    millisDelta: int = recievedMillis - timeFetched
    if millisDelta < 0:
        millisDelta = millisDelta + 2**32 #Unsign the delta. This method should work as long as the GPS update is not older than 2^32-1 milliseconds
    
    print("millisDelta" + str(millisDelta))
    currentTime = lastGPSTime + timedelta(milliseconds = millisDelta)
    return currentTime

#CONFIG INIT REGION
#get config from excel config workbook. Check 'CAN data' sheet exists
if not fileExists(configFile):
    print("Config file " + configFile + " does not exist")
    sys.exit(5)
#configData = open(configFile)

#with open(configFile) as configData:
config: dict[int, dict] = dict()
#with load_workbook(configFile, read_only=True, keep_vba=True, data_only=True) as configBook:
configBook = load_workbook(configFile, read_only=True, keep_vba=True, data_only=True) #Config has VBA macros. Also, data_only=True only works if formulae were evaluated. This is fine since excel does this and openpyxl does not modify config
if not 'CAN Data' in configBook.sheetnames: #check CAN data worksheet exists
    print("Missing 'CAN Data' worksheet in workbook. Is the config file correct?")
    print("Worksheets available: ", end='')
    print(configBook.sheetnames)
    sys.exit(1)
configSheet = configBook['CAN Data']
#c = csvAsDictReader(configData)
configColumns: dict[str, int] = dict()
for columnIterator in range(1, configSheet.max_column + 1):
    configColumns[configSheet.cell(row=1, column=columnIterator).value] = columnIterator
for rowIndex in range(2, configSheet.max_row + 1):
    if configSheet.cell(row=rowIndex, column=1).value == "END":
        break
    rowAsDict = dict()
    for columnName in configColumns:
        rowAsDict[columnName] = configSheet.cell(row=rowIndex, column=configColumns[columnName]).value
    config[configSheet.cell(row=rowIndex, column=configColumns["CAN_ID (dec)"]).value] = rowAsDict
configBook.close()

rowForCurrentMessage = dict()
def __fromConfig(dictKey):
    #row = config.get(canId)
    if dictKey in rowForCurrentMessage:
        return rowForCurrentMessage[dictKey]
    else:
        print("Column '" + dictKey + "' missing in 'CAN Data' worksheet in config")
        sys.exit(2)

print(config)

#TRANSLATE MESSAGE REGION
def translateMsg(msgBytesAndTime: bytearray) -> tuple[str, str, dict, datetime, bool]: #Format: TI0 TI1 TI2 TI3 ID0 ID1 DLC B0 B1 B2 B3 B4 B5 B6 B7 CRC0 CRC1 (NOTE that end of frame marker is not included)
    print("Translating -> " + str(msgBytesAndTime))
    
    msgBytes = msgBytesAndTime[4:]

    #get time
    #msgTime = __getTime() #get current time (according to GPS time, not system time)

    #CRC check
    msgCRCStatus = __checkCRC(msgBytesAndTime)
    if not msgCRCStatus:
        print("CRC FAILED (ignoring message) ")# + msgTime.strftime("%Y-%m-%d %H:%M:%S"))
        return "CRCFail", "", {"Data": hexlify(msgBytesAndTime)}, datetime(1970, 1, 1, 3, 0, 0), False

    #convert recieved millis delta time
    recievedMillisTime = int.from_bytes(msgBytesAndTime[0:3], byteorder="little")
    msgTime = __getTime(recievedMillisTime)

    #do a lookup in spreadsheet using can id to work out can message type
    canId = msgBytes[0] << 8 | msgBytes[1]
    global rowForCurrentMessage
    rowForCurrentMessage = config[canId]
    
    #Translate
    msgItem: str = __fromConfig("ItemCC")
    msgSource: str = __fromConfig("SourceCC")
    msgDLC = __fromConfig("DLC")
    msgData = struct.unpack(__fromConfig("struct unpack code"), msgBytes[3:(3 + msgDLC)])
    msgBody: dict = {}
    dataIterator = 0
    for i in range(0, 8):
        fieldValue = __fromConfig("BYTE_" + str(i) + "CC")
        if not (fieldValue == '-'): #if byte labelled '-', then is part of a value that spans multiple bytes or is not being used at all
            msgBody.update({fieldValue: msgData[dataIterator]})
            dataIterator = dataIterator + 1

    #if GPS time and fix message, update time
    if canId == 246: #can id for GPS Time and Fix message (hex: 0x0F6)
        print("Updating GPS time...")
        global lastGPSTime
        global timeFetched
        lastGPSTime = datetime( \
            hour = msgData[0], \
            minute = msgData[1], \
            second = msgData[2], \
            day = msgData[3], \
            month = msgData[4], \
            year = 2000 + msgData[5] ) #msgData only contains last 2 digits of year so have to add 2000
        timeFetched = int.from_bytes(recievedMillisTime, byteorder="little") # update when data was last fetched
        print("GPS time is now: " + lastGPSTime.strftime("%Y-%m-%d %H:%M:%S"))
    
    print("Current Time: " + msgTime.strftime("%Y-%m-%d %H:%M:%S"))

    return msgItem, msgSource, msgBody, msgTime, msgCRCStatus

def __checkCRC(msgBytes: bytearray) -> bool:
    data = msgBytes[0:-2]      # All except the last two
    crc_rcvd = int.from_bytes(msgBytes[-2:], "big")  # Convert received CRC code to int
    crc_calc = Crc16Modbus.calc(data)
    return crc_calc == crc_rcvd
