import serial
from .telemetryStorer import storeData

SERIALPORT = '/dev/ttyUSB0' # Raspberry Pi
# SERIALPORT = '/dev/cu.usbmodem14101' # macOS
BAUD = 115200

serialConnection = serial.Serial(SERIALPORT, BAUD)
EndOfFrameMarker = b'\x7E'
frameReadInProgress: bool = False
frameBuffer: bytearray = bytearray()

#Radio listen loop
while True:
    if serialConnection.in_waiting: #in_waiting returns number of bytes ready to be processed. If greater than 0, process data
        inputByte = serialConnection.read(size = 1)  # Read byte
        
        if inputByte == EndOfFrameMarker:
            storeData(frameBuffer)
            frameBuffer = bytearray() #reset buffer
        else:
            frameBuffer.append(inputByte)
