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

#xlsxOutputFile: str = './ExcelOutput/ExcelTest.xlsx' #set equal to '' to switch off xslx output
xlsxOutputFile: str = ''


ifCredentials = influxCredentials()

# configFile: str = './CANConfig.xslx' #raspberrypi
configFile: str = "../../0/config/CANBusConfig.xlsm"  # testing with windows

dbc_folder = PurePath("../0/")
dbc_files = [
    dbc_folder / "wavesculptor_22.dbc",
    dbc_folder / "MPPT.dbc",
    dbc_folder / "Telemetry.dbc",
    dbc_folder / "Orion.dbc",
]
