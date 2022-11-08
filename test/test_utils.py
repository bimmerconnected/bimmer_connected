"""Tests for utils."""
import datetime
import json

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo  # type: ignore[import, no-redef]

import pytest
import time_machine

from bimmer_connected.models import ValueWithUnit
from bimmer_connected.utils import MyBMWJSONEncoder, get_class_property_names, parse_datetime

from . import VIN_G23
from .test_account import get_mocked_account


@pytest.mark.asyncio
async def test_drive_train():
    """Tests available attribute."""
    vehicle = (await get_mocked_account()).get_vehicle(VIN_G23)
    assert [
        "available_attributes",
        "brand",
        "drive_train",
        "drive_train_attributes",
        "has_combustion_drivetrain",
        "has_electric_drivetrain",
        "has_hv_battery",
        "has_internal_combustion_engine",
        "has_range_extender",
        "has_weekly_planner_service",
        "is_charging_plan_supported",
        "is_lsc_enabled",
        "is_vehicle_active",
        "is_vehicle_tracking_enabled",
        "lsc_type",
        "mileage",
        "name",
        "timestamp",
        "vin",
    ] == get_class_property_names(vehicle)


def test_parse_datetime(caplog):
    """Test datetime parser."""

    dt_without_milliseconds = datetime.datetime(2021, 11, 12, 13, 14, 15, tzinfo=datetime.timezone.utc)

    assert dt_without_milliseconds == parse_datetime("2021-11-12T13:14:15.567Z")

    assert dt_without_milliseconds == parse_datetime("2021-11-12T13:14:15Z")

    assert dt_without_milliseconds == parse_datetime("2021-11-12T16:14:15+03:00")

    unparseable_datetime = "2021-14-12T13:14:15Z"
    assert parse_datetime(unparseable_datetime) is None
    errors = [r for r in caplog.records if r.levelname == "ERROR" and unparseable_datetime in r.message]
    assert len(errors) == 1


@time_machine.travel(
    datetime.datetime(2011, 11, 28, tzinfo=zoneinfo.ZoneInfo("America/Los_Angeles")),
    tick=False,
)
@pytest.mark.asyncio
async def test_account_timezone():
    """Test the timezone in MyBMWAccount."""
    account = await get_mocked_account()
    assert account.utcdiff == 960


def test_json_encoder():
    """Test the MyBMWJSONEncoder."""
    encoded = json.dumps(
        {
            "datetime": datetime.datetime(2022, 6, 2, 22, 19, 34, 123456),
            "date": datetime.date(2022, 6, 2),
            "value": ValueWithUnit(17, "mi"),
            "list": [
                {
                    "value_int": 1,
                    "value_str": "string",
                },
                zoneinfo.ZoneInfo("America/Los_Angeles"),
            ],
        },
        cls=MyBMWJSONEncoder,
    )

    assert (
        '{"datetime": "2022-06-02T22:19:34.123456", "date": "2022-06-02", "value": [17, "mi"],'
        ' "list": [{"value_int": 1, "value_str": "string"}, "America/Los_Angeles"]}'
    ) == encoded
