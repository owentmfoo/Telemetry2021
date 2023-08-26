"""Script to upload solarsim to Influx

This is a stand alone script independent from the rest of the receiver scripts.
This can be run from any client that have connection to the influx database (on
the same LAN)

To install the required packages:
`pip install -r requirement.txt`

"""
import logging
from typing import NamedTuple
import json
from tqdm import tqdm
import pandas as pd
from influxdb import InfluxDBClient
import S5.Tecplot as tp

logging.getLogger().setLevel(logging.INFO)


class InfluxCredentials(NamedTuple):  # pylint: disable=missing-class-docstring
    # influx configuration - edit these
    username: str = "admin"
    password: str = "password"
    db: str = "test"  # "PalaceGreen_2022"
    host: str = "localhost"
    port: int = 8086
    enabled: bool = True


def write_row(row: pd.Series, influx_client: InfluxDBClient) -> None:
    """Write a set of points all with the same timestamp to influx.

    Args:
        row: Set of points to write to influx. Series name should be
            pd.TimeStamp and specifies the timestamp the data should be
            associated with. Series index will correspond to field names in
            influx.
        influx_client: Credentials to connect to influx.


    Returns:
        None
    """
    if not isinstance(row.name, pd.Timestamp):
        raise TypeError("Series name must be pd.Timestamp.")
    # format as the influx line protocol
    # https://docs.influxdata.com/influxdb/v2.7/reference/syntax/line-protocol/
    body = [
        {
            "measurement": "SolarSim",
            "fields": json.loads(row.to_json()),
            "time": row.name.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            # dictionary of all fields and corresponding values in CAN message
        }
    ]
    influx_success = influx_client.write_points(
        body, time_precision="ms", protocol="json"
    )  # Write data and check if successful
    if influx_success is False:
        logging.warning(
            "Error writing to Influx for %s", row.name.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        )


def upload_solarsim(
    history: pd.DataFrame, if_credentials: InfluxCredentials = InfluxCredentials()
) -> None:
    """Uploads SolarSim data to Influx.

    SolarSim data should be in the form of a DataFrame with a DatetimeIndex.
    The time will be assumed to be Darwin time unless specified. To localise the
    DatetimeIndex, use `df.tz_localize(timezone)`.
    Args:
        history: DataFrame with timezoned index of data to add to influx.
        if_credentials: Credentials to connect to influx.

    Returns:
        None
    """
    influx_client = InfluxDBClient(
        host=if_credentials.host,
        port=if_credentials.port,
        username=if_credentials.username,
        password=if_credentials.password,
        database=if_credentials.db,
    )
    if not isinstance(history.index, pd.DatetimeIndex):
        raise TypeError("Input DataFrame Index must be DatetimeIndex.")
    if history.index.tz is None:
        logging.warning("DataFrame Index is not tz localised. Assuming Darwin tz")
        history = history.tz_localize("Australia/Darwin")
    for _, row in tqdm(history.iterrows()):
        write_row(row, influx_client)
    influx_client.close()


def clear_solarsim(if_credentials: InfluxCredentials = InfluxCredentials()):
    """Clears all datapoints associated to the measurement SolarSim.

    Args:
        if_credentials: Credentials to connect to influx.

    Returns:
        None
    """
    influx_client = InfluxDBClient(
        host=if_credentials.host,
        port=if_credentials.port,
        username=if_credentials.username,
        password=if_credentials.password,
        database=if_credentials.db,
    )
    query = "DELETE FROM SolarSim"

    influx_client.query(query)
    influx_client.close()


if __name__ == "__main__":
    # TODO: edit these before running the script  # pylint: disable=fixme
    # path the the history file
    path_to_SSHistory = r"D:\path\to\History.dat"  # pylint: disable=invalid-name

    # date that corresponds to Day 1 of the history file e.g. 20231021
    start_date = "20230826"  # pylint: disable=invalid-name

    # timezone the hours the history file is in e.g. "Australia/Darwin" or "UTC"
    tz = "Australia/Darwin"  # pylint: disable=invalid-name

    solarsim = tp.SSHistory(path_to_SSHistory)
    solarsim.add_timestamp(startday=start_date)
    solarsim.data.set_index("DateTime", inplace=True)
    solarsim.data = solarsim.data.tz_localize(tz=tz)
    upload_solarsim(solarsim.data)
