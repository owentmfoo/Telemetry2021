import rec2db
import time
from can import Message
"""replay can messages captured in a file"""


def to_byte(sample) -> bytearray:
    sample = sample.split(' ')
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

    with open('../f.csv', 'r') as dumpfile:
        line = dumpfile.readline();
        line = dumpfile.readline()
        line = dumpfile.readline()
        line = dumpfile.readline()
        addset = set()
        while line:
            line = line.replace('\n', '')
            if line:
                sample = line
                linebt = to_byte(line)
                msg = rec2db.bytes2canmsg(linebt, time.time())
                rec2db.parse_msg(msg)
            line = dumpfile.readline()



