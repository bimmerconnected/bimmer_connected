"""Tests for MyBMWAccount."""

from typing import Dict, List

import httpx
import pytest
import respx

from bimmer_connected.account import ConnectedDriveAccount, MyBMWAccount
from bimmer_connected.api.authentication import Authentication
from bimmer_connected.api.client import MyBMWClientConfiguration
from bimmer_connected.api.regions import get_region_from_name
from bimmer_connected.vehicle.models import GPSPosition

from . import (
    RESPONSE_DIR,
    TEST_PASSWORD,
    TEST_REGION,
    TEST_REGION_STRING,
    TEST_USERNAME,
    VIN_G21,
    get_deprecation_warning_count,
    get_fingerprint_count,
    load_response,
)


def authenticate_sideeffect(request: httpx.Request) -> httpx.Response:
    """Returns /oauth/authentication response based on request."""
    request_text = request.read().decode("UTF-8")
    if "username" in request_text and "password" in request_text and "grant_type" in request_text:
        return httpx.Response(200, json=load_response(RESPONSE_DIR / "auth" / "authorization_response.json"))
    return httpx.Response(
        302,
        headers={
            "Location": "com.mini.connected://oauth?code=CODE&state=STATE&client_id=CLIENT_ID&nonce=login_nonce",
        },
    )


def vehicles_sideeffect(request: httpx.Request) -> httpx.Response:
    """Returns /vehicles response based on x-user-agent."""
    x_user_agent = request.headers.get("x-user-agent", "").split(";")
    if len(x_user_agent) == 3:
        brand = x_user_agent[1]
    else:
        raise ValueError("x-user-agent not configured correctly!")

    response_vehicles: List[Dict] = []
    files = RESPONSE_DIR.rglob(f"vehicles_v2_{brand}_0.json")
    for file in files:
        response_vehicles.extend(load_response(file))
    return httpx.Response(200, json=response_vehicles)


def account_mock():
    """Returns mocked adapter for auth."""
    router = respx.mock(assert_all_called=False)

    # Login to north_america and rest_of_world
    router.get("/eadrax-ucs/v1/presentation/oauth/config").respond(
        200, json=load_response(RESPONSE_DIR / "auth" / "oauth_config.json")
    )
    router.post("/gcdm/oauth/authenticate").mock(side_effect=authenticate_sideeffect)
    router.post("/gcdm/oauth/token").respond(200, json=load_response(RESPONSE_DIR / "auth" / "auth_token.json"))

    # Login to china
    router.get("/eadrax-coas/v1/cop/publickey").respond(
        200, json=load_response(RESPONSE_DIR / "auth" / "auth_cn_publickey.json")
    )
    router.post("/eadrax-coas/v1/login/pwd").respond(
        200, json=load_response(RESPONSE_DIR / "auth" / "auth_cn_login_pwd.json")
    )

    # Get all vehicle fingerprints
    router.get("/eadrax-vcs/v1/vehicles").mock(side_effect=vehicles_sideeffect)

    return router


def get_account(region=None):
    """Returns account without token and vehicles (sync)."""
    return MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, region or TEST_REGION)


async def get_mocked_account(region=None):
    """Returns pre-mocked account."""
    with account_mock():
        account = get_account(region)
        await account.get_vehicles()
    return account


@account_mock()
@pytest.mark.asyncio
async def test_login_row_na():
    """Test the login flow."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name(TEST_REGION_STRING))
    await account.get_vehicles()
    assert account is not None


@account_mock()
@pytest.mark.asyncio
async def test_login_china():
    """Test raising an error for region `china`."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))
    await account.get_vehicles()
    assert account is not None


@account_mock()
@pytest.mark.asyncio
async def test_vehicles():
    """Test the login flow."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))
    await account.get_vehicles()

    assert account.mybmw_client_config.authentication.token is not None
    assert get_fingerprint_count() == len(account.vehicles)

    vehicle = account.get_vehicle(VIN_G21)
    assert VIN_G21 == vehicle.vin

    assert account.get_vehicle("invalid_vin") is None


@pytest.mark.asyncio
async def test_invalid_password():
    """Test parsing the results of an invalid password."""
    with account_mock() as mock_api:
        mock_api.post("/gcdm/oauth/authenticate").respond(
            401, json=load_response(RESPONSE_DIR / "auth" / "auth_error_wrong_password.json")
        )
        with pytest.raises(httpx.HTTPStatusError):
            account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
            await account.get_vehicles()


@pytest.mark.asyncio
async def test_invalid_password_china():
    """Test parsing the results of an invalid password."""
    with account_mock() as mock_api:
        mock_api.post("/eadrax-coas/v1/login/pwd").respond(
            422, json=load_response(RESPONSE_DIR / "auth" / "auth_cn_login_error.json")
        )
        with pytest.raises(httpx.HTTPStatusError):
            account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))
            await account.get_vehicles()


@pytest.mark.asyncio
async def test_server_error():
    """Test parsing the results of a server error."""
    with account_mock() as mock_api:
        mock_api.post("/gcdm/oauth/authenticate").respond(
            500, text=load_response(RESPONSE_DIR / "auth" / "auth_error_internal_error.txt")
        )
        with pytest.raises(httpx.HTTPStatusError):
            account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
            await account.get_vehicles()


@pytest.mark.asyncio
async def test_vehicle_search_case():
    """Check if the search for the vehicle by VIN is NOT case sensitive."""
    account = await get_mocked_account()

    vin = account.vehicles[1].vin
    assert vin == account.get_vehicle(vin).vin
    assert vin == account.get_vehicle(vin.lower()).vin
    assert vin == account.get_vehicle(vin.upper()).vin


@pytest.mark.asyncio
async def test_storing_fingerprints(tmp_path):
    """Test the login flow."""
    with account_mock() as mock_api:
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION, log_responses=tmp_path)
        await account.get_vehicles()

        mock_api.get("/eadrax-vcs/v1/vehicles").respond(
            500, text=load_response(RESPONSE_DIR / "auth" / "auth_error_internal_error.txt")
        )
        with pytest.raises(httpx.HTTPStatusError):
            await account.get_vehicles()

    files = list(tmp_path.iterdir())
    json_files = [f for f in files if f.suffix == ".json"]
    txt_files = [f for f in files if f.suffix == ".txt"]

    assert len(json_files) == 2
    assert len(txt_files) == 2


@pytest.mark.asyncio
async def test_set_observer_value():
    """Test set_observer_position with valid arguments."""
    account = await get_mocked_account()

    account.set_observer_position(1.0, 2.0)

    assert account.observer_position == GPSPosition(1.0, 2.0)


@pytest.mark.asyncio
async def test_set_observer_not_set():
    """Test set_observer_position with no arguments."""
    account = await get_mocked_account()

    assert account.observer_position is None

    account.set_observer_position(17.99, 179.9)

    assert account.observer_position == GPSPosition(17.99, 179.9)


@pytest.mark.asyncio
async def test_set_observer_invalid_values():
    """Test set_observer_position with invalid arguments."""
    account = await get_mocked_account()

    with pytest.raises(TypeError):
        account.set_observer_position(None, 2.0)

    with pytest.raises(TypeError):
        account.set_observer_position(1.0, None)

    with pytest.raises(TypeError):
        account.set_observer_position(1.0, "16.0")


@account_mock()
@pytest.mark.asyncio
async def test_base_authentication():
    """Test logging in with the Authentication base clas."""
    account = get_account()
    account.mybmw_client_config = MyBMWClientConfiguration(Authentication(TEST_USERNAME, TEST_PASSWORD, TEST_REGION))
    with pytest.raises(NotImplementedError):
        await account.get_vehicles()


@account_mock()
@pytest.mark.asyncio
async def test_deprecated_account(caplog):
    """Test deprecation warning for ConnectedDriveAccount."""
    account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
    await account.get_vehicles()
    assert account is not None

    assert 1 == len(get_deprecation_warning_count(caplog))
