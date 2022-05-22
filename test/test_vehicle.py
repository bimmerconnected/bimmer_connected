"""Tests for MyBMWVehicle."""
import pytest

from bimmer_connected.const import CarBrands
from bimmer_connected.vehicle import DriveTrainType, VehicleViewDirection
from bimmer_connected.vehicle.models import GPSPosition, StrEnum, VehicleDataBase

from . import (
    VIN_F11,
    VIN_F31,
    VIN_F35,
    VIN_F44,
    VIN_F45,
    VIN_F48,
    VIN_G01,
    VIN_G05,
    VIN_G08,
    VIN_G21,
    VIN_G23,
    VIN_G30,
    VIN_I01_NOREX,
    VIN_I01_REX,
    get_deprecation_warning_count,
)
from .test_account import account_mock, get_mocked_account

ATTRIBUTE_MAPPING = {
    "remainingFuel": "remaining_fuel",
    "position": "gps_position",
    "cbsData": "condition_based_services",
    "checkControlMessages": "check_control_messages",
    "doorLockState": "door_lock_state",
    "updateReason": "last_update_reason",
    "chargingLevelHv": "charging_level_hv",
    "chargingStatus": "charging_status",
    "maxRangeElectric": "max_range_electric",
    "remainingRangeElectric": "remaining_range_electric",
    "parkingLight": "parking_lights",
    "remainingRangeFuel": "remaining_range_fuel",
    "updateTime": "timestamp",
    "chargingTimeRemaining": "charging_time_remaining",
}


@pytest.mark.asyncio
async def test_drive_train(caplog):
    """Tests around drive_train attribute."""
    vehicle = (await get_mocked_account()).get_vehicle(VIN_G21)
    assert DriveTrainType.PLUGIN_HYBRID == vehicle.drive_train

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_parsing_attributes(caplog):
    """Test parsing different attributes of the vehicle."""
    account = await get_mocked_account()

    for vehicle in account.vehicles:
        print(vehicle.name)
        assert vehicle.drive_train is not None
        assert vehicle.name is not None
        assert isinstance(vehicle.brand, CarBrands)
        assert vehicle.has_combustion_drivetrain is not None
        assert vehicle.has_electric_drivetrain is not None
        assert vehicle.drive_train_attributes is not None
        assert vehicle.is_charging_plan_supported is not None

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_drive_train_attributes(caplog):
    """Test parsing different attributes of the vehicle."""
    account = await get_mocked_account()

    vehicle_drivetrains = {
        VIN_F11: (True, False, False),
        VIN_F31: (True, False, False),
        VIN_F35: (True, False, False),
        VIN_F44: (True, False, False),
        VIN_F45: (True, True, False),
        VIN_F48: (True, False, False),
        VIN_G01: (True, True, False),
        VIN_G05: (True, True, False),
        VIN_G08: (False, True, False),
        VIN_G21: (True, True, False),
        VIN_G23: (True, True, False),
        VIN_G30: (True, True, False),
        VIN_I01_NOREX: (False, True, False),
        VIN_I01_REX: (False, True, True),
    }

    for vehicle in account.vehicles:
        assert vehicle_drivetrains[vehicle.vin][0] == vehicle.has_combustion_drivetrain
        assert vehicle_drivetrains[vehicle.vin][1] == vehicle.has_electric_drivetrain
        assert vehicle_drivetrains[vehicle.vin][2] == vehicle.has_range_extender_drivetrain

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_parsing_of_lsc_type(caplog):
    """Test parsing the lsc type field."""
    account = await get_mocked_account()

    for vehicle in account.vehicles:
        assert vehicle.lsc_type is not None

    assert len(get_deprecation_warning_count(caplog)) == 0


def test_car_brand(caplog):
    """Test CarBrand enum"""
    assert CarBrands("BMW") == CarBrands("bmw")

    with pytest.raises(ValueError):
        CarBrands("Audi")

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_get_is_tracking_enabled(caplog):
    """Test setting observer position"""
    vehicle = (await get_mocked_account()).get_vehicle(VIN_F11)
    assert vehicle.is_vehicle_tracking_enabled is False

    vehicle = (await get_mocked_account()).get_vehicle(VIN_F31)
    assert vehicle.is_vehicle_tracking_enabled is True

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_available_attributes(caplog):
    """Check that available_attributes returns exactly the arguments we have in our test data."""
    account = await get_mocked_account()

    vehicle = account.get_vehicle(VIN_F31)
    assert ["gps_position", "vin"] == vehicle.available_attributes

    vehicle = account.get_vehicle(VIN_G08)
    assert [
        "gps_position",
        "vin",
        "remaining_range_total",
        "mileage",
        "charging_time_remaining",
        "charging_start_time",
        "charging_end_time",
        "charging_time_label",
        "charging_status",
        "connection_status",
        "remaining_battery_percent",
        "remaining_range_electric",
        "last_charging_end_result",
        "condition_based_services",
        "check_control_messages",
        "door_lock_state",
        "timestamp",
        "last_update_reason",
        "lids",
        "windows",
        "convertible_top",
    ] == vehicle.available_attributes

    vehicle = account.get_vehicle(VIN_G30)
    assert [
        "gps_position",
        "vin",
        "remaining_range_total",
        "mileage",
        "charging_time_remaining",
        "charging_start_time",
        "charging_end_time",
        "charging_time_label",
        "charging_status",
        "connection_status",
        "remaining_battery_percent",
        "remaining_range_electric",
        "last_charging_end_result",
        "remaining_fuel",
        "remaining_range_fuel",
        "remaining_fuel_percent",
        "condition_based_services",
        "check_control_messages",
        "door_lock_state",
        "timestamp",
        "last_update_reason",
        "lids",
        "windows",
        "convertible_top",
    ] == vehicle.available_attributes

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_vehicle_image(caplog):
    """Test vehicle image request."""
    vehicle = (await get_mocked_account()).get_vehicle(VIN_G05)

    with account_mock() as mock_api:
        mock_api.get(
            path__regex=r"(.*)/eadrax-ics/v3/presentation/vehicles/\w*/images",
            params={"carView": "VehicleInfo"},
            headers={"accept": "image/png"},
        ).respond(200, content="png_image")
        assert b"png_image" == await vehicle.get_vehicle_image(VehicleViewDirection.FRONT)

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_no_timestamp():
    """Test no timestamp available."""
    vehicle = (await get_mocked_account()).get_vehicle(VIN_F31)
    vehicle._properties.pop("lastUpdatedAt")  # pylint: disable=protected-access
    vehicle._status.pop("lastUpdatedAt")  # pylint: disable=protected-access

    assert vehicle.timestamp is None


def test_strenum():
    """Tests StrEnum."""

    class TestEnum(StrEnum):
        """Test StrEnum."""

        HELLO = "HELLO"

    assert TestEnum("hello") == TestEnum.HELLO
    assert TestEnum("HELLO") == TestEnum.HELLO

    with pytest.raises(ValueError):
        TestEnum("WORLD")


def test_vehiclebasedata():
    """Tests VehicleBaseData."""
    with pytest.raises(NotImplementedError):
        VehicleDataBase._parse_vehicle_data({})  # pylint: disable=protected-access


def test_gpsposition():
    """Tests around GPSPosition."""
    pos = GPSPosition(1.0, 2.0)
    assert pos == GPSPosition(1, 2)
    assert pos == {"latitude": 1.0, "longitude": 2.0}
    assert pos == (1, 2)
    assert pos != "(1, 2)"
