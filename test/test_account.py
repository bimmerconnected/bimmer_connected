"""Tests for MyBMWAccount."""

import datetime
import logging
from pathlib import Path

try:
    from unittest import mock

    if not hasattr(mock, "AsyncMock"):
        # AsyncMock was only introduced with Python3.8, so we have to use the backported module
        raise ImportError()
except ImportError:
    import mock  # type: ignore[import,no-redef]  # noqa: UP026

import httpx
import pytest
import respx

from bimmer_connected.account import ConnectedDriveAccount, MyBMWAccount
from bimmer_connected.api.authentication import MyBMWAuthentication, MyBMWLoginRetry
from bimmer_connected.api.client import MyBMWClient
from bimmer_connected.api.regions import get_region_from_name
from bimmer_connected.const import ATTR_CAPABILITIES
from bimmer_connected.models import GPSPosition, MyBMWAPIError, MyBMWAuthError, MyBMWQuotaError

from . import (
    RESPONSE_DIR,
    TEST_PASSWORD,
    TEST_REGION,
    TEST_REGION_STRING,
    TEST_USERNAME,
    VIN_G26,
    get_deprecation_warning_count,
    get_fingerprint_count,
    load_response,
)
from .conftest import prepare_account_with_vehicles


@pytest.mark.asyncio
async def test_login_row_na(bmw_fixture: respx.Router):
    """Test the login flow."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name(TEST_REGION_STRING))
    await account.get_vehicles()
    assert account is not None


@pytest.mark.asyncio
async def test_login_refresh_token_row_na_expired(bmw_fixture: respx.Router):
    """Test the login flow using refresh_token."""
    with mock.patch("bimmer_connected.api.authentication.EXPIRES_AT_OFFSET", datetime.timedelta(seconds=30000)):
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name(TEST_REGION_STRING))
        await account.get_vehicles()

        with mock.patch(
            "bimmer_connected.api.authentication.MyBMWAuthentication._refresh_token_row_na",
            wraps=account.config.authentication._refresh_token_row_na,
        ) as mock_listener:
            mock_listener.reset_mock()
            await account.get_vehicles()

            # Should not be called at all, as expiry date is not checked anymore
            assert mock_listener.call_count == 0
            assert account.config.authentication.refresh_token is not None


@pytest.mark.asyncio
async def test_login_refresh_token_row_na_401(bmw_fixture: respx.Router):
    """Test the login flow using refresh_token."""

    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name(TEST_REGION_STRING))
    await account.get_vehicles()

    with mock.patch(
        "bimmer_connected.api.authentication.MyBMWAuthentication._refresh_token_row_na",
        wraps=account.config.authentication._refresh_token_row_na,
    ) as mock_listener:
        bmw_fixture.get("/eadrax-vcs/v4/vehicles/state").mock(
            side_effect=[httpx.Response(401), *([httpx.Response(200, json={ATTR_CAPABILITIES: {}})] * 10)]
        )
        mock_listener.reset_mock()
        await account.get_vehicles()

        assert mock_listener.call_count == 1
        assert account.config.authentication.refresh_token is not None


@pytest.mark.asyncio
async def test_login_refresh_token_row_na_invalid(caplog, bmw_fixture: respx.Router):
    """Test the login flow using refresh_token."""
    bmw_fixture.post("/gcdm/oauth/token").mock(
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
    assert "Unable to get access token using refresh token, falling back to username/password." in debug_messages
    assert "Authenticating with MyBMW flow for North America & Rest of World." in debug_messages


@pytest.mark.asyncio
async def test_login_china(bmw_fixture: respx.Router):
    """Test the login flow for region `china`."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))
    await account.get_vehicles()
    assert account is not None


@pytest.mark.asyncio
async def test_login_refresh_token_china_expired(bmw_fixture: respx.Router):
    """Test the login flow using refresh_token  for region `china`."""
    with mock.patch("bimmer_connected.api.authentication.EXPIRES_AT_OFFSET", datetime.timedelta(seconds=30000)):
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))
        await account.get_vehicles()

        with mock.patch(
            "bimmer_connected.api.authentication.MyBMWAuthentication._refresh_token_china",
            wraps=account.config.authentication._refresh_token_china,
        ) as mock_listener:
            mock_listener.reset_mock()
            await account.get_vehicles()

            # Should not be called at all, as expiry date is not checked anymore
            assert mock_listener.call_count == 0
            assert account.config.authentication.refresh_token is not None


@pytest.mark.asyncio
async def test_login_refresh_token_china_401(bmw_fixture: respx.Router):
    """Test the login flow using refresh_token."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))
    await account.get_vehicles()

    with mock.patch(
        "bimmer_connected.api.authentication.MyBMWAuthentication._refresh_token_china",
        wraps=account.config.authentication._refresh_token_china,
    ) as mock_listener:
        bmw_fixture.get("/eadrax-vcs/v4/vehicles/state").mock(
            side_effect=[httpx.Response(401), *([httpx.Response(200, json={ATTR_CAPABILITIES: {}})] * 10)]
        )
        mock_listener.reset_mock()
        await account.get_vehicles()

        assert mock_listener.call_count == 1
        assert account.config.authentication.refresh_token is not None


@pytest.mark.asyncio
async def test_login_refresh_token_china_invalid(caplog, bmw_fixture: respx.Router):
    """Test the login flow using refresh_token."""
    bmw_fixture.post("/eadrax-coas/v2/oauth/token").mock(
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
    assert "Unable to get access token using refresh token, falling back to username/password." in debug_messages
    assert "Authenticating with MyBMW flow for China." in debug_messages


@pytest.mark.asyncio
async def test_vehicles(bmw_fixture: respx.Router):
    """Test the login flow."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))
    await account.get_vehicles()

    assert account.config.authentication.access_token is not None
    assert get_fingerprint_count() == len(account.vehicles)

    vehicle = account.get_vehicle(VIN_G26)
    assert vehicle is not None
    assert VIN_G26 == vehicle.vin

    assert account.get_vehicle("invalid_vin") is None


@pytest.mark.asyncio
async def test_vehicle_init(bmw_fixture: respx.Router):
    """Test vehicle initialization."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
    with mock.patch(
        "bimmer_connected.account.MyBMWAccount._init_vehicles",
        wraps=account._init_vehicles,
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
async def test_invalid_password(bmw_fixture: respx.Router):
    """Test parsing the results of an invalid password."""
    bmw_fixture.post("/gcdm/oauth/authenticate").respond(
        401, json=load_response(RESPONSE_DIR / "auth" / "auth_error_wrong_password.json")
    )
    with pytest.raises(MyBMWAuthError):
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
        await account.get_vehicles()


@pytest.mark.asyncio
async def test_invalid_password_china(bmw_fixture: respx.Router):
    """Test parsing the results of an invalid password."""
    bmw_fixture.post("/eadrax-coas/v2/login/pwd").respond(
        422, json=load_response(RESPONSE_DIR / "auth" / "auth_cn_login_error.json")
    )
    with pytest.raises(MyBMWAPIError):
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))
        await account.get_vehicles()


@pytest.mark.asyncio
async def test_server_error(bmw_fixture: respx.Router):
    """Test parsing the results of a server error."""
    bmw_fixture.post("/gcdm/oauth/authenticate").respond(
        500, text=load_response(RESPONSE_DIR / "auth" / "auth_error_internal_error.txt")
    )
    with pytest.raises(MyBMWAPIError):
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
        await account.get_vehicles()


@pytest.mark.asyncio
async def test_vehicle_search_case(bmw_fixture: respx.Router):
    """Check if the search for the vehicle by VIN is NOT case sensitive."""
    account = await prepare_account_with_vehicles()

    vin = account.vehicles[1].vin
    assert vin == account.get_vehicle(vin).vin
    assert vin == account.get_vehicle(vin.lower()).vin
    assert vin == account.get_vehicle(vin.upper()).vin


@pytest.mark.asyncio
async def test_get_fingerprints(bmw_fixture: respx.Router):
    """Test getting fingerprints."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION, log_responses=True)
    await account.get_vehicles()

    bmw_fixture.get("/eadrax-vcs/v4/vehicles/state").respond(
        500, text=load_response(RESPONSE_DIR / "auth" / "auth_error_internal_error.txt")
    )
    with pytest.raises(MyBMWAPIError):
        await account.get_vehicles()

    filenames = [Path(f.filename) for f in account.get_stored_responses()]
    json_files = [f for f in filenames if f.suffix == ".json"]
    txt_files = [f for f in filenames if f.suffix == ".txt"]

    assert len(json_files) == (get_fingerprint_count() + 1)
    assert len(txt_files) == 1


@pytest.mark.asyncio
async def test_set_observer_value(bmw_fixture: respx.Router):
    """Test set_observer_position with valid arguments."""
    account = await prepare_account_with_vehicles()

    account.set_observer_position(1.0, 2.0)

    assert account.config.observer_position == GPSPosition(1.0, 2.0)


@pytest.mark.asyncio
async def test_set_observer_not_set(bmw_fixture: respx.Router):
    """Test set_observer_position with no arguments."""
    account = await prepare_account_with_vehicles()

    assert account.config.observer_position is None

    account.set_observer_position(17.99, 179.9)

    assert account.config.observer_position == GPSPosition(17.99, 179.9)


@pytest.mark.asyncio
async def test_set_observer_invalid_values(bmw_fixture: respx.Router):
    """Test set_observer_position with invalid arguments."""
    account = await prepare_account_with_vehicles()

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


@pytest.mark.asyncio
async def test_deprecated_account(caplog, bmw_fixture: respx.Router):
    """Test deprecation warning for ConnectedDriveAccount."""
    account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
    await account.get_vehicles()
    assert account is not None

    assert 1 == len(get_deprecation_warning_count(caplog))


@pytest.mark.asyncio
async def test_refresh_token_getset(bmw_fixture: respx.Router):
    """Test getting/setting the refresh_token and gcid."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
    assert account.refresh_token is None
    await account.get_vehicles()
    assert account.refresh_token == "another_token_string"
    assert account.gcid is None

    account.set_refresh_token("new_refresh_token")
    assert account.refresh_token == "new_refresh_token"
    assert account.gcid is None

    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))
    account.set_refresh_token("new_refresh_token", "dummy_gcid")
    assert account.refresh_token == "new_refresh_token"
    assert account.gcid == "dummy_gcid"
    await account.get_vehicles()
    assert account.refresh_token == "another_token_string"
    assert account.gcid == "DUMMY"


@pytest.mark.asyncio
async def test_429_retry_ok_login(caplog, bmw_fixture: respx.Router):
    """Test the login flow using refresh_token."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

    json_429 = {"statusCode": 429, "message": "Rate limit is exceeded. Try again in 2 seconds."}

    bmw_fixture.get("/eadrax-ucs/v1/presentation/oauth/config").mock(
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
async def test_429_retry_raise_login(caplog, bmw_fixture: respx.Router):
    """Test the login flow using refresh_token."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

    json_429 = {"statusCode": 429, "message": "Rate limit is exceeded. Try again in 2 seconds."}

    bmw_fixture.get("/eadrax-ucs/v1/presentation/oauth/config").mock(return_value=httpx.Response(429, json=json_429))
    caplog.set_level(logging.DEBUG)

    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
        with pytest.raises(MyBMWAPIError):
            await account.get_vehicles()

    log_429 = [
        r
        for r in caplog.records
        if r.module == "authentication" and "seconds due to 429 Too Many Requests" in r.message
    ]
    assert len(log_429) == 3


@pytest.mark.asyncio
async def test_429_retry_ok_vehicles(caplog, bmw_fixture: respx.Router):
    """Test waiting on 429 for vehicles."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

    json_429 = {"statusCode": 429, "message": "Rate limit is exceeded. Try again in 2 seconds."}

    bmw_fixture.get("/eadrax-vcs/v4/vehicles").mock(
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
async def test_429_retry_raise_vehicles(caplog, bmw_fixture: respx.Router):
    """Test waiting on 429 for vehicles and fail if it happens too often."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

    json_429 = {"statusCode": 429, "message": "Rate limit is exceeded. Try again in 2 seconds."}

    bmw_fixture.get("/eadrax-vcs/v4/vehicles").mock(return_value=httpx.Response(429, json=json_429))
    caplog.set_level(logging.DEBUG)

    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
        with pytest.raises(MyBMWQuotaError):
            await account.get_vehicles()

    log_429 = [
        r
        for r in caplog.records
        if r.module == "authentication" and "seconds due to 429 Too Many Requests" in r.message
    ]
    assert len(log_429) == 3


@pytest.mark.asyncio
async def test_403_quota_exceeded_vehicles_usa(caplog, bmw_fixture: respx.Router):
    """Test 403 quota issues for vehicle state and fail if it happens too often."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)
    # get vehicles once
    await account.get_vehicles()

    bmw_fixture.get("/eadrax-vcs/v4/vehicles/state").mock(
        return_value=httpx.Response(
            403,
            json={"statusCode": 403, "message": "Out of call volume quota. Quota will be replenished in 02:12:20."},
        )
    )
    caplog.set_level(logging.DEBUG)

    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
        with pytest.raises(MyBMWQuotaError):
            await account.get_vehicles()

    log_quota = [r for r in caplog.records if "quota" in r.message]
    assert len(log_quota) == 1


@pytest.mark.asyncio
async def test_client_async_only(bmw_fixture: respx.Router):
    """Test that the Authentication providers only work async."""

    with httpx.Client(auth=MyBMWAuthentication(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)) as client:
        with pytest.raises(RuntimeError):
            client.get("/eadrax-ucs/v1/presentation/oauth/config")

    with httpx.Client(auth=MyBMWLoginRetry()) as client:
        with pytest.raises(RuntimeError):
            client.get("/eadrax-ucs/v1/presentation/oauth/config")
