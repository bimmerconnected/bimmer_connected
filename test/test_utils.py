"""Tests for utils."""
import datetime
import os
import time
from unittest import mock

import pytest
import time_machine

from bimmer_connected.utils import get_class_property_names, parse_datetime, to_json

from . import RESPONSE_DIR, VIN_G21
from .test_account import get_mocked_account


@pytest.mark.asyncio
async def test_drive_train():
    """Tests available attribute."""
    vehicle = (await get_mocked_account()).get_vehicle(VIN_G21)
    assert [
        "available_attributes",
        "available_state_services",
        "brand",
        "charging_profile",
        "drive_train",
        "drive_train_attributes",
        "has_hv_battery",
        "has_internal_combustion_engine",
        "has_range_extender",
        "has_weekly_planner_service",
        "is_vehicle_tracking_enabled",
        "lsc_type",
        "name",
    ] == get_class_property_names(vehicle)


@time_machine.travel("2011-11-28 21:28:59 +0000", tick=False)
@pytest.mark.asyncio
async def test_to_json():
    """Test serialization to JSON."""
    with mock.patch(
        "bimmer_connected.account.ConnectedDriveAccount.timezone", new_callable=mock.PropertyMock
    ) as mock_timezone:
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

        expected_lines = expected.split("\n")
        actual_lines = to_json(vehicle, indent=4).split("\n")

        for i in range(max(len(expected_lines), len(actual_lines))):
            assert expected_lines[i] == actual_lines[i], f"line {i+1}"

        # assert expected == to_json(vehicle, indent=4)


def test_parse_datetime(caplog):
    """Test datetime parser."""

    dt_with_milliseconds = datetime.datetime(2021, 11, 12, 13, 14, 15, 567000, tzinfo=datetime.timezone.utc)
    dt_without_milliseconds = datetime.datetime(2021, 11, 12, 13, 14, 15, tzinfo=datetime.timezone.utc)

    assert dt_with_milliseconds == parse_datetime("2021-11-12T13:14:15.567Z")

    assert dt_without_milliseconds == parse_datetime("2021-11-12T13:14:15Z")

    unparseable_datetime = "2021-14-12T13:14:15Z"
    assert parse_datetime(unparseable_datetime) is None
    errors = [r for r in caplog.records if r.levelname == "ERROR" and unparseable_datetime in r.message]
    assert len(errors) == 1
