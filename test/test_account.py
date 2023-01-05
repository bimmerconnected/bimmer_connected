"""Tests for MyBMWAccount."""

import datetime
import logging
from pathlib import Path
from typing import Optional

try:
    from unittest import mock

    if not hasattr(mock, "AsyncMock"):
        # AsyncMock was only introduced with Python3.8, so we have to use the backported module
        raise ImportError()
except ImportError:
    import mock  # type: ignore[import,no-redef]

import httpx
import pytest
import respx

from bimmer_connected.account import ConnectedDriveAccount, MyBMWAccount
from bimmer_connected.api.authentication import MyBMWAuthentication, MyBMWLoginRetry
from bimmer_connected.api.client import MyBMWClient
from bimmer_connected.api.regions import get_region_from_name
from bimmer_connected.const import Regions
from bimmer_connected.models import GPSPosition

from . import (
    ALL_FINGERPRINTS,
    ALL_STATES,
    RESPONSE_DIR,
    TEST_PASSWORD,
    TEST_REGION,
    TEST_REGION_STRING,
    TEST_USERNAME,
    VIN_G23,
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
    if len(x_user_agent) == 4:
        brand = x_user_agent[1]
    else:
        raise ValueError("x-user-agent not configured correctly!")

    # Test if given region is valid
    _ = Regions(x_user_agent[3])

    return httpx.Response(200, json=ALL_FINGERPRINTS.get(brand, []))


def vehicle_state_sideeffect(request: httpx.Request) -> httpx.Response:
    """Returns /vehicles response based on x-user-agent."""
    x_user_agent = request.headers.get("x-user-agent", "").split(";")
    assert len(x_user_agent) == 4

    try:
        return httpx.Response(200, json=ALL_STATES[request.headers["bmw-vin"]])
    except KeyError:
        return httpx.Response(404)


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
    router.post("/eadrax-coas/v2/login/pwd").respond(
        200, json=load_response(RESPONSE_DIR / "auth" / "auth_cn_login_pwd.json")
    )
    router.post("/eadrax-coas/v1/oauth/token").respond(
        200, json=load_response(RESPONSE_DIR / "auth" / "auth_token.json")
    )

    # Get all vehicle fingerprints
    router.get("/eadrax-vcs/v4/vehicles").mock(side_effect=vehicles_sideeffect)

    # router.get("/eadrax-vcs/v2/vehicles").mock(side_effect=vehicles_sideeffect)
    router.get("/eadrax-vcs/v4/vehicles/state").mock(side_effect=vehicle_state_sideeffect)

    return router


def get_account(region: Optional[Regions] = None, metric: bool = True):
    """Returns account without token and vehicles (sync)."""
    return MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, region or TEST_REGION, use_metric_units=metric)


async def get_mocked_account(region: Optional[Regions] = None, metric: bool = True):
    """Returns pre-mocked account."""
    with account_mock():
        account = get_account(region, metric)
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
async def test_login_refresh_token_row_na_expired():
    """Test the login flow using refresh_token."""
    with mock.patch("bimmer_connected.api.authentication.EXPIRES_AT_OFFSET", datetime.timedelta(seconds=30000)):
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name(TEST_REGION_STRING))
        await account.get_vehicles()

        with mock.patch(
            "bimmer_connected.api.authentication.MyBMWAuthentication._refresh_token_row_na",
            wraps=account.config.authentication._refresh_token_row_na,  # pylint: disable=protected-access
        ) as mock_listener:
            mock_listener.reset_mock()
            await account.get_vehicles()

            # Should not be called at all, as expiry date is not checked anymore
            assert mock_listener.call_count == 0
            assert account.config.authentication.refresh_token is not None


@pytest.mark.asyncio
async def test_login_refresh_token_row_na_401():
    """Test the login flow using refresh_token."""
    with account_mock() as mock_api:
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name(TEST_REGION_STRING))
        await account.get_vehicles()

        with mock.patch(
            "bimmer_connected.api.authentication.MyBMWAuthentication._refresh_token_row_na",
            wraps=account.config.authentication._refresh_token_row_na,  # pylint: disable=protected-access
        ) as mock_listener:
            mock_api.get("/eadrax-vcs/v4/vehicles/state").mock(
                side_effect=[httpx.Response(401), *([httpx.Response(200, json=[])] * 10)]
            )
            mock_listener.reset_mock()
            await account.get_vehicles()

            assert mock_listener.call_count == 1
            assert account.config.authentication.refresh_token is not None


@pytest.mark.asyncio
async def test_login_refresh_token_row_na_invalid(caplog):
    """Test the login flow using refresh_token."""
    with account_mock() as mock_api:
        mock_api.post("/gcdm/oauth/token").mock(
            side_effect=[
                httpx.Response(400),
                httpx.Response(200, json=load_response(RESPONSE_DIR / "auth" / "auth_token.json")),
            ]
        )

        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name(TEST_REGION_STRING))
        account.set_refresh_token("INVALID")

        caplog.set_level(logging.DEBUG)
        await account.get_vehicles()

        debug_messages = [r.message for r in caplog.records if r.name.startswith("bimmer_connected")]
        assert "Authenticating with refresh token for North America & Rest of World." in debug_messages
        assert "Unable to get access token using refresh token." in debug_messages
        assert "Authenticating with MyBMW flow for North America & Rest of World." in debug_messages


@account_mock()
@pytest.mark.asyncio
async def test_login_china():
    """Test the login flow for region `china`."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))
    await account.get_vehicles()
    assert account is not None


@account_mock()
@pytest.mark.asyncio
async def test_login_refresh_token_china_expired():
    """Test the login flow using refresh_token  for region `china`."""
    with mock.patch("bimmer_connected.api.authentication.EXPIRES_AT_OFFSET", datetime.timedelta(seconds=30000)):
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))
        await account.get_vehicles()

        with mock.patch(
            "bimmer_connected.api.authentication.MyBMWAuthentication._refresh_token_china",
            wraps=account.config.authentication._refresh_token_china,  # pylint: disable=protected-access
        ) as mock_listener:
            mock_listener.reset_mock()
            await account.get_vehicles()

            # Should not be called at all, as expiry date is not checked anymore
            assert mock_listener.call_count == 0
            assert account.config.authentication.refresh_token is not None


@pytest.mark.asyncio
async def test_login_refresh_token_china_401():
    """Test the login flow using refresh_token."""
    with account_mock() as mock_api:
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))
        await account.get_vehicles()

        with mock.patch(
            "bimmer_connected.api.authentication.MyBMWAuthentication._refresh_token_china",
            wraps=account.config.authentication._refresh_token_china,  # pylint: disable=protected-access
        ) as mock_listener:
            mock_api.get("/eadrax-vcs/v4/vehicles/state").mock(
                side_effect=[httpx.Response(401), *([httpx.Response(200, json=[])] * 10)]
            )
            mock_listener.reset_mock()
            await account.get_vehicles()

            assert mock_listener.call_count == 1
            assert account.config.authentication.refresh_token is not None


@pytest.mark.asyncio
async def test_login_refresh_token_china_invalid(caplog):
    """Test the login flow using refresh_token."""
    with account_mock() as mock_api:
        mock_api.post("/eadrax-coas/v1/oauth/token").mock(
            side_effect=[
                httpx.Response(400),
                httpx.Response(200, json=load_response(RESPONSE_DIR / "auth" / "auth_token.json")),
            ]
        )

        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))
        account.set_refresh_token("INVALID")

        caplog.set_level(logging.DEBUG)
        await account.get_vehicles()

        debug_messages = [r.message for r in caplog.records if r.name.startswith("bimmer_connected")]
        assert "Authenticating with refresh token for China." in debug_messages
        assert "Unable to get access token using refresh token." in debug_messages
        assert "Authenticating with MyBMW flow for China." in debug_messages


@account_mock()
@pytest.mark.asyncio
async def test_vehicles():
    """Test the login flow."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))
    await account.get_vehicles()

    assert account.config.authentication.access_token is not None
    assert get_fingerprint_count() == len(account.vehicles)

    vehicle = account.get_vehicle(VIN_G23)
    assert VIN_G23 == vehicle.vin

    assert account.get_vehicle("invalid_vin") is None


@account_mock()
@pytest.mark.asyncio
async def test_vehicle_init():
    """Test vehicle initialization."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
    with mock.patch(
        "bimmer_connected.account.MyBMWAccount._init_vehicles",
        wraps=account._init_vehicles,  # pylint: disable=protected-access
    ) as mock_listener:
        mock_listener.reset_mock()

        # First call on init
        await account.get_vehicles()
        assert len(account.vehicles) == get_fingerprint_count()

        # No call to _init_vehicles()
        await account.get_vehicles()
        assert len(account.vehicles) == get_fingerprint_count()

        # Second, forced call _init_vehicles()
        await account.get_vehicles(force_init=True)
        assert len(account.vehicles) == get_fingerprint_count()

        assert mock_listener.call_count == 2


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
        mock_api.post("/eadrax-coas/v2/login/pwd").respond(
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
async def test_get_fingerprints():
    """Test getting fingerprints."""
    with account_mock() as mock_api:
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION, log_responses=True)
        await account.get_vehicles()

        mock_api.get("/eadrax-vcs/v4/vehicles/state").respond(
            500, text=load_response(RESPONSE_DIR / "auth" / "auth_error_internal_error.txt")
        )
        with pytest.raises(httpx.HTTPStatusError):
            await account.get_vehicles()

    filenames = [Path(f.filename) for f in account.get_stored_responses()]
    json_files = [f for f in filenames if f.suffix == ".json"]
    txt_files = [f for f in filenames if f.suffix == ".txt"]

    assert len(json_files) == (get_fingerprint_count() + 1)
    assert len(txt_files) == 1


@pytest.mark.asyncio
async def test_set_observer_value():
    """Test set_observer_position with valid arguments."""
    account = await get_mocked_account()

    account.set_observer_position(1.0, 2.0)

    assert account.config.observer_position == GPSPosition(1.0, 2.0)


@pytest.mark.asyncio
async def test_set_observer_not_set():
    """Test set_observer_position with no arguments."""
    account = await get_mocked_account()

    assert account.config.observer_position is None

    account.set_observer_position(17.99, 179.9)

    assert account.config.observer_position == GPSPosition(17.99, 179.9)


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


@pytest.mark.asyncio
async def test_set_use_metric_units():
    """Test set_observer_position with no arguments."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
    assert account.config.use_metric_units is True

    metric_client = MyBMWClient(account.config)
    assert metric_client.generate_default_header()["bmw-units-preferences"] == "d=KM;v=L"

    account.set_use_metric_units(False)
    assert account.config.use_metric_units is False
    imperial_client = MyBMWClient(account.config)
    assert imperial_client.generate_default_header()["bmw-units-preferences"] == "d=MI;v=G"

    imperial_account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION, use_metric_units=False)
    assert imperial_account.config.use_metric_units is False
    imperial_client = MyBMWClient(imperial_account.config)
    assert imperial_client.generate_default_header()["bmw-units-preferences"] == "d=MI;v=G"


@account_mock()
@pytest.mark.asyncio
async def test_deprecated_account(caplog):
    """Test deprecation warning for ConnectedDriveAccount."""
    account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
    await account.get_vehicles()
    assert account is not None

    assert 1 == len(get_deprecation_warning_count(caplog))


@account_mock()
@pytest.mark.asyncio
async def test_refresh_token_getset():
    """Test getting/setting the refresh_token."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
    assert account.refresh_token is None
    await account.get_vehicles()
    assert account.refresh_token == "another_token_string"

    account.set_refresh_token("new_refresh_token")
    assert account.refresh_token == "new_refresh_token"


@pytest.mark.asyncio
async def test_429_retry_ok_login(caplog):
    """Test the login flow using refresh_token."""
    with account_mock() as mock_api:
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

        json_429 = {"statusCode": 429, "message": "Rate limit is exceeded. Try again in 2 seconds."}

        mock_api.get("/eadrax-ucs/v1/presentation/oauth/config").mock(
            side_effect=[
                httpx.Response(429, json=json_429),
                httpx.Response(429, json=json_429),
                httpx.Response(200, json=load_response(RESPONSE_DIR / "auth" / "oauth_config.json")),
            ]
        )
        caplog.set_level(logging.DEBUG)

        with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
            await account.get_vehicles()

        log_429 = [
            r
            for r in caplog.records
            if r.module == "authentication" and "seconds due to 429 Too Many Requests" in r.message
        ]
        assert len(log_429) == 2


@pytest.mark.asyncio
async def test_429_retry_raise_login(caplog):
    """Test the login flow using refresh_token."""
    with account_mock() as mock_api:
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

        json_429 = {"statusCode": 429, "message": "Rate limit is exceeded. Try again in 2 seconds."}

        mock_api.get("/eadrax-ucs/v1/presentation/oauth/config").mock(return_value=httpx.Response(429, json=json_429))
        caplog.set_level(logging.DEBUG)

        with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
            with pytest.raises(httpx.HTTPStatusError):
                await account.get_vehicles()

        log_429 = [
            r
            for r in caplog.records
            if r.module == "authentication" and "seconds due to 429 Too Many Requests" in r.message
        ]
        assert len(log_429) == 3


@pytest.mark.asyncio
async def test_429_retry_ok_vehicles(caplog):
    """Test waiting on 429 for vehicles."""
    with account_mock() as mock_api:
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

        json_429 = {"statusCode": 429, "message": "Rate limit is exceeded. Try again in 2 seconds."}

        mock_api.get("/eadrax-vcs/v4/vehicles").mock(
            side_effect=[
                httpx.Response(429, json=json_429),
                httpx.Response(429, json=json_429),
                *[httpx.Response(200, json=[])] * 2,
            ]
        )
        caplog.set_level(logging.DEBUG)

        with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
            await account.get_vehicles()

        log_429 = [
            r
            for r in caplog.records
            if r.module == "authentication" and "seconds due to 429 Too Many Requests" in r.message
        ]
        assert len(log_429) == 2


@pytest.mark.asyncio
async def test_429_retry_raise_vehicles(caplog):
    """Test waiting on 429 for vehicles and fail if it happens too often."""
    with account_mock() as mock_api:
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

        json_429 = {"statusCode": 429, "message": "Rate limit is exceeded. Try again in 2 seconds."}

        mock_api.get("/eadrax-vcs/v4/vehicles").mock(return_value=httpx.Response(429, json=json_429))
        caplog.set_level(logging.DEBUG)

        with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
            with pytest.raises(httpx.HTTPStatusError):
                await account.get_vehicles()

        log_429 = [
            r
            for r in caplog.records
            if r.module == "authentication" and "seconds due to 429 Too Many Requests" in r.message
        ]
        assert len(log_429) == 3


@account_mock()
@pytest.mark.asyncio
async def test_client_async_only():
    """Test that the Authentication providers only work async."""

    with httpx.Client(auth=MyBMWAuthentication(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)) as client:
        with pytest.raises(RuntimeError):
            client.get("/eadrax-ucs/v1/presentation/oauth/config")

    with httpx.Client(auth=MyBMWLoginRetry()) as client:
        with pytest.raises(RuntimeError):
            client.get("/eadrax-ucs/v1/presentation/oauth/config")
