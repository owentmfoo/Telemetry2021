from datetime import datetime
from openpyxl import load_workbook, Workbook
import sys, getopt
from os.path import exists as fileExists
import struct
import time

configFile = './CANConfig.xslx'
xlsxOutputFile = '' #set equal to '' to switch off xslx output. Same for influx credentials and outputting to influx database
influxCredentials = ''

#STORE DATA REGION
storeFunctionList: list[str] = []
def storeData(msg: str):
    msgItem, msgSource, msgBody = __translateMsg(msg) #this implicitly updates timestamp. I.e always run this first
    for i in storeFunctionList:
        i(msgItem, msgSource, msgBody)

#INFLUX REGION
#init influx
if not (influxCredentials == ''): #if '', disable influx output
    
    storeFunctionList.append('toInflux') #add function name to list.
#influx store function
def toInflux(msgItem: str, msgSource: str, msgBody: dict):
    body = [{
                "measurement": msgSource, #Should
                #"": msgItem,
                "time": __getTime(),
                "fields": msgBody
            }]

#XLSX REGION
#init excel output
XlsxOutWorkbook = ''
XlsxOutWorkSheet = ''
XlsxOutRowPointer = 2 #skip first row as that is for column labels
if not (xlsxOutputFile == ''): #if '', disable xlsx output
    if fileExists(xlsxOutputFile):
        XlsxOutWorkbook = load_workbook(xlsxOutputFile, read_only=False)
        if 'Translated Messages' in XlsxOutWorkbook.worksheets:
            XlsxOutWorkSheet = XlsxOutWorkbook['Translated Messages']
            XlsxOutRowPointer = XlsxOutWorkSheet.max_row + 1 #leave gap in between sessions. Just to make reader aware that more than one session continued with the same file
    else:
        XlsxOutWorkbook = Workbook() #creates new workbook
        XlsxOutWorkSheet = XlsxOutWorkbook.create_sheet(title='Translated Messages')
    
    #If new log, add columns labels and excel filters
    if XlsxOutRowPointer == 2: #if true, then this is a new log
        for i, label in enumerate(['Source', 'Item', 'Data...']): #Column labels
            XlsxOutWorkSheet.cell(column=i + 1, row=1, value=label) 
        XlsxOutWorkSheet.auto_filter.ref = 'A1:' + str(XlsxOutWorkSheet.max_row) + '2'# Add filters to first two columns (Source and Item)
    
    storeFunctionList.append('toXlsx') #add function name to list.
#xlsx store function
def toXlsx(msgItem: str, msgSource: str, msgBody: dict):
    print()
        


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
def __translateMsg(msg: str) -> tuple[str, str, dict]:
    msgBytes = msg.split(' ') #Format: ESC ID0 ID1 DLC B0 B1 B2 B3 B4 B5 B6 B7 CRC0 CRC1

    #do a lookup in spreadsheet using can id to work out can message type
    canId = int(msgBytes[1:3], base=16)
    configRow = 1
    while not (str(configSheet.cell(configRow, 1).value) == "END"):
        if configSheet.cell(configRow, __getConfigColumn("CAN_ID (dec)")).value == canId: #column 6 canId
            break
    
    #Translate
    msgItem: str = configSheet.cell(configRow, __getConfigColumn("ItemCC")).value #use camel case formats to avoid issues with storing data
    msgSource: str = configSheet.cell(configRow, __getConfigColumn("SourceCC")).value
    msgData = struct.unpack(configSheet.cell(configRow, __getConfigColumn("struct unpack code")).value, bytes.fromhex(''.join(str(element) for element in msgBytes[4:12])))
    msgBody: dict = {}
    dataIterator = 0
    for i in range(0, 8):
        fieldName = configSheet.cell(configRow, __getConfigColumn("BYTE_" + i + "CC")).value
        if not (fieldName == '-'): #if byte labelled '-', then is part of a value that spans multiple bytes or is not being used at all
            msgBody.update({fieldName, msgData[dataIterator]})
            dataIterator = dataIterator + 1
    #msgDataType = configSheet.cell(configRow, __getConfigColumn("data type"))


    #if GPS time and fix message, update time
    if msgItem == "TimeAndFix":
        lastGPSTime.hour = msgData[0]
        lastGPSTime.minute = msgData[1]
        lastGPSTime.second = msgData[2]
        lastGPSTime.day = msgData[3]
        lastGPSTime.month = msgData[4]
        lastGPSTime.year = msgData[5]
        timeFetched = time.time() # update when data was last fetched

    return msgItem, msgSource, msgBody
    
def __getConfigColumn(columnLabel: str) -> int: #used to make sure reordering of columns in config spreadsheet does not cause errors in this script
    if columnLabel in configColumns:
        return configColumns[columnLabel]
    else:
        print("Column '" + columnLabel + "' missing in 'CAN data' worksheet in config")
        sys.exit(2)


#try:
#    opts, args = getopt.getopt(sys.argv[1:],"c:i:it:o:ot:",["configTable=", "input=", "inputType=", "output=", "outputType=", "headerStream="]) #from https://www.tutorialspoint.com/python/python_command_line_arguments.htm.
#except:
#    print('Translator.py -i <input data> -o <output file> -c <config table file> -h <header file>')
#    sys.exit(2)
#for opt, arg in opts:
#    #print(arg)
#    if opt in ("-i", "--inputFile"):
#        inputfile = arg
#    elif opt in ("-o", "--outputFile"):
#        outputfile = arg
#    elif opt in ("-c", "--configTable"):
#        configFile = arg
#    elif opt in ("-h", "--headerStream"):
#        headerFile = arg
#print("Config file: " + configFile)
