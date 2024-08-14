import cantools.database

tritium_dbc = cantools.database.load_file("../dbc/wavesculptor_22.dbc")

def decode_can_msg(canId, msgBytes)->dict:
    return tritium_dbc.decode_message(canId, msgBytes)
