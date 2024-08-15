from typing import Union

import cantools.database
from Receiver.receiver_config import dbc_files

database = cantools.database.Database()
for dbc_file in dbc_files:
    database.add_dbc_file(dbc_file)


def decode_can_msg(canId, msgBytes) -> dict[str, Union[int, float, str, bytes]]:
    decode_msg: dict[str, Union[int, float, str, bytes]]
    decode_msg = database.decode_message(canId, msgBytes)

    # convert back to bytes for backwards compatibility
    if canId == 248:
        decode_msg["GpsLat"] = decode_msg["GpsLat"].to_bytes(1, "little")
    elif canId == 249:
        decode_msg["GpsLon"] = decode_msg["GpsLon"].to_bytes(1, "little")
    return decode_msg
