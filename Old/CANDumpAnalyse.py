import rec2db
import time
from can import Message

printUniqueAdd = True

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
        line = dumpfile.readline()
        line = dumpfile.readline()
        line = dumpfile.readline()
        line = dumpfile.readline()
        addset = set()
        while line:
            line = line.replace('\n', '')
            if line:
                # print(line)
                linelst = line.split(' ')
                # print(line)
                add = tuple(linelst[0:2])
                # print(add)
                 #use set to avoid repeats
                if False: #can address filter
                    #print(line)
                    sample = line
                    linebt = to_byte(line)
                    msg = rec2db.bytes2canmsg(linebt, time.time())
                    rec2db.parse_msg(msg)
                addset.add(add)
            line = dumpfile.readline()
    addlst = list(addset)
    addlst.sort()



    if printUniqueAdd: #print all unique can address
        print('Address', 'DLC')
        for i, j in addlst:
            print(i, j)



