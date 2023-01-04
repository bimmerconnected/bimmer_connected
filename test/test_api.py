"""Tests for API that are not covered by other tests."""
import json

import httpx
import pytest

from bimmer_connected.account import MyBMWAccount
from bimmer_connected.api.regions import get_region_from_name, valid_regions
from bimmer_connected.api.utils import anonymize_data
from bimmer_connected.utils import log_response_store_to_file

from . import RESPONSE_DIR, TEST_PASSWORD, TEST_REGION, TEST_USERNAME, get_fingerprint_count, load_response
from .test_account import account_mock


def test_valid_regions():
    """Test valid regions."""
    assert ["north_america", "china", "rest_of_world"] == valid_regions()


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
            {"vin": "WBA000000SECRET01"},
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
async def test_storing_fingerprints(tmp_path):
    """Test storing fingerprints to file."""
    with account_mock() as mock_api:
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION, log_responses=True)
        await account.get_vehicles()

        mock_api.get("/eadrax-vcs/v4/vehicles/state").respond(
            500, text=load_response(RESPONSE_DIR / "auth" / "auth_error_internal_error.txt")
        )
        with pytest.raises(httpx.HTTPStatusError):
            await account.get_vehicles()

    log_response_store_to_file(account.get_stored_responses(), tmp_path)

    files = list(tmp_path.iterdir())
    json_files = [f for f in files if f.suffix == ".json"]
    txt_files = [f for f in files if f.suffix == ".txt"]

    assert len(json_files) == (get_fingerprint_count() + 1)
    assert len(txt_files) == 1


@pytest.mark.asyncio
async def test_fingerprint_deque():
    """Test storing fingerprints to file."""
    with account_mock() as mock_api:
        account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, TEST_REGION, log_responses=True)
        await account.get_vehicles()
        await account.get_vehicles()

        # More than 10 calls were made, but only last 10 are stored
        assert len([c for c in mock_api.calls if c.request.url.path.startswith("/eadrax-vcs")]) > 10
        assert len(account.get_stored_responses()) == min(2 + get_fingerprint_count() * 2, 10)

        # Stored responses are reset
        account.config.set_log_responses(False)
        assert len(account.get_stored_responses()) == 0

        # No new responses are getting added
        await account.get_vehicles()
        assert len(account.get_stored_responses()) == 0

        # Get responses again
        account.config.set_log_responses(True)
        await account.get_vehicles()
        assert len(account.get_stored_responses()) == min(get_fingerprint_count(), 10)
