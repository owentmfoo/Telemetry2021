from datetime import timezone, datetime
from unittest.mock import MagicMock

import pytest



@pytest.fixture(autouse=True)
def run_in_receiver(request, monkeypatch):
    monkeypatch.chdir(request.config.rootdir + "/Receiver")

def test_store_data_nrt(monkeypatch, tmp_path, run_in_receiver):
    # arrange
    # Create a mock store function
    monkeypatch.setattr("Receiver.receiver_config.configFile",
                        "../Tests/data/CANBusConfig.xlsm")
    mock_store_function = MagicMock()
    monkeypatch.setattr('Receiver.telemetryStorer.storeFunctionList', [mock_store_function])


    from Receiver.telemetry_parser3 import TelemetryParser
    telemetry_parser = TelemetryParser()
    telemetry_parser.last_gps_time = datetime(year=1970, month=1, day=1, hour=3,
                                              minute=0,
                                              second=0, tzinfo=timezone.utc)
    monkeypatch.setattr("Receiver.telemetryStorer.telemetry_parser",
                        telemetry_parser)

    hex_file = "../Tests/data/NRT.BIN"
    end_of_frame_marker = b"\x7E"
    with open(hex_file, mode="rb") as file:
        input_bytes = file.readlines()
    msgs = bytearray().join(input_bytes).split(end_of_frame_marker)

    from Receiver.telemetryStorer import storeData
    # act
    storeData(msgs[20])  # Orion
    mock_store_function.assert_called_with('PackParameters', 'Orion', {'PackCurrent': 0, 'PackInstVoltage': 1305, 'PackSoc': 159, 'RelayState': 32843}, datetime(1970, 1, 1, 3, 0, 1, 880000, tzinfo=timezone.utc), True)

    storeData(msgs[128])  # tritium
    mock_store_function.assert_called_with('SlipSpeedMeasurement', 'Tritium', {'Reserved': 99.99999237060547, 'SlipSpeed': 0.0}, datetime(1970, 1, 1, 3, 0, 3, 579000, tzinfo=timezone.utc), True)

    storeData(msgs[153])  # crc fail
    mock_store_function.assert_called_with('CRCFail', '', {'Data': b'0f00000602085e7a0243000000004872'}, datetime(1970, 1, 1, 3, 0), False)

    storeData(msgs[166])  # status msg
    mock_store_function.assert_called_with('SystemStatusMessages', 'Telemetry', {'Power': 1, 'WritingToSd': 255, 'GpsTimeObtained': 0, 'LoadedConfig': 102, 'Flag': 1, 'Spare1': 0, 'Spare2': 0, 'Spare3': 0}, datetime(1970, 1, 1, 3, 0, 4, 152000, tzinfo=timezone.utc), True)

    storeData(msgs[173])  # drv control
    mock_store_function.assert_called_with('Maxbuscurrent', 'DriverControls', {'Zero': 0.0, 'MaxBusCurrent': 0.23999999463558197}, datetime(1970, 1, 1, 3, 0, 4, 207000, tzinfo=timezone.utc), True)

    # assert
    assert mock_store_function.call_count == 5

def test_store_data_mppt(monkeypatch, tmp_path, run_in_receiver):
    # arrange
    monkeypatch.setattr("Receiver.receiver_config.configFile",
                        "../Tests/data/CANBusConfig.xlsm")
    mock_store_function = MagicMock()
    monkeypatch.setattr('Receiver.telemetryStorer.storeFunctionList', [mock_store_function])


    from Receiver.telemetry_parser3 import TelemetryParser
    telemetry_parser = TelemetryParser()
    telemetry_parser.last_gps_time = datetime(year=1970, month=1, day=1, hour=3,
                                              minute=0,
                                              second=0, tzinfo=timezone.utc)
    monkeypatch.setattr("Receiver.telemetryStorer.telemetry_parser",
                        telemetry_parser)
    hex_file = "../Tests/data/MPPT.BIN"
    end_of_frame_marker = b"\x7E"
    with open(hex_file, mode="rb") as file:
        input_bytes = file.readlines()
    msgs = bytearray().join(input_bytes).split(end_of_frame_marker)

    from Receiver.telemetryStorer import storeData
    # act
    storeData(msgs[20])  # Javed
    mock_store_function.assert_called_with('Javed', 'Mppt', {'VoltageIn': 508, 'CurrentIn': 121, 'VoltageOut': 612, 'AmbientTemperature': 20, 'BatteryVoltageLevelReached': 0, 'OverTemperature': 0, 'NoCharge': 0, 'UnderVoltage': 0}, datetime(1970, 1, 1, 3, 0, 19, tzinfo=timezone.utc), True)

    storeData(msgs[25])  # Woof
    mock_store_function.assert_called_with('Woof', 'Mppt', {'VoltageIn': 450, 'CurrentIn': 121, 'VoltageOut': 614, 'AmbientTemperature': 20, 'BatteryVoltageLevelReached': 0, 'OverTemperature': 0, 'NoCharge': 0, 'UnderVoltage': 0}, datetime(1970, 1, 1, 3, 0, 24, tzinfo=timezone.utc), True)

    storeData(msgs[100])  # crc fail
    mock_store_function.assert_called_with('CRCFail', '', {'Data': b'010007720701d4006d02680f8e72'}, datetime(1970, 1, 1, 3, 0), False)

    # assert
    assert mock_store_function.call_count == 3

