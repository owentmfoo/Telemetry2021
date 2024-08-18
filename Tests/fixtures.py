from datetime import datetime, timezone
from pathlib import PurePath

import pytest

@pytest.fixture(autouse=True)
def run_in_receiver(request, monkeypatch):
    monkeypatch.chdir(request.config.rootdir + "/Receiver")

@pytest.fixture(autouse=True)
def patch_receiver_config(request, monkeypatch):
    dbc_folder = PurePath(request.config.rootdir + "/Tests/data/dbc")
    dbc_files = [
        dbc_folder / "wavesculptor_22.dbc",
        dbc_folder / "MPPT.dbc",
        dbc_folder / "Telemetry.dbc",
        dbc_folder / "Orion.dbc",
    ]
    monkeypatch.setattr("Receiver.receiver_config.dbc_files", dbc_files)


@pytest.fixture(scope="session")
def nrt_bytes(request):
    hex_file = request.config.rootdir + "/Tests/data/NRT.BIN"
    end_of_frame_marker = b"\x7E"
    with open(hex_file, mode="rb") as file:
        input_bytes = file.readlines()
    msgs = bytearray().join(input_bytes).split(end_of_frame_marker)
    return msgs


@pytest.fixture(scope="session")
def mppt_bytes(request):
    hex_file = request.config.rootdir + "/Tests/data/MPPT.BIN"
    end_of_frame_marker = b"\x7E"
    with open(hex_file, mode="rb") as file:
        input_bytes = file.readlines()
    msgs = bytearray().join(input_bytes).split(end_of_frame_marker)
    return msgs
