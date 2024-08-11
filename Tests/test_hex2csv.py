from datetime import timezone, datetime
import pytest


@pytest.fixture(autouse=True)
def run_in_receiver(request, monkeypatch):
    monkeypatch.chdir(request.config.rootdir + "/Receiver")

def test_hex2csv(monkeypatch, tmp_path, run_in_receiver):
    # arrange
    monkeypatch.setattr("Receiver.receiver_config.configFile",
                        "../Tests/data/CANBusConfig.xlsm")
    monkeypatch.setattr("Receiver.telemetryParser2.lastGPSTime",
                        datetime(year=1970, month=1, day=1, hour=3, minute=0,
                                 second=0, tzinfo=timezone.utc))
    from Receiver.hex2csv import hex2csv

    # act
    hex2csv("../Tests/data/NRT.BIN", f"{tmp_path}/output.csv", "w")

    # assert
    with open(f"{tmp_path}/output.csv") as f1:
        with open("../Tests/data/NRT.csv") as f2:
            f1lines = f1.readlines()
            f2lines = f2.readlines()
            assert f1lines == f2lines


def test_hex2csv2(monkeypatch, tmp_path, run_in_receiver):
    # arrange
    monkeypatch.setattr("Receiver.receiver_config.configFile",
                        "../Tests/data/CANBusConfig.xlsm")
    monkeypatch.setattr("Receiver.telemetryParser2.lastGPSTime",
                        datetime(year=1970, month=1, day=1, hour=3, minute=0,
                                 second=0, tzinfo=timezone.utc))
    from Receiver.hex2csv import hex2csv

    # act
    hex2csv("../Tests/data/MPPT.BIN", f"{tmp_path}/output.csv", "w")

    # assert
    with open(f"{tmp_path}/output.csv") as f1:
        with open("../Tests/data/MPPT.csv") as f2:
            f1lines = f1.readlines()
            f2lines = f2.readlines()
            assert f1lines == f2lines