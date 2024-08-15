import sys

if __name__ == '__main__':  # Warn if trying to run this as a script
    print("\n**********************************************")
    print("   This is not meant to be run as a main script")
    print("   Run log-to-data.py or live-telem.py instead")
    print("**********************************************\n")
    sys.exit(4)

from datetime import datetime
from openpyxl import load_workbook, Workbook
from os.path import exists as fileExists

from influxdb import InfluxDBClient
from Receiver.telemetry_parser3 import TelemetryParser
from Receiver.receiver_config import ifCredentials

telemetry_parser = TelemetryParser()

#TELEMETRY STORE CONFIG
#xlsxOutputFile: str = './ExcelOutput/ExcelTest.xlsx' #set equal to '' to switch off xslx output
xlsxOutputFile: str = ''

#STORE DATA REGION
storeFunctionList: list = []
def storeData(msg: bytearray) -> None:
    msgItem, msgSource, msgBody, msgTime, msgCRCStatus = telemetry_parser.translate_msg(msg) #this implicitly updates timestamp. I.e always run this first
    for i in storeFunctionList:
        i(msgItem, msgSource, msgBody, msgTime, msgCRCStatus)

#INFLUX REGION
#influx store function
def __toInflux(msgItem: str, msgSource: str, msgBody: dict, msgTime: datetime, msgCRCStatus: bool) -> None:
    if not msgCRCStatus: #CRC failed, message was corrupted. Do not add to database
        #print("CRC FAILED for " + msgSource + "/" + msgItem + " at " + msgTime.strftime("%Y-%m-%d %H:%M:%S"))
        return
    global influxClient
    
    body = [{
                "measurement": msgSource + '/' + msgItem, #NOTE: Should check format. Old format was "measurement": msgSource but assumes that all fields in all items are uniquely named
                #"time": int(msgTime.timestamp() * 1000), #NOTE: get timestamp from 1970 in milliseconds
                "time": msgTime.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "fields": msgBody #dictionary of all fields and corresponding values in CAN message
            }]
    influx_success = influxClient.write_points(body, time_precision='ms', protocol='json') #Write data and check if successful
    if influx_success is False:
        print("Error writing to Influx for %s/%s (%s)" %msgSource %msgItem %msgBody)
#init influx
influxClient = ''
if ifCredentials.enabled: #if false, do not initialise or enable influx output
    influxClient = InfluxDBClient(host=ifCredentials.host, port=ifCredentials.port, username=ifCredentials.username, password=ifCredentials.password, database=ifCredentials.db)
    storeFunctionList.append(__toInflux) #add function name to list.
#XLSX REGION
#xlsx store function
def __toXlsx(msgItem: str, msgSource: str, msgBody: dict, msgTime: datetime, msgCRCStatus: bool) -> None:
    global XlsxOutWorkbook
    global XlsxOutWorkSheet
    global XlsxOutRowPointer
    global xlsxOutputFile
    
    msgTime = msgTime.replace(tzinfo=None)
    XlsxOutWorkSheet.cell(column=1, row=XlsxOutRowPointer, value=msgTime)
    XlsxOutWorkSheet.cell(column=2, row=XlsxOutRowPointer, value=msgTime)
    
    XlsxOutWorkSheet.cell(column=3, row=XlsxOutRowPointer, value=msgSource)
    XlsxOutWorkSheet.cell(column=4, row=XlsxOutRowPointer, value=msgItem)

    columnPointer: int = 5
    for dataLabel, value in msgBody.items():
        XlsxOutWorkSheet.cell(column=columnPointer, row=XlsxOutRowPointer, value=dataLabel)
        #print("DEBUG: " + dataLabel + " : " + str(value))
        XlsxOutWorkSheet.cell(column=columnPointer + 1, row=XlsxOutRowPointer, value=value)
        columnPointer += 2
    
    XlsxOutWorkSheet.cell(column=21, row=XlsxOutRowPointer, value=msgCRCStatus)

    XlsxOutRowPointer = XlsxOutRowPointer + 1
    XlsxOutWorkbook.save(xlsxOutputFile) #save every time a line is written. NOTE: this can corrupt xlsx file if program doesn't exit gracefully (i.e. the computer is unplugged). This is fine as it can be rebuilt using telemetry hex dump on SD card
#init excel output
XlsxOutWorkbook = ''
XlsxOutWorkSheet = ''
XlsxOutRowPointer: int = 2 #skip first row as that is for column labels
if not (xlsxOutputFile == ''): #if '', disable xlsx output
    if fileExists(xlsxOutputFile):
        XlsxOutWorkbook = load_workbook(xlsxOutputFile, read_only=False)
        if 'Translated Messages' in XlsxOutWorkbook.sheetnames:
            XlsxOutWorkSheet = XlsxOutWorkbook['Translated Messages']
            XlsxOutRowPointer = XlsxOutWorkSheet.max_row + 3 #leave gap in between sessions. Just to make reader aware that more than one session continued with the same file
    else:
        XlsxOutWorkbook = Workbook() #creates new workbook
        XlsxOutWorkSheet = XlsxOutWorkbook.create_sheet(title='Translated Messages')
    
    #If new log, add columns labels and excel filters
    if XlsxOutRowPointer == 2: #if true, then this is a new log
        for i, label in enumerate(['Date', 'Time', 'Source', 'Item', 'Data...']): #Column labels
            XlsxOutWorkSheet.cell(column=i + 1, row=1, value=label)
        XlsxOutWorkSheet.cell(column=21, row=1, value="CRC check") #longest record is 19 cells so put CRC in 20th
        XlsxOutWorkSheet.auto_filter.ref = 'A1:T' + str(XlsxOutWorkSheet.max_row) #Add filters to columns (Source and Item)
    
    storeFunctionList.append(__toXlsx) #add function name to list.

def endSession():
    global XlsxOutWorkbook
    global XlsxOutWorkSheet
    global XlsxOutRowPointer
    global xlsxOutputFile

    print("Ending telemetry storer session")

    if type(XlsxOutWorkbook) is Workbook:
        print("Closing xlsx output file")
        XlsxOutWorkbook.save(xlsxOutputFile)
        XlsxOutWorkbook.close()
    
    if ifCredentials.enabled:
        print("Closing InfluxDB connection")
        influxClient.close()
