import os
#import struct
import sys, getopt
from Receiver.telemetryStorer import storeData,endSession
import atexit
import signal
from time import time

#trying to exit gracefully
keepLooping = True
def onProgramExit():
    global keepLooping
    keepLooping = False
def sigintHandler(sig, frame):
    onProgramExit()
atexit.register(onProgramExit)
signal.signal(signal.SIGINT, sigintHandler)

hexFile = ''
try:
    opts, args = getopt.getopt(sys.argv[1:],"h:",["hexFile="]) #from https://www.tutorialspoint.com/python/python_command_line_arguments.htm.
except:
    print('HexReader.py -h <hexFile>')
    sys.exit(2)
for opt, arg in opts:
    if opt in ("-h", "--hex"):
        hexFile = arg

if hexFile == '':
    print("No hex file specified. Exiting.")
    sys.exit(0)

EndOfFrameMarker = b'\x7E'
timeStart = time()
with open(hexFile, mode='rb') as file:
    inputByte = file.read(1)
    frameBuffer: bytearray = bytearray()
    while inputByte:
        if not keepLooping:
            break
        if inputByte == EndOfFrameMarker:
            storeData(frameBuffer)
            frameBuffer = bytearray() #reset buffer
        else:
            frameBuffer.extend(inputByte)
        inputByte = file.read(1)
endSession()
timeEnd = time()
timeTaken = timeEnd - timeStart
print("Converted to Excel in: " + str(timeTaken) + " seconds")

# hex = open(hexFile)
# hex.readline()
# hex.readline() #Skip first 2 lines as they are not data
# for line in hex.readlines():
#     if not keepLooping:
#         break
#     #framebuffer = "".join(line.split()[:-1]).strip()
#     framebuffer = line.split(" ")[:-1] #removes ESC at end of each frame
#     print(framebuffer)
#     data: bytearray = bytearray()
#     for i in framebuffer:
#         if len(i) == 1:
#             data.extend(bytes.fromhex('0' + i))
#         else:
#             data.extend(bytes.fromhex(i))

#     print(''.join('{:02x}'.format(x) for x in data))
#     storeData(data)

    # if len(framebuffer) % 2 == 1:
    #     temp = framebuffer[len(framebuffer) - 1]
    #     framebuffer = framebuffer[:-1] + '0' + temp
    # print(framebuffer)
    # data = bytearray.fromhex(framebuffer)
    # storeData(data)

print("End")