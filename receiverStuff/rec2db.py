import can
import serial
import time
import datetime
import json
# import re
import struct
import numpy as np
from can import Message
from influxdb import InfluxDBClient
import os

json_path = 'recv_conf.json'
serial_port = '/dev/ttyUSB0'  # '/dev/ttyUSB0', '/dev/ttyAMA0'

"""
Database parameters
"""
# influx configuration - edit these
ifuser = "admin"
ifpass = "password"
ifdb = "home"
ifhost = "192.168.0.174"
ifport = 8086
# measurement_name = "system"

ifclient = InfluxDBClient(ifhost, ifport, ifuser, ifpass, ifdb)

"""
FUNCTION DEFINITIONS
"""


def recv_bytes(new_data):
    can_bytes = bytearray()
    can_len = max_frame
    index = 0

    recv_in_progress = False
    start_marker = b'\x7E'

    while ser.in_waiting and not new_data:
        # Proceed only if we have processed the last batch of data
        # Doesn't need to be in code
        this_byte = ser.read()

        if recv_in_progress:
            can_bytes.append(ord(this_byte))  # Store this_byte in can_bytes. Silly conversion to and from byte/int

            index = index + 1

            if index == 3:
                # If we're at the 3rd position, this is the DLC
                # Update can_len with this info, but as an integer
                data_length = ord(this_byte)
                # Remember 2 bytes for ID, 1 for DLC, 2 for CRC:
                can_len = data_length + 2 + 1 + 2

            if index >= can_len:
                # We've reached the end of our 'frame'
                recv_in_progress = False
                # last_can_len = index
                index = 0
                new_data = True

                # Potentially check CRC

                return new_data, can_bytes

        elif this_byte == start_marker:
            # When we spot the start_marker, flip the flag
            recv_in_progress = True

    # If we haven't entered the while loop, make sure we return the correct value
    return new_data, None


def bytes2canmsg(can_bytes, can_timestamp) -> can.Message:
    '''
    :param can_bytes:
    :param can_timestamp:
    :return message: can.Message object
    '''
    can_id = int.from_bytes(can_bytes[0:2], "big")
    can_dlc = can_bytes[2]  # Returns integer value
    can_data = can_bytes[3:3 + can_dlc]  # Returns bytearray
    message = Message(is_extended_id=False, arbitration_id=can_id, data=can_data, timestamp=can_timestamp)
    message.channel = "XBee"
    return message


def parse_msg(message):
    '''
    :param message:
    :return None:
    '''
    with open(json_path) as json_file:  # There is already a global version so just use that
        lookup = json.load(json_file)
        # Convert ID to a string in the form "0xABC1"
        can_id = "0x%0.2X" % message.arbitration_id
        time = datetime.datetime.utcnow()
        if can_id in lookup:

            # Maybe compare apparent size to DLC and error if disagree. Might have to do before otherwise too late
            structure = lookup[can_id][0]["structure"]  # The structure of a message with this id. returns type list
            offset = 0
            ndx = 0  # Not very Pythonic but have an index so we know where we are. Removes issue of multiple identical entries.

            # Go through all the data in the message
            for dataType in structure:  # todo: use enumerate?
                # Send to the right function for the right data
                types = {
                    "float32": up_float,
                    "float32_le": up_float_le,
                    "int32": up_int32,
                    "uint32": up_uint32,
                    "int16": up_int16,
                    "uint16": up_uint16,
                    "int8": up_int8,
                    "uint8": up_uint8,
                    "char": up_char,
                    "char4": up_char4,
                    "mppt_msb": mppt_msb,
                    "mppt_uint10": mppt_uint10, # to be decided
                }
                value, offset = types[dataType](message.data, offset)

                # Find variable name from lookup and append array in appropriate dictionary
                varName = lookup[can_id][0]["fields"][ndx]
                measurement_name = lookup[can_id][0]["source"]
                varLabel = lookup[can_id][0]["labels"][ndx]
                dataSet[varName] = np.append(dataSet[varName], value)

                # datetime.fromtimestamp(*your_timestamp_here*).strftime('%Y-%m-%d')
                # message.timestamp.strftime('%H:%M:%S.%f')
                # ttiimmee = datetime.fromtimestamp(message.timestamp).strftime('%H:%M:%S.%f')
                # ttiimmee = message.timestamp
                # timeVals[varName] = np.append(timeVals[varName], ttiimmee)
                setSize = 2  # Set this form config. Next line keeps data setSize long - ditches oldest value
                # setSize = lookup[can_id][0]["maxnumel"][ndx]
                dataSet[varName] = dataSet[varName][-setSize:]
                # timeVals[varName] = timeVals[varName][-setSize:]

                # Save to txt

                # Save to database
                print(lookup[can_id][0]["source"])

                print(time)

                body = [
                    {
                        "measurement": measurement_name,
                        "time": time,

                        "fields": {
                            varLabel: value,
                        }
                    }
                ]
                # At the moment this writes each time. Might be better to add to the json body. Actually, no - fields might no arrive grouped to the measurement we want but could group as CAN message?

                ndx += 1

                print("Variable name\t: %s" % varName)
                print("Data type\t: %s" % dataType)
                print("Data value\t: %s" % value)
                print("Set offset to\t: %s\n" % offset)

                ifclient.write_points(body)

                # print(body)
                """
                with open('log_rcvd.txt', 'w') as f:
                    f.write(body)
                    f.write('\n')
                """
            return body

        else:
            print("ID %s not found" % can_id)
            body = [
                {
                    "measurement": "Unknown",
                    "time": time,

                    "fields": {
                        ["Unknown"],
                    }
                }
            ]
            return body  # still return the same type of obj


"""
Unpack bytes from CAN messages into appropriate data types
List of arguments for datatypes available at:
    https://docs.python.org/3/library/struct.html#format-characters

At the microcontroller, we the following to split up eg a float.
    float a_float = 12.375
    *(float*)(my_bytes) = a_float;
    canMsg1.data[0] = my_bytes[0];
    canMsg1.data[1] = my_bytes[1];
    canMsg1.data[2] = my_bytes[2];
    canMsg1.data[3] = my_bytes[3];

This transmits: 0x00 0x00 0x46 0x41, hence we use '<f' below to unpack the bytes.
ie. the most significant BYTE is last.
In https://en.wikipedia.org/wiki/Single-precision_floating-point_format#Converting_from_decimal_representation_to_binary32_format
(12.375)_10,float = (41640000)_16

If numbers are looking dodgy, try unpacking from the other way: '>f'

"""


def up_float(data, offset):
    [x] = struct.unpack('>f', data[offset:offset + 4])
    # Could use: struct.unpack_from(format, /, buffer, offset=offset)
    offset += 4
    return x, offset


def up_float_le(data, offset):  # unpack the bytes from the other side
    [x] = struct.unpack('<f', data[offset:offset + 4])
    # Could use: struct.unpack_from(format, /, buffer, offset=offset)
    offset += 4
    return x, offset


def up_int32(data, offset):
    [x] = struct.unpack('>i', data[offset:offset + 4])
    offset += 4
    return x, offset


def up_uint32(data, offset):
    [x] = struct.unpack('>I', data[offset:offset + 4])
    offset += 4
    return x, offset


def up_int16(data, offset):
    [x] = struct.unpack('>h', data[offset:offset + 2])
    offset += 2
    return x, offset


def up_uint16(data, offset):
    [x] = struct.unpack('>H', data[offset:offset + 2])
    offset += 2
    return x, offset


def up_int8(data, offset):
    [x] = struct.unpack('>b', data[offset:offset + 1])
    offset += 1
    return x, offset


def up_uint8(data, offset):
    [x] = struct.unpack('>B', data[offset:offset + 1])
    offset += 1
    return x, offset


def up_char(data, offset):
    [x] = struct.unpack('>c', data[offset:offset + 1])  # Doesn't really do particularly much I don't think...
    offset += 1
    return x, offset


def up_char4(data, offset):
    [a, b, c, d] = struct.unpack('>cccc', data[offset:offset + 4])
    offset += 4
    x = b''.join([a, b, c, d])
    return x, offset


def mppt_msb(data, offset):  # for extracting MPPT msb in the last 2 bit of this byte and the rest is in the next byte.
    x, offset = up_uint8(data, offset)
    x = x % 4  # make sure only extract the last 2 bit ass there might be flags in the first 4 bit.
    return x, offset


def mppt_uint10(data, offset):    # todo: decide what method to unpack MPPT data and function name
    offset -= 1
    if offset < 0:
        raise IndexError(f'Cannot obtain msb from the last byte, current offset is {offset}') # error out of range
        return 0
    x, offset = mppt_msb(data, offset)
    y, offset = up_uint8(data, offset)
    return x*256+y, offset
"""
End of unpacking functions
"""

"""
COMMS SETUP AND DATA STORAGE
"""
# On startup create a numpy array in a dict with each variable name
with open(json_path) as json_file:
    # dataSet = {"varName": "numpy.array"}
    dataSet = {}  # Keep our array of data here
    timeVals = {}  # Corresponding time
    labels = {}  # Line labels
    ylims = {}  # y-limits for the data type... need to think how to use
    lookup = json.load(json_file)
    for can_id in lookup:
        fields = lookup[can_id][0]["fields"]
        ndx = 0  # Where are we? So we can find adjacent data
        for varName in fields:  # can use enumerate if wanted, kept index for beginner readability
            print(varName)
            dataSet[varName] = np.array([0])  # Might be better if empty but numbers go weird?
            timeVals[varName] = np.array([0])
            labels[varName] = lookup[can_id][0]["labels"][ndx]
            # maxnumel - do this in parse_msg() but might be good for xlim
            # ylims[varName] = lookup[can_id][0]["ylims"][ndx]
            ndx += 1
if __name__ == "__main__":
    # ser = serial.Serial(serial_port, 115200)    # If it's not working, check this
    max_frame = 13  # Preset out max entire 'frame' length. Will update with correct value when we get it from the DLC

    # Hopefully waits for influx to wake up at the start
    # print("Waiting 20s")
    # time.sleep(20)
    print("Let's gooo")

    ser = serial.Serial(serial_port, 115200)  # /dev/ttyAMA0

    new_data = False
    # valid_data = False

    # Make a log file to write to - this should be changed so the name updates
    # this has been moved up

    while True:
        new_data, the_bytes = recv_bytes(new_data)

        if new_data:
            # time = datetime.utcnow()
            new_data = False  # Data only stops being new when it's used
            local_can_time = time.time()  # There's some work to be done to align with GPS time
            msg = bytes2canmsg(the_bytes, local_can_time)
            print(msg)
            rec = parse_msg(msg)
            # print(dataSet)

        time.sleep(0.05)
