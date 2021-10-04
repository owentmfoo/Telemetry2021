import  rec2db
import time
from can import Message
"""
replay can messages captured in the SD card for DUEM telemetry
Owen Foo 2021
"""

# an example line
# ESC ID0 ID1 DLC B0 B1 B2 B3 B4 B5 B6 B7 CRC0 CRC1
# 7E 1 11 8 FF 6B A A 0 0 0 0 3E C

def to_byte(sample) -> bytearray:
    sample = sample.split(' ')
    sample = [''.join(sample[1,2])].append(sample[2:11])
    for n,i in enumerate(sample):
        if len(i)%2 != 0:
            sample[n] = '0'+ sample[n]
    sample = ''.join(sample)
    out = bytearray()
    l=[]
    for i in range(len(sample)):
        if i%2 !=0:
            l.append(sample[i-1:i+1])
            out.append(int(sample[i-1:i+1],16))
    return out

if __name__ == "__main__":

    with open('../CAN_record/00000007.TXT', 'r') as dumpfile:
        line = dumpfile.readline() # skip header

        while line:
            line = line.replace('\n', '')
            if line:
                sample = line
                linebt = to_byte(line)
                msg = rec2db.bytes2canmsg(linebt, time.time())
                rec2db.parse_msg(msg)
            line = dumpfile.readline()



