import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def filter_function(row: pd.Series) -> bool:
    """Filter function to identify the rows that need timestamp recalculation.

    TODO: edit the function as appropriate to select which rows need
        timestamp recalculation.

    Args:
        row: The row in the DataFrame as a pd.Series.
    Returns:
         True if the row needs the timestamp to be recalculated.
    """
    return row.timestamp > pd.Timestamp("20231101", tz="utc")
    # return row.timestamp == pd.Timestamp('200301231100',tz='utc')


def recalculate_timestamps(df: pd.DataFrame):
    """

    df passed in by reference as a mutable object.
    Args:
        df: CSV loaded in with

            >>> df = pd.read_csv(file,
            >>>                  header=0,
            >>>                  names=['timestamp', 'measurement', 'source', 'f1',
            >>>                         'v1', 'f2', 'v2', 'f3', 'v3', 'f4', 'v4',
            >>>                         'f5', 'v5', 'f6', 'v6', 'f7', 'v7', 'f8',
            >>>                         'v8', 'crc', 'delta']
            >>>                 )


    Returns:
        None, the DataFrame passed in will be modified.
    """

    # Each Recording starts when the millis counter reset to 0.
    df.loc[:, "NRecording"] = (df.delta.diff() < 0).cumsum()

    for timei in tqdm(df.NRecording.unique(), disable=True):
        segment = df[df.NRecording == timei].copy()
        if "TimeAndFix" not in df.measurement.unique():
            logger.info(
                "No GPS fix in session, session duration: %i ms",
                df.delta.max() - df.delta.min(),
            )
            continue
        # Use the fist GPS messages to establish the "datum" for delta
        basetime = (
            df[(df.measurement == "TimeAndFix") & (df.NRecording == timei)]
            .sort_values(by="timestamp")
            .iloc[0]
            .timestamp
        )
        basedelta = (
            df[(df.measurement == "TimeAndFix") & (df.NRecording == timei)]
            .sort_values(by="timestamp")
            .iloc[0]
            .delta
        )

        segment.delta = segment.delta - basedelta
        segment.loc[:, "calculatedTimestamp"] = (
            segment.delta.astype("timedelta64[ms]") + basetime
        )

        update_timestamp = segment.apply(filter_function, axis=1)
        maxdelta = segment.loc[~update_timestamp, "delta"].max()
        logger.debug("Statistics of delta used to backwards calculate timestamps.")
        logger.debug(
            segment.loc[
                update_timestamp & (segment.delta < maxdelta), "delta"
            ].describe()
        )

        # only replace those that didn't get the timestamp from the forward pass
        segment.loc[update_timestamp, "timestamp"] = segment[
            update_timestamp
        ].calculatedTimestamp

        logger.info("%i timestamp updated.", update_timestamp.sum())

        # Update the original DataFrame for this recording.
        df.loc[segment.index, "timestamp"] = segment.timestamp
        df.loc[segment.index, "calculatedTimestamp"] = segment.calculatedTimestamp
        df.loc[segment.index, "delta"] = segment.delta

    # print(df.columns)


def assert_timestamps(df_original, file_name):
    """Check if the timestamp at GPS fix corresponds to the GPS time.

    This function takes a copy of the DataFrame and analyses only the GPS
    messages. The logged timestamp of the message are compared to the GPS
    timestamp.
    The GPSDelta is plotted against time to check for potential clock drift
    during the day.
    The GPSDelta is plotted agains the millis value to check if there are any
    correlation.

    Args:
        df_original: The DataFrame to analyse

    Returns:
        None, a copy of the df is taken and processed within the function so the
         original df remains unchanged

    """
    df = df_original[(df_original.measurement == "TimeAndFix")].copy()
    df = df.rename(
        columns={
            "v1": "hour",
            "v2": "minute",
            "v3": "second",
            "v4": "day",
            "v5": "month",
            "v6": "year",
        }
    )
    df = df[df.year != 0]
    df.year += 2000
    ts = pd.to_datetime(
        df[["year", "month", "day", "hour", "minute", "second"]], utc=True
    )
    df.loc[:, "gpstime"] = ts
    df.loc[:, "gpsdelta"] = df.timestamp - df.gpstime
    # df[abs(df.gpsdelta) > pd.Timedelta(1, 's')]
    df.set_index("timestamp", inplace=True)
    import pytz

    tz = pytz.timezone("Australia/Darwin")
    df.index = df.index.tz_convert(tz)

    """
    For CAN messages received before there is a GPS fix, the decoding time is 
    used. This is a viable fallback strategy during the race as time of decoding
    is very close to the logged time.
    However this is not the case when we are processing after the event. 
    We filter out the timestamps where it is out by more than a minute and 
    and analyse them separately. 
    Before recalculation, this is likely to be the messages before a GPS fix and
    there should not be any message with a delta larger than 1 minuter after 
    recalculation. 
    """
    fig, ax = plt.subplots(2, 1, sharex=False, figsize=(15, 15))
    (
        df.loc[abs(df.gpsdelta) > pd.Timedelta(60, "s"), "gpsdelta"].plot(
            title=file_name, ax=ax[0], marker="o"
        )
    )
    ax[0].set_ylabel("gpsdelta (s)")
    (
        df.loc[abs(df.gpsdelta) < pd.Timedelta(60, "s"), "gpsdelta"].plot(
            ax=ax[1], marker="x"
        )
    )
    ax[1].set_ylabel("gpsdelta (s)")
    plt.show()

    fig, ax = plt.subplots(1, 1)
    (
        df.loc[abs(df.gpsdelta) < pd.Timedelta(60, "s"), :].plot(
            x="delta", y="gpsdelta", kind="scatter", ax=ax, title=file_name
        )
    )
    plt.show()
    print()


if __name__ == "__main__":
    files = [rf"E:\WSC2023Data\Day{i}BINs\output.csv" for i in range(1, 7)]

    for file in files:
        # Read in CSV
        raw = pd.read_csv(
            file,
            header=0,
            names=[
                "timestamp",
                "measurement",
                "source",
                "f1",
                "v1",
                "f2",
                "v2",
                "f3",
                "v3",
                "f4",
                "v4",
                "f5",
                "v5",
                "f6",
                "v6",
                "f7",
                "v7",
                "f8",
                "v8",
                "crc",
                "delta",
            ],
        )

        # Remove row that did not pass CRC check
        df = raw[raw["crc"]].copy()
        df.loc[:, "timestamp"] = pd.to_datetime(
            df.timestamp, utc=True, format="%d/%m/%Y %H:%M:%S.%f"
        )

        # assert_timestamps(df, file)
        recalculate_timestamps(df)
        assert_timestamps(df, file)

        df.loc[:, "tdelta"] = df.timestamp - df.calculatedTimestamp
        print(f"Max Delta between recalculated time and telem time for {file}")
        # print(df.tdelta.describe())
        print(np.abs(df.tdelta).max())
        print()
        raw.loc[raw["crc"], :] = df
        df.to_csv(file[:-4] + "_fixed.csv")
