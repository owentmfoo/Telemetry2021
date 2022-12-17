import sys

if __name__ == '__main__':  # Warn if trying to run this as a script
    print("\n**********************************************")
    print("   This is not meant to be run as a main script")
    print("   Run log-to-data.py or live-telem.py instead")
    print("**********************************************\n")
    sys.exit(4)

from telemetryParser import translateMsg
from datetime import datetime
from openpyxl import load_workbook, Workbook
from os.path import exists as fileExists
from typing import NamedTuple
from influxdb import InfluxDBClient

xlsxOutputFile: str = './CANTelemOutput.xlsx' #set equal to '' to switch off xslx output. Same for influx credentials and outputting to influx database
class influxCredentials(NamedTuple):
    # influx configuration - edit these
    username: str  = "admin"
    password: str  = "password"
    db: str    = "Test22DB" #"PalaceGreen_2022"
    host: str  = "127.0.0.1"
    port: int  = 8086
    enabled: bool = False
ifCredentials = influxCredentials()

#STORE DATA REGION
storeFunctionList: list = []
def storeData(msg: bytearray) -> None:
    msgItem, msgSource, msgBody, msgTime, msgCRCStatus = translateMsg(msg) #this implicitly updates timestamp. I.e always run this first
    for i in storeFunctionList:
        i(msgItem, msgSource, msgBody, msgTime, msgCRCStatus)

#INFLUX REGION
#influx store function
def __toInflux(msgItem: str, msgSource: str, msgBody: dict, msgTime: datetime, msgCRCStatus: bool) -> None:
    global influxClient
    body = [{
                "measurement": msgSource + '/' + msgItem, #NOTE: Should check format
                #"": msgItem,
                "time": int(msgTime.timestamp() * 1000), #NOTE: This should already be an int because * 1000 but isnt and idk why. NOTE: check
                "fields": msgBody
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
    XlsxOutWorkSheet.cell(column=1, row=XlsxOutRowPointer, value=msgTime)
    XlsxOutWorkSheet.cell(column=2, row=XlsxOutRowPointer, value=msgSource)
    XlsxOutWorkSheet.cell(column=3, row=XlsxOutRowPointer, value=msgItem)

    columnPointer: int = 4
    for dataLabel, value in msgBody.items():
        XlsxOutWorkSheet.cell(column=columnPointer, row=XlsxOutRowPointer, value=dataLabel)
        XlsxOutWorkSheet.cell(column=columnPointer, row=XlsxOutRowPointer, value=value)
        columnPointer += 2
    
    XlsxOutWorkSheet.cell(column=columnPointer, row=XlsxOutRowPointer, value=msgCRCStatus)

    XlsxOutRowPointer = XlsxOutRowPointer + 1
    XlsxOutWorkbook.save(xlsxOutputFile) #save every time a line is written
#init excel output
XlsxOutWorkbook = ''
XlsxOutWorkSheet = ''
XlsxOutRowPointer: int = 2 #skip first row as that is for column labels
if not (xlsxOutputFile == ''): #if '', disable xlsx output
    if fileExists(xlsxOutputFile):
        XlsxOutWorkbook = load_workbook(xlsxOutputFile, read_only=False)
        if 'Translated Messages' in XlsxOutWorkbook.sheetnames:
            XlsxOutWorkSheet = XlsxOutWorkbook['Translated Messages']
            XlsxOutRowPointer = XlsxOutWorkSheet.max_row + 1 #leave gap in between sessions. Just to make reader aware that more than one session continued with the same file
    else:
        XlsxOutWorkbook = Workbook() #creates new workbook
        XlsxOutWorkSheet = XlsxOutWorkbook.create_sheet(title='Translated Messages')
    
    #If new log, add columns labels and excel filters
    if XlsxOutRowPointer == 2: #if true, then this is a new log
        for i, label in enumerate(['Time', 'Source', 'Item', 'Data...', "CRC check"]): #Column labels
            XlsxOutWorkSheet.cell(column=i + 1, row=1, value=label) 
        XlsxOutWorkSheet.auto_filter.ref = 'A1:B' + str(XlsxOutWorkSheet.max_row) #Add filters to first two columns (Source and Item)
    
    storeFunctionList.append(__toXlsx) #add function name to list.

def endSession():
    if XlsxOutWorkbook is Workbook:
        XlsxOutWorkbook.save(xlsxOutputFile)
        XlsxOutWorkbook.close()
    
    if influxCredentials.enabled:
        influxClient.close()
