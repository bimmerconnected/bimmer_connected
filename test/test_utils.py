"""Tests for utils."""
import datetime
import json
import os
import time
from unittest import mock

import pytest
import time_machine

from bimmer_connected.utils import MyBMWJSONEncoder, get_class_property_names, parse_datetime

from . import RESPONSE_DIR, VIN_G21, get_deprecation_warning_count
from .test_account import get_mocked_account


@pytest.mark.asyncio
async def test_drive_train():
    """Tests available attribute."""
    vehicle = (await get_mocked_account()).get_vehicle(VIN_G21)
    assert [
        "available_attributes",
        "brand",
        "drive_train",
        "drive_train_attributes",
        "fuel_indicator_count",
        "has_combustion_drivetrain",
        "has_electric_drivetrain",
        "has_hv_battery",
        "has_internal_combustion_engine",
        "has_range_extender",
        "has_range_extender_drivetrain",
        "has_weekly_planner_service",
        "is_charging_plan_supported",
        "is_lsc_enabled",
        "is_vehicle_active",
        "is_vehicle_tracking_enabled",
        "last_update_reason",
        "lsc_type",
        "mileage",
        "name",
        "timestamp",
        "vin",
    ] == get_class_property_names(vehicle)


@time_machine.travel("2011-11-28 21:28:59 +0000", tick=False)
@pytest.mark.asyncio
async def test_to_json(caplog):
    """Test serialization to JSON."""
    with mock.patch("bimmer_connected.account.MyBMWAccount.timezone", new_callable=mock.PropertyMock) as mock_timezone:
        # Force UTC
        os.environ["TZ"] = "UTC"
        time.tzset()
        mock_timezone.return_value = datetime.timezone.utc

        account = await get_mocked_account()
        vehicle = account.get_vehicle(VIN_G21)

        # Unset UTC after vehicle has been loaded
        del os.environ["TZ"]
        time.tzset()

        with open(RESPONSE_DIR / "G21" / "json_export.json", "rb") as file:
            expected = file.read().decode("UTF-8")

        expected_lines = expected.splitlines()
        actual_lines = json.dumps(vehicle, cls=MyBMWJSONEncoder, indent=4).splitlines()

        for i in range(max(len(expected_lines), len(actual_lines))):
            assert expected_lines[i] == actual_lines[i], f"line {i+1}"

        assert len(get_deprecation_warning_count(caplog)) == 0


def test_parse_datetime(caplog):
    """Test datetime parser."""

    dt_without_milliseconds = datetime.datetime(2021, 11, 12, 13, 14, 15)

    assert dt_without_milliseconds == parse_datetime("2021-11-12T13:14:15.567Z")

    assert dt_without_milliseconds == parse_datetime("2021-11-12T13:14:15Z")

    unparseable_datetime = "2021-14-12T13:14:15Z"
    assert parse_datetime(unparseable_datetime) is None
    errors = [r for r in caplog.records if r.levelname == "ERROR" and unparseable_datetime in r.message]
    assert len(errors) == 1
