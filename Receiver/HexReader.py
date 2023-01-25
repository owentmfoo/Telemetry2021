import os
#import struct
import sys, getopt
from telemetryStorer import storeData
import atexit
import signal

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
    print('Translator.py -h <hexFile>')
    sys.exit(2)
for opt, arg in opts:
    if opt in ("-h", "--hex"):
        hexFile = arg

if hexFile == '':
    print("No hex file specified. Exiting.")
    sys.exit(0)

hex = open(hexFile)
hex.readline()
hex.readline() #Skip first 2 lines as they are not data
for line in hex.readlines():
    if not keepLooping:
        break
    #framebuffer = "".join(line.split()[:-1]).strip()
    framebuffer = line.split(" ")[:-1] #removes ESC at end of each frame
    print(framebuffer)
    data: bytearray = bytearray()
    for i in framebuffer:
        if len(i) == 1:
            data.extend(bytes.fromhex('0' + i))
        else:
            data.extend(bytes.fromhex(i))

    print(''.join('{:02x}'.format(x) for x in data))
    storeData(data)

    # if len(framebuffer) % 2 == 1:
    #     temp = framebuffer[len(framebuffer) - 1]
    #     framebuffer = framebuffer[:-1] + '0' + temp
    # print(framebuffer)
    # data = bytearray.fromhex(framebuffer)
    # storeData(data)

print("End")