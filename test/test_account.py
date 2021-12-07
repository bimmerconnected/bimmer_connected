"""Tests for ConnectedDriveAccount."""
import json
import unittest

import requests_mock
from requests import HTTPError

from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.country_selector import get_region_from_name

from . import (
    RESPONSE_DIR,
    TEST_PASSWORD,
    TEST_REGION,
    TEST_REGION_STRING,
    TEST_USERNAME,
    VIN_G21,
    get_fingerprint_count,
    load_response,
)


def authenticate_callback(request, context):  # pylint: disable=inconsistent-return-statements
    """Returns /oauth/authentication response based on request."""
    # pylint: disable=protected-access,unused-argument,no-self-use

    if "username" in request.text and "password" in request.text and "grant_type" in request.text:
        return load_response(RESPONSE_DIR / "auth" / "authorization_response.json")
    context.headers = {
        "Location": "com.mini.connected://oauth?code=CODE&state=STATE&client_id=CLIENT_ID&nonce=login_nonce",
    }
    context.status_code = 302


def return_vehicles(request, context):  # pylint: disable=inconsistent-return-statements
    """Returns /vehicles response based on x-user-agent."""
    # pylint: disable=protected-access,unused-argument,no-self-use

    x_user_agent = request._request.headers.get("x-user-agent", "").split(";")
    if len(x_user_agent) == 3:
        brand = x_user_agent[1]
    else:
        raise ValueError("x-user-agent not configured correctly!")

    response_vehicles = []
    files = RESPONSE_DIR.rglob("vehicles_v2_{}_0.json".format(brand))
    for file in files:
        response_vehicles.extend(load_response(file))
    return response_vehicles


def get_base_adapter():
    """Returns mocked adapter for auth."""
    adapter = requests_mock.Adapter()
    adapter.register_uri(
        "GET",
        "/eadrax-ucs/v1/presentation/oauth/config",
        json=load_response(RESPONSE_DIR / "auth" / "oauth_config.json"),
    )
    adapter.register_uri("POST", "/gcdm/oauth/authenticate", json=authenticate_callback)
    adapter.register_uri("POST", "/gcdm/oauth/token", json=load_response(RESPONSE_DIR / "auth" / "auth_token.json"))
    adapter.register_uri("GET", "/eadrax-vcs/v1/vehicles", json=return_vehicles)
    adapter.register_uri(
        "GET", "/eadrax-coas/v1/cop/publickey", json=load_response(RESPONSE_DIR / "auth" / "auth_cn_publickey.json")
    )
    adapter.register_uri(
        "POST", "/eadrax-coas/v1/login/pwd", json=load_response(RESPONSE_DIR / "auth" / "auth_cn_login_pwd.json")
    )
    return adapter


def get_mocked_account(region=None):
    """Returns pre-mocked account."""
    with requests_mock.Mocker(adapter=get_base_adapter()):
        account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, region or TEST_REGION)
    return account


class TestAccount(unittest.TestCase):
    """Tests for ConnectedDriveAccount."""

    def test_login_row_na(self):
        """Test the login flow."""
        with requests_mock.Mocker(adapter=get_base_adapter()):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name(TEST_REGION_STRING))
        self.assertIsNotNone(account)

    def test_login_china(self):
        """Test raising an error for region `china`."""
        with requests_mock.Mocker(adapter=get_base_adapter()):
            account = ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))
        self.assertIsNotNone(account)

    def test_vehicles(self):
        """Test the login flow."""
        account = get_mocked_account()

        self.assertIsNotNone(account._oauth_token)  # pylint: disable=protected-access
        self.assertEqual(get_fingerprint_count(), len(account.vehicles))
        vehicle = account.get_vehicle(VIN_G21)
        self.assertEqual(VIN_G21, vehicle.vin)

        self.assertIsNone(account.get_vehicle("invalid_vin"))

    def test_invalid_password(self):
        """Test parsing the results of an invalid password."""
        with requests_mock.Mocker(adapter=get_base_adapter()) as mock:
            mock.post(
                "/gcdm/oauth/authenticate",
                json=load_response(RESPONSE_DIR / "auth" / "auth_error_wrong_password.json"),
                status_code=401,
            )
            with self.assertRaises(HTTPError):
                ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

    def test_invalid_password_china(self):
        """Test parsing the results of an invalid password."""
        with requests_mock.Mocker(adapter=get_base_adapter()) as mock:
            mock.post(
                "/eadrax-coas/v1/login/pwd",
                json=load_response(RESPONSE_DIR / "auth" / "auth_cn_login_error.json"),
                status_code=422,
            )
            with self.assertRaises(HTTPError):
                ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, get_region_from_name("china"))

    def test_server_error(self):
        """Test parsing the results of a server error."""
        with requests_mock.Mocker(adapter=get_base_adapter()) as mock:
            mock.post(
                "/gcdm/oauth/authenticate",
                text=load_response(RESPONSE_DIR / "auth" / "auth_error_internal_error.txt"),
                status_code=500,
            )
            with self.assertRaises(HTTPError):
                ConnectedDriveAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION)

    def test_anonymize_data(self):
        """Test anonymization function."""
        test_dict = {
            "vin": "secret",
            "a sub-dict": {
                "lat": 666,
                "lon": 666,
                "heading": 666,
            },
            "licensePlate": "secret",
            "public": "public_data",
            "a_list": [
                {"vin": "secret"},
                {
                    "lon": 666,
                    "public": "more_public_data",
                },
            ],
            "b_list": ["a", "b"],
            "empty_list": [],
        }
        anon_text = json.dumps(ConnectedDriveAccount._anonymize_data(test_dict))  # pylint: disable=protected-access
        self.assertNotIn("secret", anon_text)
        self.assertNotIn("666", anon_text)
        self.assertIn("public_data", anon_text)
        self.assertIn("more_public_data", anon_text)

    def test_vehicle_search_case(self):
        """Check if the search for the vehicle by VIN is NOT case sensitive."""
        account = get_mocked_account()

        vin = account.vehicles[1].vin
        self.assertEqual(vin, account.get_vehicle(vin).vin)
        self.assertEqual(vin, account.get_vehicle(vin.lower()).vin)
        self.assertEqual(vin, account.get_vehicle(vin.upper()).vin)

    def test_set_observer_value(self):
        """Test set_observer_position with valid arguments."""
        account = get_mocked_account()

        account.set_observer_position(1.0, 2.0)
        for vehicle in account.vehicles:
            self.assertEqual(vehicle.observer_latitude, 1.0)
            self.assertEqual(vehicle.observer_longitude, 2.0)

    def test_set_observer_not_set(self):
        """Test set_observer_position with no arguments."""
        account = get_mocked_account()

        for vehicle in account.vehicles:
            self.assertIsNone(vehicle.observer_latitude)
            self.assertIsNone(vehicle.observer_longitude)

        account.set_observer_position(17.99, 179.9)

        for vehicle in account.vehicles:
            self.assertEqual(vehicle.observer_latitude, 17.99)
            self.assertEqual(vehicle.observer_longitude, 179.9)

    def test_set_observer_some_none(self):
        """Test set_observer_position with invalid arguments."""
        account = get_mocked_account()

        with self.assertRaises(ValueError):
            account.set_observer_position(None, 2.0)

        with self.assertRaises(ValueError):
            account.set_observer_position(1.0, None)
