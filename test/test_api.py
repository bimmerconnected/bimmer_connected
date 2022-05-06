"""Tests for API that are not covered by other tests."""
import datetime
import json
import sys
from unittest import mock

import pytest
from black import asyncio

from bimmer_connected.api.regions import get_region_from_name, valid_regions
from bimmer_connected.api.utils import anonymize_data, log_to_to_file

from .test_account import account_mock, get_account


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
    anon_text = json.dumps(anonymize_data(test_dict))
    assert "secret" not in anon_text
    assert "666" not in anon_text
    assert "public_data" in anon_text
    assert "more_public_data" in anon_text


def test_log_to_file_without_file_name(tmp_path):
    """Test not logging to file if no file name is given."""
    assert log_to_to_file(content=[], logfile_path=tmp_path, logfile_name=None) is None
    assert len(list(tmp_path.iterdir())) == 0


@account_mock()
def test_asyncio_run_lock():
    """Test calling asyncio.run() multiple times."""

    with mock.patch("bimmer_connected.api.authentication.EXPIRES_AT_OFFSET", datetime.timedelta(seconds=30000)):
        account = get_account()
        with mock.patch(
            "bimmer_connected.api.authentication.MyBMWAuthentication._create_or_update_lock",
            wraps=account.mybmw_client_config.authentication._create_or_update_lock,  # pylint: disable=protected-access
        ) as mock_listener:
            mock_listener.reset_mock()

            # Python 3.6 doesn't provide asyncio.run()
            if sys.version_info < (3, 7):
                for _ in range(2):
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(account.get_vehicles())
                    loop.close()
            else:
                asyncio.run(account.get_vehicles())
                asyncio.run(account.get_vehicles())

            assert mock_listener.call_count == 4
