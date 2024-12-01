import contextlib
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
import respx
import time_machine

import bimmer_connected.cli
from bimmer_connected import __version__ as VERSION

from . import RESPONSE_DIR, get_fingerprint_count, load_response

ARGS_USER_PW_REGION = ["--captcha-token", "P1_eY...", "myuser", "mypassword", "rest_of_world"]
FIXTURE_CLI_HELP = "Connect to MyBMW/MINI API and interact with your vehicle."


def test_run_entrypoint():
    """Test if the entrypoint is installed correctly."""
    result = subprocess.run(["bimmerconnected", "--help"], capture_output=True, text=True)

    assert FIXTURE_CLI_HELP in result.stdout
    assert result.returncode == 0


def test_run_module():
    """Test if the module can be run as a python module."""
    result = subprocess.run(["python", "-m", "bimmer_connected.cli", "--help"], capture_output=True, text=True)

    assert FIXTURE_CLI_HELP in result.stdout
    assert VERSION in result.stdout
    assert result.returncode == 0


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.usefixtures("cli_home_dir")
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

    sys.argv = ["bimmerconnected", "status", "-j", "-v", vin, *ARGS_USER_PW_REGION]
    with contextlib.suppress(SystemExit):
        bimmer_connected.cli.main()
    result = capsys.readouterr()

    if expected_count == 1:
        result_json = json.loads(result.out)
        assert isinstance(result_json, dict)
        assert result_json["vin"] == vin
    else:
        assert "Error: Could not find vehicle" in result.err


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.usefixtures("cli_home_dir")
def test_status_json_unfiltered(capsys: pytest.CaptureFixture):
    """Test the status command JSON output without filtering by VIN."""

    sys.argv = ["bimmerconnected", "status", "-j", *ARGS_USER_PW_REGION]
    bimmer_connected.cli.main()
    result = capsys.readouterr()

    result_json = json.loads(result.out)
    assert isinstance(result_json, list)
    assert len(result_json) == get_fingerprint_count("states")


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.usefixtures("cli_home_dir")
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

    sys.argv = ["bimmerconnected", "status", "-v", vin, *ARGS_USER_PW_REGION]
    with contextlib.suppress(SystemExit):
        bimmer_connected.cli.main()
    result = capsys.readouterr()

    assert f"Found {get_fingerprint_count('states')} vehicles" in result.out

    if expected_count == 1:
        assert f"VIN: {vin}" in result.out
        assert result.out.count("VIN: ") == expected_count
    else:
        assert result.out.count("VIN: ") == expected_count


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.usefixtures("cli_home_dir")
def test_status_unfiltered(capsys: pytest.CaptureFixture):
    """Test the status command text output filtered by VIN."""

    sys.argv = ["bimmerconnected", "status", *ARGS_USER_PW_REGION]
    bimmer_connected.cli.main()
    result = capsys.readouterr()

    assert f"Found {get_fingerprint_count('states')} vehicles" in result.out
    assert result.out.count("VIN: ") == get_fingerprint_count("states")


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.usefixtures("bmw_log_all_responses")
def test_fingerprint(capsys: pytest.CaptureFixture, cli_home_dir: Path):
    """Test the fingerprint command."""

    sys.argv = ["bimmerconnected", "fingerprint", *ARGS_USER_PW_REGION]
    bimmer_connected.cli.main()
    result = capsys.readouterr()

    assert "fingerprint of the vehicles written to" in result.out

    files = list((cli_home_dir / "vehicle_fingerprint").rglob("*"))
    json_files = [f for f in files if f.suffix == ".json"]
    txt_files = [f for f in files if f.suffix == ".txt"]

    assert len(json_files) == (
        get_fingerprint_count("vehicles")
        + get_fingerprint_count("profiles")
        + get_fingerprint_count("states")
        + get_fingerprint_count("charging_settings")
    )
    assert len(txt_files) == 0


@pytest.mark.usefixtures("cli_home_dir")
def test_oauth_store_credentials(cli_home_dir: Path, bmw_fixture: respx.Router):
    """Test storing the oauth credentials."""

    assert (cli_home_dir / ".bimmer_connected.json").exists() is False

    sys.argv = ["bimmerconnected", "status", *ARGS_USER_PW_REGION]
    bimmer_connected.cli.main()

    assert bmw_fixture.routes["token"].call_count == 1
    assert bmw_fixture.routes["vehicles"].calls[0].request.headers["authorization"] == "Bearer some_token_string"

    assert (cli_home_dir / ".bimmer_connected.json").exists() is True
    oauth_storage = json.loads((cli_home_dir / ".bimmer_connected.json").read_text())

    assert set(oauth_storage.keys()) == {"access_token", "refresh_token", "gcid", "session_id", "session_id_timestamp"}


@time_machine.travel("2021-11-28 21:28:59 +0000")
@pytest.mark.usefixtures("cli_home_dir")
def test_oauth_load_credentials(cli_home_dir: Path, bmw_fixture: respx.Router):
    """Test loading and storing the oauth credentials."""

    demo_oauth_data = {
        "access_token": "demo_access_token",
        "refresh_token": "demo_refresh_token",
        "gcid": "demo_gcid",
        "session_id": "demo_session_id",
        "session_id_timestamp": 1638134000,
    }

    (cli_home_dir / ".bimmer_connected.json").write_text(json.dumps(demo_oauth_data))
    assert (cli_home_dir / ".bimmer_connected.json").exists() is True

    sys.argv = ["bimmerconnected", "status", *ARGS_USER_PW_REGION]

    bimmer_connected.cli.main()

    assert bmw_fixture.routes["token"].call_count == 0
    assert bmw_fixture.routes["vehicles"].calls[0].request.headers["authorization"] == "Bearer demo_access_token"
    assert bmw_fixture.routes["vehicles"].calls[0].request.headers["bmw-session-id"] == "demo_session_id"

    assert (cli_home_dir / ".bimmer_connected.json").exists() is True
    oauth_storage = json.loads((cli_home_dir / ".bimmer_connected.json").read_text())

    assert set(oauth_storage.keys()) == {"access_token", "refresh_token", "gcid", "session_id", "session_id_timestamp"}

    # no change as the old tokens are still valid
    assert oauth_storage["refresh_token"] == demo_oauth_data["refresh_token"]
    assert oauth_storage["access_token"] == demo_oauth_data["access_token"]
    assert oauth_storage["gcid"] == demo_oauth_data["gcid"]
    assert oauth_storage["session_id"] == demo_oauth_data["session_id"]


@time_machine.travel("2021-11-28 21:28:59 +0000")
@pytest.mark.usefixtures("cli_home_dir")
def test_oauth_load_credentials_old_session_id(cli_home_dir: Path, bmw_fixture: respx.Router):
    """Test loading and storing the oauth credentials and getting a new session_id."""

    demo_oauth_data = {
        "access_token": "demo_access_token",
        "refresh_token": "demo_refresh_token",
        "gcid": "demo_gcid",
        "session_id": "demo_session_id",
        "session_id_timestamp": 1636838939,  # 2021-11-13 21:28:59 +0000
    }

    (cli_home_dir / ".bimmer_connected.json").write_text(json.dumps(demo_oauth_data))
    assert (cli_home_dir / ".bimmer_connected.json").exists() is True

    sys.argv = ["bimmerconnected", "status", *ARGS_USER_PW_REGION]

    bimmer_connected.cli.main()

    assert (cli_home_dir / ".bimmer_connected.json").exists() is True
    oauth_storage = json.loads((cli_home_dir / ".bimmer_connected.json").read_text())

    # no change as the old tokens are still valid
    assert oauth_storage["refresh_token"] == demo_oauth_data["refresh_token"]
    assert oauth_storage["access_token"] == demo_oauth_data["access_token"]
    assert oauth_storage["gcid"] == demo_oauth_data["gcid"]
    # but we have a new session_id and session_id_timestamp
    assert oauth_storage["session_id"] != demo_oauth_data["session_id"]
    assert oauth_storage["session_id_timestamp"] == pytest.approx(time.time(), abs=5)


@time_machine.travel("2021-11-28 21:28:59 +0000")
@pytest.mark.usefixtures("cli_home_dir")
def test_oauth_store_credentials_on_error(cli_home_dir: Path, bmw_fixture: respx.Router):
    """Test loading and storing the oauth credentials, even if a call errors out."""

    demo_oauth_data = {
        "access_token": "demo_access_token",
        "refresh_token": "demo_refresh_token",
        "gcid": "DUMMY",
        "session_id": "demo_session_id",
        "session_id_timestamp": 1638134000,
    }

    (cli_home_dir / ".bimmer_connected.json").write_text(json.dumps(demo_oauth_data))
    assert (cli_home_dir / ".bimmer_connected.json").exists() is True

    vehicle_routes = bmw_fixture.pop("vehicles")
    bmw_fixture.post("/eadrax-vcs/v5/vehicle-list", name="vehicles").mock(
        side_effect=[
            httpx.Response(401, json=load_response(RESPONSE_DIR / "auth" / "auth_error_wrong_password.json")),
            vehicle_routes.side_effect,  # type: ignore[list-item]
            httpx.Response(500),
        ]
    )

    sys.argv = ["bimmerconnected", "--debug", "status", *ARGS_USER_PW_REGION]
    with pytest.raises(SystemExit):
        bimmer_connected.cli.main()

    assert bmw_fixture.routes["token"].call_count == 1

    # Check that tokens are stored and a new refresh_token is saved
    assert (cli_home_dir / ".bimmer_connected.json").exists() is True
    oauth_storage = json.loads((cli_home_dir / ".bimmer_connected.json").read_text())
    assert oauth_storage["refresh_token"] == "another_token_string"
    assert oauth_storage["access_token"] == "some_token_string"
    assert oauth_storage["gcid"] == demo_oauth_data["gcid"]
    assert oauth_storage["session_id"] == demo_oauth_data["session_id"]


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.usefixtures("cli_home_dir")
@pytest.mark.parametrize(
    ("filepath"),
    [
        (".bimmer_connected.json"),
        ("other-dir/myfile.json"),
    ],
)
def test_oauth_store_credentials_path(cli_home_dir: Path, tmp_path_factory: pytest.TempPathFactory, filepath: str):
    """Test storing the oauth credentials to another file."""

    new_folder = tmp_path_factory.mktemp("specific-path-")

    assert (cli_home_dir / ".bimmer_connected.json").exists() is False
    assert (new_folder / filepath).exists() is False

    sys.argv = [
        "bimmerconnected",
        "--oauth-store",
        str((new_folder / filepath).absolute()),
        "status",
        *ARGS_USER_PW_REGION,
    ]
    bimmer_connected.cli.main()

    assert (cli_home_dir / ".bimmer_connected.json").exists() is False
    assert (new_folder / filepath).exists() is True

    oauth_storage = json.loads((new_folder / filepath).read_text())

    assert set(oauth_storage.keys()) == {"access_token", "refresh_token", "gcid", "session_id", "session_id_timestamp"}


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.usefixtures("cli_home_dir")
def test_oauth_store_credentials_disabled(cli_home_dir: Path):
    """Test NOT storing the oauth credentials."""

    assert (cli_home_dir / ".bimmer_connected.json").exists() is False

    sys.argv = ["bimmerconnected", "--disable-oauth-store", "status", *ARGS_USER_PW_REGION]
    bimmer_connected.cli.main()

    assert (cli_home_dir / ".bimmer_connected.json").exists() is False


@pytest.mark.usefixtures("cli_home_dir")
def test_login_refresh_token(cli_home_dir: Path, bmw_fixture: respx.Router):
    """Test logging in with refresh token."""

    # set up stored tokens
    demo_oauth_data = {
        "access_token": "outdated_access_token",
        "refresh_token": "demo_refresh_token",
        "gcid": "demo_gcid",
    }

    (cli_home_dir / ".bimmer_connected.json").write_text(json.dumps(demo_oauth_data))
    assert (cli_home_dir / ".bimmer_connected.json").exists() is True

    vehicle_routes = bmw_fixture.pop("vehicles")
    bmw_fixture.post("/eadrax-vcs/v5/vehicle-list", name="vehicles").mock(
        side_effect=[
            httpx.Response(401, json=load_response(RESPONSE_DIR / "auth" / "auth_error_wrong_password.json")),
            *[vehicle_routes.side_effect for _ in range(1000)],  # type: ignore[list-item]
        ]
    )

    sys.argv = ["bimmerconnected", "--debug", "status", *ARGS_USER_PW_REGION]
    bimmer_connected.cli.main()

    assert bmw_fixture.routes["token"].call_count == 1
    # TODO: The following doesn't work with MyBMWMockRouter.using = "httpx"
    # Need to wait for a respx update supporting httpx>=0.28.0 natively
    # assert bmw_fixture.routes["vehicles"].calls[0].request.headers["authorization"] == "Bearer outdated_access_token"
    assert bmw_fixture.routes["vehicles"].calls.last.request.headers["authorization"] == "Bearer some_token_string"

    assert (cli_home_dir / ".bimmer_connected.json").exists() is True


@pytest.mark.usefixtures("cli_home_dir")
def test_login_invalid_refresh_token(cli_home_dir: Path, bmw_fixture: respx.Router):
    """Test logging in with an invalid refresh token."""

    # set up stored tokens
    demo_oauth_data = {
        "refresh_token": "invalid_refresh_token",
        "gcid": "demo_gcid",
    }

    (cli_home_dir / ".bimmer_connected.json").write_text(json.dumps(demo_oauth_data))
    assert (cli_home_dir / ".bimmer_connected.json").exists() is True

    bmw_fixture.post("/gcdm/oauth/token", name="token").mock(
        side_effect=[
            httpx.Response(401, json=load_response(RESPONSE_DIR / "auth" / "auth_error_wrong_password.json")),
            *[httpx.Response(200, json=load_response(RESPONSE_DIR / "auth" / "auth_token.json")) for _ in range(1000)],
        ]
    )

    sys.argv = ["bimmerconnected", "status", *ARGS_USER_PW_REGION]
    bimmer_connected.cli.main()

    assert bmw_fixture.routes["token"].call_count == 2
    assert bmw_fixture.routes["authenticate"].call_count == 2
    assert bmw_fixture.routes["vehicles"].calls[0].request.headers["authorization"] == "Bearer some_token_string"

    assert (cli_home_dir / ".bimmer_connected.json").exists() is True


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.usefixtures("cli_home_dir")
def test_captcha_set(capsys: pytest.CaptureFixture):
    """Test login for North America if captcha is given."""

    ARGS_USER_PW_REGION = ["myuser", "mypassword", "north_america"]
    sys.argv = ["bimmerconnected", "status", "-j", "--captcha-token", "SOME_CAPTCHA_TOKEN", *ARGS_USER_PW_REGION]
    bimmer_connected.cli.main()
    result = capsys.readouterr()

    result_json = json.loads(result.out)
    assert isinstance(result_json, list)
    assert len(result_json) == get_fingerprint_count("states")


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.usefixtures("cli_home_dir")
def test_captcha_unavailable(capsys: pytest.CaptureFixture):
    """Test login for North America failing if no captcha token was given."""

    ARGS_USER_PW_REGION = ["myuser", "mypassword", "north_america"]
    sys.argv = ["bimmerconnected", "status", "-j", *ARGS_USER_PW_REGION]
    with contextlib.suppress(SystemExit):
        bimmer_connected.cli.main()
    result = capsys.readouterr()
    assert (
        result.err.strip()
        == "MyBMWCaptchaMissingError: Missing hCaptcha token for login. See https://bimmer-connected.readthedocs.io/en/stable/captcha.html"
    )
