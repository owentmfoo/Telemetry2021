from pathlib import PurePath

import cantools.database

dbc_folder = PurePath("../dbc/")
database = cantools.database.Database()
database.add_dbc_file(dbc_folder/"wavesculptor_22.dbc")
database.add_dbc_file(dbc_folder/"MPPT.dbc")
def decode_can_msg(canId, msgBytes)->dict:
    return database.decode_message(canId, msgBytes)
