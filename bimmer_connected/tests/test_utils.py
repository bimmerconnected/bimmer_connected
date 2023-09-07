"""Tests for utils."""
import datetime
import json

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo  # type: ignore[import, no-redef]

import pytest
import respx
import time_machine

from bimmer_connected.api.utils import get_capture_position
from bimmer_connected.models import ChargingSettings, ValueWithUnit
from bimmer_connected.utils import MyBMWJSONEncoder, get_class_property_names, parse_datetime

from . import RESPONSE_DIR, VIN_G26, load_response
from .conftest import prepare_account_with_vehicles


@pytest.mark.asyncio
async def test_drive_train(bmw_fixture: respx.Router):
    """Tests available attribute."""
    vehicle = (await prepare_account_with_vehicles()).get_vehicle(VIN_G26)
    assert [
        "available_attributes",
        "brand",
        "drive_train",
        "drive_train_attributes",
        "has_combustion_drivetrain",
        "has_electric_drivetrain",
        "is_charging_plan_supported",
        "is_lsc_enabled",
        "is_remote_charge_start_enabled",
        "is_remote_charge_stop_enabled",
        "is_remote_climate_start_enabled",
        "is_remote_climate_stop_enabled",
        "is_remote_horn_enabled",
        "is_remote_lights_enabled",
        "is_remote_lock_enabled",
        "is_remote_sendpoi_enabled",
        "is_remote_set_ac_limit_enabled",
        "is_remote_set_target_soc_enabled",
        "is_remote_unlock_enabled",
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
async def test_account_timezone(bmw_fixture: respx.Router):
    """Test the timezone in MyBMWAccount."""
    account = await prepare_account_with_vehicles()
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


def test_charging_settings():
    """Test parsing and validation of charging settings."""

    cs = ChargingSettings(chargingTarget=90, acLimitValue=32)
    assert cs.acLimitValue == 32
    assert cs.chargingTarget == 90
    assert cs.dcLoudness is None
    assert cs.isUnlockCableActive is None


def test_get_capture_position():
    """Test the auto get slider captcha position."""
    base64_background_img = load_response(RESPONSE_DIR / "auth" / "auth_slider_captcha.json")["data"]["backGroundImg"]
    position = get_capture_position(base64_background_img)
    assert position == "0.81"
