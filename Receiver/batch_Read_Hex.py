"""Utility script to read multiple bin files

It obtains a list of bin files via regex and runs the hex2 script for the list
of bin files.
"""

import logging
import subprocess as sp
import os
import re
from time import time

timeStart = time()
# TODO: set the to the folder containing all the bin files
bin_folder=r'E:\2023Dunsfold2'
# TODO: set regex pattern to filter all the interested bin files
regex_pattern = "231018[0-9]{2}\.BIN"

dir = os.listdir(bin_folder)

vaild_list = []
for file in dir:
    mtch = re.match(regex_pattern, file)
    if mtch is not None:
        vaild_list.append(mtch.group(0))
        print(mtch.group(0))

for file in vaild_list:
    # TODO: uncomment as appropriate
    # sp.run(fr"python HexReader.py -h E:\2023Dunsfold2\{file}")
    sp.run(fr"python hex2influx.py -i E:\2023Dunsfold2\{file}")


timeEnd = time()
timeTaken = timeEnd - timeStart
print(f'\n All files converted in {timeTaken} seconds.')