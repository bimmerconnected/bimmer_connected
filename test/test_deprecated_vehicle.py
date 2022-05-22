"""Tests for deprecated MyBMWVehicle."""
import pytest

from bimmer_connected.const import CarBrands
from bimmer_connected.vehicle.vehicle import ConnectedDriveVehicle

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
from .test_account import get_mocked_account

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
async def test_parsing_attributes(caplog):
    """Test parsing different attributes of the vehicle."""
    account = await get_mocked_account()

    for vehicle in account.vehicles:
        print(vehicle.name)
        assert vehicle.drive_train is not None
        assert vehicle.name is not None
        assert isinstance(vehicle.brand, CarBrands)
        assert vehicle.has_internal_combustion_engine is not None  #
        assert vehicle.has_hv_battery is not None  #
        assert vehicle.drive_train_attributes is not None
        assert vehicle.has_weekly_planner_service is not None  #

    assert len(get_deprecation_warning_count(caplog)) == len(account.vehicles) * 3


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
        assert vehicle_drivetrains[vehicle.vin][0] == vehicle.has_internal_combustion_engine
        assert vehicle_drivetrains[vehicle.vin][1] == vehicle.has_hv_battery
        assert vehicle_drivetrains[vehicle.vin][2] == vehicle.has_range_extender

    assert len(get_deprecation_warning_count(caplog)) == len(account.vehicles) * 3


@pytest.mark.asyncio
async def test_deprecated_vehicle(caplog):
    """Test deprecation warning for ConnectedDriveVehicle."""
    account = await get_mocked_account()

    deprecated_vehicle = ConnectedDriveVehicle(account, account.vehicles[0].data)

    assert deprecated_vehicle is not None
    assert len(get_deprecation_warning_count(caplog)) == 1
