"""Tests for API that are not covered by other tests."""
import json

import pytest

from bimmer_connected.api.regions import get_region_from_name, valid_regions
from bimmer_connected.api.utils import anonymize_data, log_to_to_file


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
