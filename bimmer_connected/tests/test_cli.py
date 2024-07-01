import json
import tempfile
from pathlib import Path

import pytest
from cli_test_helpers import ArgvContext, shell

import bimmer_connected.cli

from . import get_fingerprint_count

ARGS_USER_PW_REGION = ["myuser", "mypassword", "rest_of_world"]
FIXTURE_CLI_HELP = "A simple executable to use and test the library."


def test_run_entrypoint():
    """Test if the entrypoint is installed correctly."""
    result = shell("bimmerconnected --help")

    assert FIXTURE_CLI_HELP in result.stdout
    assert result.exit_code == 0


def test_run_module():
    """Test if the module can be run as a python module."""
    result = shell("python -m bimmer_connected.cli --help")

    assert FIXTURE_CLI_HELP in result.stdout
    assert result.exit_code == 0


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.parametrize(
    ("vin", "expected_count"),
    [
        ("WBA00000000000F31", 1),
        ("WBA00000000000F31,WBA00000000DEMO03", 0),
        ("WBA00000000000Z99", 0),
    ],
)
def test_status_json_filtered(capsys: pytest.CaptureFixture, vin, expected_count):
    """Test the status command JSON output filtered by VIN."""

    with ArgvContext("bimmerconnected", "status", "-j", "-v", vin, *ARGS_USER_PW_REGION):
        try:
            bimmer_connected.cli.main()
        except SystemExit:
            pass
    result = capsys.readouterr()

    if expected_count == 1:
        result_json = json.loads(result.out)
        assert isinstance(result_json, dict)
        assert result_json["vin"] == vin
    else:
        assert "Error: Could not find vehicle" in result.err


@pytest.mark.usefixtures("bmw_fixture")
def test_status_json_unfiltered(capsys: pytest.CaptureFixture):
    """Test the status command JSON output filtered by VIN."""

    with ArgvContext("bimmerconnected", "status", "-j", *ARGS_USER_PW_REGION):
        bimmer_connected.cli.main()
    result = capsys.readouterr()

    result_json = json.loads(result.out)
    assert isinstance(result_json, list)
    assert len(result_json) == get_fingerprint_count("states")


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.parametrize(
    ("vin", "expected_count"),
    [
        ("WBA00000000000F31", 1),
        ("WBA00000000000F31,WBA00000000DEMO03", 0),
        ("WBA00000000000Z99", 0),
    ],
)
def test_status_filtered(capsys: pytest.CaptureFixture, vin, expected_count):
    """Test the status command text output filtered by VIN."""

    with ArgvContext("bimmerconnected", "status", "-v", vin, *ARGS_USER_PW_REGION):
        try:
            bimmer_connected.cli.main()
        except SystemExit:
            pass
    result = capsys.readouterr()

    assert f"Found {get_fingerprint_count('states')} vehicles" in result.out

    if expected_count == 1:
        assert f"VIN: {vin}" in result.out
        assert result.out.count("VIN: ") == expected_count
    else:
        assert result.out.count("VIN: ") == expected_count


@pytest.mark.usefixtures("bmw_fixture")
def test_status_unfiltered(capsys: pytest.CaptureFixture):
    """Test the status command text output filtered by VIN."""

    with ArgvContext("bimmerconnected", "status", *ARGS_USER_PW_REGION):
        bimmer_connected.cli.main()
    result = capsys.readouterr()

    assert f"Found {get_fingerprint_count('states')} vehicles" in result.out
    assert result.out.count("VIN: ") == get_fingerprint_count("states")


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.usefixtures("bmw_log_all_responses")
def test_fingerprint(capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch):
    """Test the fingerprint command."""

    with tempfile.TemporaryDirectory() as tmpdirname:
        tmp_path = Path(tmpdirname)
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        with ArgvContext("bimmerconnected", "fingerprint", *ARGS_USER_PW_REGION):
            bimmer_connected.cli.main()
        result = capsys.readouterr()

        assert "fingerprint of the vehicles written to" in result.out

        files = list(tmp_path.rglob("*"))
        json_files = [f for f in files if f.suffix == ".json"]
        txt_files = [f for f in files if f.suffix == ".txt"]

        assert len(json_files) == (
            get_fingerprint_count("vehicles")
            + get_fingerprint_count("profiles")
            + get_fingerprint_count("states")
            + get_fingerprint_count("charging_settings")
        )
        assert len(txt_files) == 0
