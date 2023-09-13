"""Script to calculated the theoretical instantaneous power


"""
import sys
import logging
import pandas as pd
from influxdb import InfluxDBClient, DataFrameClient
# TODO: update path to the path to telemetryStorer.py on the Pi
sys.path.append(r"/Receiver")
from telemetryStorer import influxCredentials

logger = logging.getLogger(__name__)

VEHICLE_MASS = 250
G = 9.81
MOTOR_EFF = 0.95
CRR = 0.004
CDA = 0.1
RHO = 1.225


def calc_incline_power(df):
    df.loc[:, "InclineDrag"] = VEHICLE_MASS * G * df.Incline
    df.loc[:, "InclinePower"] = df.InclineDrag * df.VehicleVelocity


def calc_accel(df):
    """Calculates the acceleration and take a 5s rolling average.
    Assumes that the index is already resampled to 1s.
    """
    df.loc[:, "Accel"] = (
        df.VehicleVelocity.diff().rolling(pd.Timedelta("5s")).mean()
    )


def calc_rolling_power(df):
    df.loc[:, "RollingPower"] = VEHICLE_MASS * CRR * G * df.VehicleVelocity


def calc_drive_power(df):
    df.loc[:, "DriveThrust"] = VEHICLE_MASS * df.Accel
    df.loc[:, "DrivePower"] = (df.DriveThrust * df.VehicleVelocity) / MOTOR_EFF


def calc_aero_power(df):
    # TODO: update when we have wind data
    df.loc[:, "HeadWind"] = df.VehicleVelocity
    df.loc[:, "AeroDrag"] = 0.5 * RHO * CDA * df.HeadWind**2
    df.loc[:, "AeroPower"] = df.AeroDrag * df.HeadWind


def calc_solar_power(df):
    # CAN conversion factor from MPPT datasheet
    df.loc[:, "SolarPower1"] = (
        df.VoltageIn1 * 0.15049 * df.CurrentIn1 * 8.72 * 1e-3
    )
    df.loc[:, "SolarPower2"] = (
        df.VoltageIn2 * 0.15049 * df.CurrentIn2 * 8.72 * 1e-3
    )
    df.loc[:, "SolarPower"] = (
        df.loc[:, "SolarPower1"] + df.loc[:, "SolarPower2"]
    )


def main(
    if_credentials: influxCredentials = influxCredentials(),
) -> None:
    """Get Latitude and Longitude info off the influxdb and maps it to race
    distance. Latitude and Longitude from the GPS are in the for DDMM.MMM so
    this script first converts it back to decimal degrees beforehand. Decoded
    latitude, longitude and mapped race distance are written back to the
    influxdb under the measurement "Calculated"

    Args:
        if_credentials: Credentials for influxDB.
        road_file_path: File path to road file.

    Returns:
        None
    """
    logger.info("Live power script started.")

    # Read from influx
    influx_client = InfluxDBClient(
        host=if_credentials.host,
        port=if_credentials.port,
        username=if_credentials.username,
        password=if_credentials.password,
        database=if_credentials.db,
    )

    influx_df_client = DataFrameClient(
        host=if_credentials.host,
        port=if_credentials.port,
        username=if_credentials.username,
        password=if_credentials.password,
        database=if_credentials.db,
    )
    # TODO: query wind data as well when it is integrated with Influx.
    query_where = (
        'SELECT "VehicleVelocity","Incline","VoltageIn","CurrentIn","VoltageIn1","CurrentIn1","VoltageIn2","CurrentIn2"'
        'FROM "Tritium/Velocity","Calculated Parameters","MpptWoof/Mppt","MpptJaved/Mppt"'
        "WHERE (time > now() - 180d) ORDER BY time DESC LIMIT 10"
    )

    ifdfq = influx_df_client.query(query_where)
    logger.info("Influx query successful")

    if ifdfq == {}:
        logger.info("No new points to process.")
        return

    # pandas dataframes are mutable so we need to change it back as we delete
    # and rewrite new points at the end of this.
    ifdfq["MpptJaved/Mppt"].columns = ["VoltageIn1", "CurrentIn1"]
    ifdfq["MpptWoof/Mppt"].columns = ["VoltageIn2", "CurrentIn2"]
    # Reformat the data to a single dataframe and decode
    df = pd.concat([j.copy() for i, j in ifdfq.items()], axis=1)
    ifdfq["MpptJaved/Mppt"].columns = ["VoltageIn", "CurrentIn"]
    ifdfq["MpptWoof/Mppt"].columns = ["VoltageIn", "CurrentIn"]

    df = (
        df.resample("1s")
        .mean(numeric_only=True)
        .dropna(how="all", axis=1)
        .interpolate()
    )

    # Calculate
    calc_accel(df)
    calc_drive_power(df)
    calc_incline_power(df)
    calc_rolling_power(df)
    calc_aero_power(df)
    calc_solar_power(df)

    logger.info("Calculations complete.")
    # Write to influx
    # write mapped distance
    influx_df_client.write_points(
        df,
        "Live Power",
        {"live_power": True, "power": True},
        protocol="line",
        batch_size=5000,
    )

    # # It takes a long time to overwrite all these data so we are just gonna
    # #  process the latest n datapoint as an alternative.
    # # add tag to processed data
    # for measurement, measurement_df in ifdfq.items():
    #     influx_df_client.write_points(
    #         measurement_df,
    #         measurement,
    #         tags={"live_power": True},
    #         protocol="line",
    #         batch_size=5000,
    #     )
    #     influx_client.delete_series(
    #         measurement=measurement, tags={"live_power": ""}
    #     )

    logger.info("All data written to influx.")

    influx_df_client.close()
    influx_client.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,  # Set the root logger's level
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Add a handler for the root logger
    )

    main()
