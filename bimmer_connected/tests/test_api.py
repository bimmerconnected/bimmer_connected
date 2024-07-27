"""Tests for API that are not covered by other tests."""

import json

import httpx
import pytest
import respx

from bimmer_connected.account import MyBMWAccount
from bimmer_connected.api.authentication import get_retry_wait_time
from bimmer_connected.api.regions import get_region_from_name, valid_regions
from bimmer_connected.api.utils import anonymize_data
from bimmer_connected.utils import log_response_store_to_file

from . import (
    RESPONSE_DIR,
    TEST_PASSWORD,
    TEST_REGION,
    TEST_USERNAME,
    VIN_G26,
    get_fingerprint_count,
    load_response,
)


def test_valid_regions():
    """Test valid regions."""
    assert valid_regions() == ["north_america", "china", "rest_of_world"]


def test_unknown_region():
    """Test unknown region."""
    with pytest.raises(ValueError):
        get_region_from_name("unknown")


def test_anonymize_data():
    """Test anonymization function."""
    test_dict = {
        "vin": "WBA000000SECRET01",
        "a sub-dict": {
            "lat": 666,
            "lon": 666,
            "heading": 666,
        },
        "licensePlate": "secret",
        "public": "public_data",
        "a_list": [
            {"vin": "4US000000SECRET01"},
            {
                "lon": 666,
                "public": "more_public_data",
            },
        ],
        "b_list": ["a", "b"],
        "empty_list": [],
    }
    anon_text = json.dumps(anonymize_data(test_dict))
    assert "SECRET" not in anon_text
    assert "secret" not in anon_text
    assert "666" not in anon_text
    assert "public_data" in anon_text
    assert "more_public_data" in anon_text


@pytest.mark.asyncio
async def test_storing_fingerprints(tmp_path, bmw_fixture: respx.Router, bmw_log_all_responses):
    """Test storing fingerprints to file."""

    # We need to remove the existing state route first and add it back later as otherwise our error call is never
    # matched (respx matches by order of routes and we don't replace the existing one)
    state_route = bmw_fixture.routes.pop("state")
    bmw_fixture.get("/eadrax-vcs/v4/vehicles/state", headers={"bmw-vin": VIN_G26}).respond(
        500, text=load_response(RESPONSE_DIR / "auth" / "auth_error_internal_error.txt")
    )
    bmw_fixture.routes.add(state_route, "state")

    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION, log_responses=True)
    await account.get_vehicles()

    log_response_store_to_file(account.get_stored_responses(), tmp_path)

    files = list(tmp_path.iterdir())
    json_files = [f for f in files if f.suffix == ".json"]
    txt_files = [f for f in files if f.suffix == ".txt"]

    assert len(json_files) == (
        get_fingerprint_count("vehicles")
        + get_fingerprint_count("profiles")
        + get_fingerprint_count("states")
        - 1  # state with error 500
        + get_fingerprint_count("charging_settings")
        - 1  # not loaded due to state with error 500
    )
    assert len(txt_files) == 1  # state with error 500


@pytest.mark.asyncio
async def test_fingerprint_deque(monkeypatch: pytest.MonkeyPatch, bmw_fixture: respx.Router):
    """Test storing fingerprints to file."""
    # Prepare Number of good responses

    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION, log_responses=True)
    await account.get_vehicles()
    await account.get_vehicles()

    # More than 10 calls were made, but only last 10 are stored
    assert len([c for c in bmw_fixture.calls if c.request.url.path.startswith("/eadrax-vcs")]) > 10
    assert len(account.get_stored_responses()) == 10

    # Stored responses are reset
    account.config.set_log_responses(False)
    assert len(account.get_stored_responses()) == 0

    # No new responses are getting added
    await account.get_vehicles()
    assert len(account.get_stored_responses()) == 0

    # Get responses again
    account.config.set_log_responses(True)
    await account.get_vehicles()
    assert len(account.get_stored_responses()) == 10


def test_get_retry_wait_time():
    """Test extraction of retry wait time."""

    # Parsing correctly
    r = httpx.Response(429, json={"statusCode": 429, "message": "Rate limit is exceeded. Try again in 1 seconds."})
    assert get_retry_wait_time(r) == 2

    # No number found
    r = httpx.Response(429, json={"statusCode": 429, "message": "Rate limit is exceeded."})
    assert get_retry_wait_time(r) == 4

    # No JSON response
    r = httpx.Response(429, text="Rate limit is exceeded.")
    assert get_retry_wait_time(r) == 4
