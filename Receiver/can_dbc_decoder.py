from pathlib import PurePath

import cantools.database

dbc_folder = PurePath("../dbc/")
database = cantools.database.Database()
database.add_dbc_file(dbc_folder/"wavesculptor_22.dbc")
database.add_dbc_file(dbc_folder/"MPPT.dbc")
database.add_dbc_file(dbc_folder/"Telemetry.dbc")
database.add_dbc_file(dbc_folder/"Orion.dbc")


def decode_can_msg(canId, msgBytes) -> dict:
    decode_msg = database.decode_message(canId, msgBytes)

    # convert back to bytes for backwards compatibility
    if canId == 248:
        decode_msg["GpsLat"] = decode_msg["GpsLat"].to_bytes(1,"little")
    elif canId == 249:
        decode_msg["GpsLon"] = decode_msg["GpsLon"].to_bytes(1,"little")
    return decode_msg
