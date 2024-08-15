from typing import Union

import cantools.database
from Receiver.receiver_config import dbc_files

class DbcDecoder:
    def __init__(self, dbc_files=dbc_files):
        database = cantools.database.Database()
        for dbc_file in dbc_files:
            database.add_dbc_file(dbc_file)
        self.database = database

    def decode_can_msg(self, can_id, msg_bytes) -> dict[str, Union[int, float, str, bytes]]:
        decode_msg: dict[str, Union[int, float, str, bytes]]
        message = self.database.get_message_by_frame_id(can_id)
        decode_msg = message.decode(msg_bytes)

        # convert back to bytes for backwards compatibility
        if can_id == 248:
            decode_msg["GpsLat"] = decode_msg["GpsLat"].to_bytes(1, "little")
        elif can_id == 249:
            decode_msg["GpsLon"] = decode_msg["GpsLon"].to_bytes(1, "little")
        return decode_msg