"""For batch import of data to influx

Does it in batch instead of by line and will be significantly faster compared to
telemetry Storer

usage:
    `hex2influx.py [-h] -i HEXFILE`
example:
    `python hex2influx.py -i 23071805.BIN`
"""

import argparse
from time import time
from typing import NamedTuple

import tqdm
from influxdb import InfluxDBClient

from Receiver.telemetryParser2 import translateMsg
from datetime import datetime

parser = argparse.ArgumentParser(description="Import hex file to influxdb, "
                                             "configure the influx credentials "
                                             "in the script before running")
parser.add_argument(
    "-i",
    "--hexfile",
    action="store",
    type=str,
    help="Hex file to import",
    required=True,
)

args = parser.parse_args()
# TODO: we can also consider taking a list of bin files?

hexfile = args.hexfile


class influxCredentials(NamedTuple):
    # influx configuration - edit these
    username: str = "admin"
    password: str = "password"
    db: str = "Test22DB"  # "PalaceGreen_2022"
    host: str = "127.0.0.1"
    port: int = 8086
    enabled: bool = True  # Default to true (otherwise i forget and get confused when theres no data in influx)


ifCredentials = influxCredentials()


def hex2influx(hex_file, ) -> None:
    """Convert hex file to influx

    In contrast to telemetryStorer this write up to 5000 CAN messages at a time.
    Requires to be executed in a location that telemetryParser2.py can locate
    the config correctly.

    Args:
        hex_file: hex file path

    Returns:
            None
    """
    end_of_frame_marker = b"\x7E"
    time_start = time()
    with open(hex_file, mode="rb") as file:
        input_bytes = file.readlines()
    msgs = bytearray().join(input_bytes).split(end_of_frame_marker)
    data = list()
    for msg in tqdm.tqdm(msgs, desc=hex_file):
        msg_item, msg_source, msg_body, msg_time, msg_crc_status = translateMsg(
            msg)
        if msg_item == "ID UNRECOGNISED":
            continue
        data.append(
            to_point(msg_item, msg_source, msg_body, msg_time, msg_crc_status))
    influxClient = InfluxDBClient(host=ifCredentials.host,
                                  port=ifCredentials.port,
                                  username=ifCredentials.username,
                                  password=ifCredentials.password,
                                  database=ifCredentials.db)
    influx_success = influxClient.write_points(data, time_precision='ms',
                                               protocol='line', batch_size=5000)
    print(f"Imported to in: {time() - time_start} seconds")


def to_point(msgItem: str, msgSource: str, msgBody: dict, msgTime: datetime,
             msgCRCStatus: bool) -> str:
    """ Convert decoded message to influx line protocol.

    Args:
        msgItem: CAN msg Identifier.
        msgSource: Device Identifier.
        msgBody: key value pair of fields
        msgTime: Time of msg received.
        msgCRCStatus: Passed CRC check

    Returns:
        string for data formatted in influx line protocol
    """
    if not msgCRCStatus:  # CRC failed, message was corrupted. Do not add to database
        # print("CRC FAILED for " + msgSource + "/" + msgItem + " at " + msgTime.strftime("%Y-%m-%d %H:%M:%S"))
        return ''
    point = f'{msgSource}/{msgItem} '
    for key, value in msgBody.items():
        if isinstance(value, bytes):
            value = '"' + str(value, encoding='utf8') + '"'
        point += f'{key}={value},'
    point = point[:-1]
    point += f' {int(msgTime.timestamp() * 1e3)}'  # convert from seconds to ms
    return point


hex2influx(hexfile)
