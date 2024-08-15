from pathlib import PurePath
from typing import NamedTuple


# used by all live_calculation scripts
class influxCredentials(NamedTuple):
    username: str = "admin"
    password: str = "password"
    db: str = "Test22DB"
    host: str = "localhost"
    port: int = 8086
    enabled: bool = True


ifCredentials = influxCredentials()

# configFile: str = './CANConfig.xslx' #raspberrypi
configFile: str = "../../CANTranslator/config/CANBusConfig.xlsm"  # testing with windows

dbc_folder = PurePath("../dbc/")
dbc_files = [
    dbc_folder / "wavesculptor_22.dbc",
    dbc_folder / "MPPT.dbc",
    dbc_folder / "Telemetry.dbc",
    dbc_folder / "Orion.dbc",
]
