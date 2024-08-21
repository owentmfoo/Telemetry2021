import sys
from pathlib import PurePath
from typing import NamedTuple

import pytest
from unittest.mock import MagicMock, call
from datetime import datetime, timezone

from openpyxl import Workbook
from fixtures import nrt_bytes, patch_receiver_config, run_in_receiver


# Mock the Workbook and Worksheet
@pytest.fixture(scope="function")
def mock_xlsx_workbook(monkeypatch, request):
    class influxCredentials(NamedTuple):
        enabled: bool = False

    monkeypatch.setattr("Receiver.receiver_config.ifCredentials", influxCredentials())

    monkeypatch.setattr("Receiver.receiver_config.xlsxOutputFile", "mock.xlsx")

    dbc_folder = PurePath(request.config.rootdir + "/Tests/data/dbc")
    dbc_files = [
        dbc_folder / "wavesculptor_22.dbc",
        dbc_folder / "MPPT.dbc",
        dbc_folder / "Telemetry.dbc",
        dbc_folder / "Orion.dbc",
    ]
    monkeypatch.setattr("Receiver.receiver_config.dbc_files", dbc_files)

    try:
        del sys.modules["Receiver.telemetryStorer"]
    except KeyError:
        pass
    import Receiver.telemetryStorer

    mock_workbook = MagicMock(spec=Workbook)
    mock_worksheet = MagicMock()
    mock_workbook.active = mock_worksheet
    monkeypatch.setattr(Receiver.telemetryStorer, "XlsxOutWorkbook", mock_workbook)
    monkeypatch.setattr(Receiver.telemetryStorer, "XlsxOutWorkSheet", mock_worksheet)
    monkeypatch.setattr(Receiver.telemetryStorer, "XlsxOutRowPointer", 2)
    return mock_workbook, mock_worksheet


def test_data_written_to_xlsx(
    monkeypatch, run_in_receiver, patch_receiver_config, mock_xlsx_workbook, nrt_bytes
):
    # Arrange
    mock_workbook, mock_worksheet = mock_xlsx_workbook
    from Receiver.telemetry_parser3 import TelemetryParser
    import Receiver.telemetryStorer

    telemetry_parser = TelemetryParser()
    telemetry_parser.last_gps_time = datetime(
        year=1970, month=1, day=1, hour=3, minute=0, second=0, tzinfo=timezone.utc
    )
    monkeypatch.setattr(Receiver.telemetryStorer, "telemetry_parser", telemetry_parser)

    # Act
    from Receiver.telemetryStorer import storeData

    storeData(nrt_bytes[20])

    # Assert
    assert mock_worksheet.cell.call_args_list == [
        call(column=1, row=2, value=datetime(1970, 1, 1, 3, 0, 1, 880000)),
        call(column=2, row=2, value=datetime(1970, 1, 1, 3, 0, 1, 880000)),
        call(column=3, row=2, value="Orion"),
        call(column=4, row=2, value="PackParameters"),
        call(column=5, row=2, value="PackCurrent"),
        call(column=6, row=2, value=0),
        call(column=7, row=2, value="PackInstVoltage"),
        call(column=8, row=2, value=1305),
        call(column=9, row=2, value="PackSoc"),
        call(column=10, row=2, value=159),
        call(column=11, row=2, value="RelayState"),
        call(column=12, row=2, value=32843),
        call(column=21, row=2, value=True),
    ]
    mock_workbook.save.assert_called_once_with("mock.xlsx")


def test_xlsx_closed(monkeypatch, mock_xlsx_workbook, nrt_bytes, run_in_receiver):
    # Arrange
    mock_workbook, mock_worksheet = mock_xlsx_workbook
    from Receiver.telemetryStorer import endSession

    # Act
    endSession()

    # Assert
    mock_workbook.save.assert_called_once_with("mock.xlsx")
    mock_workbook.close.assert_called_once_with()
