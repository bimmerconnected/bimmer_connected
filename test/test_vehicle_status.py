"""Test for VehicleState."""

import datetime

import pytest
import time_machine

from bimmer_connected.api.regions import get_region_from_name
from bimmer_connected.vehicle.doors_windows import LidState, LockState
from bimmer_connected.vehicle.fuel_and_battery import ChargingState, FuelAndBattery
from bimmer_connected.vehicle.location import VehicleLocation
from bimmer_connected.vehicle.reports import CheckControlStatus, ConditionBasedServiceStatus

from . import VIN_F31, VIN_G01, VIN_G20, VIN_G23, VIN_I01_NOREX, VIN_I01_REX, VIN_I20, get_deprecation_warning_count
from .test_account import get_mocked_account


@pytest.mark.asyncio
async def test_generic(caplog):
    """Test generic attributes."""
    status = (await get_mocked_account()).get_vehicle(VIN_G23)

    expected = datetime.datetime(year=2023, month=1, day=4, hour=14, minute=57, second=6, tzinfo=datetime.timezone.utc)
    assert expected == status.timestamp

    assert 1121 == status.mileage[0]
    assert "km" == status.mileage[1]

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_range_combustion_no_info(caplog):
    """Test if the parsing of mileage and range is working"""
    vehicle = (await get_mocked_account()).get_vehicle(VIN_F31)
    status = vehicle.fuel_and_battery

    assert (14, "L") == status.remaining_fuel
    assert status.remaining_range_fuel == (None, None)
    assert status.remaining_fuel_percent is None

    assert status.remaining_battery_percent is None
    assert status.remaining_range_electric == (None, None)

    assert status.remaining_range_total == (None, None)

    status_from_vehicle_data = FuelAndBattery.from_vehicle_data(vehicle.data)
    status_from_vehicle_data.account_timezone = status.account_timezone
    assert status_from_vehicle_data == status
    assert FuelAndBattery.from_vehicle_data({}) is None

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_range_combustion(caplog):
    """Test if the parsing of mileage and range is working"""
    # Metric units
    status = (await get_mocked_account()).get_vehicle(VIN_G20).fuel_and_battery

    assert (40, "L") == status.remaining_fuel
    assert (629, "km") == status.remaining_range_fuel
    assert status.remaining_fuel_percent == 80

    assert status.remaining_battery_percent is None
    assert status.remaining_range_electric == (None, None)

    assert (629, "km") == status.remaining_range_total

    assert len(get_deprecation_warning_count(caplog)) == 0

    # Imperial units
    status = (await get_mocked_account(metric=False)).get_vehicle(VIN_G20).fuel_and_battery

    assert (40, "gal") == status.remaining_fuel
    assert (629, "mi") == status.remaining_range_fuel
    assert status.remaining_fuel_percent == 80

    assert status.remaining_battery_percent is None
    assert status.remaining_range_electric == (None, None)

    assert (629, "mi") == status.remaining_range_total

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_range_phev(caplog):
    """Test if the parsing of mileage and range is working"""
    # Metric units
    status = (await get_mocked_account()).get_vehicle(VIN_G01).fuel_and_battery

    assert (40, "L") == status.remaining_fuel
    assert (476, "km") == status.remaining_range_fuel
    assert 80 == status.remaining_fuel_percent

    assert 80 == status.remaining_battery_percent
    assert (40, "km") == status.remaining_range_electric

    assert (516, "km") == status.remaining_range_total

    assert status.remaining_range_fuel[0] + status.remaining_range_electric[0] == status.remaining_range_total[0]

    assert len(get_deprecation_warning_count(caplog)) == 0

    # Imperial units
    status = (await get_mocked_account(metric=False)).get_vehicle(VIN_G01).fuel_and_battery

    assert (40, "gal") == status.remaining_fuel
    assert (476, "mi") == status.remaining_range_fuel
    assert 80 == status.remaining_fuel_percent

    assert 80 == status.remaining_battery_percent
    assert (40, "mi") == status.remaining_range_electric

    assert (516, "mi") == status.remaining_range_total

    assert status.remaining_range_fuel[0] + status.remaining_range_electric[0] == status.remaining_range_total[0]

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_range_rex(caplog):
    """Test if the parsing of mileage and range is working"""
    # Metric units
    status = (await get_mocked_account()).get_vehicle(VIN_I01_REX).fuel_and_battery

    assert (6, "L") == status.remaining_fuel
    assert (105, "km") == status.remaining_range_fuel
    assert status.remaining_fuel_percent is None

    assert 82 == status.remaining_battery_percent
    assert (174, "km") == status.remaining_range_electric

    assert (279, "km") == status.remaining_range_total

    assert status.remaining_range_fuel[0] + status.remaining_range_electric[0] == status.remaining_range_total[0]

    assert len(get_deprecation_warning_count(caplog)) == 0

    # Imperial units
    status = (await get_mocked_account(metric=False)).get_vehicle(VIN_I01_REX).fuel_and_battery

    assert (6, "gal") == status.remaining_fuel
    assert (105, "mi") == status.remaining_range_fuel
    assert status.remaining_fuel_percent is None

    assert 82 == status.remaining_battery_percent
    assert (174, "mi") == status.remaining_range_electric

    assert (279, "mi") == status.remaining_range_total

    assert status.remaining_range_fuel[0] + status.remaining_range_electric[0] == status.remaining_range_total[0]

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_range_electric(caplog):
    """Test if the parsing of mileage and range is working"""
    # Metric units
    status = (await get_mocked_account()).get_vehicle(VIN_I20).fuel_and_battery

    assert status.remaining_fuel == (None, None)
    assert status.remaining_range_fuel == (None, None)
    assert status.remaining_fuel_percent is None

    assert 70 == status.remaining_battery_percent
    assert (340, "km") == status.remaining_range_electric

    assert (340, "km") == status.remaining_range_total

    assert len(get_deprecation_warning_count(caplog)) == 0

    # Imperial units
    status = (await get_mocked_account(metric=False)).get_vehicle(VIN_I20).fuel_and_battery

    assert status.remaining_fuel == (None, None)
    assert status.remaining_range_fuel == (None, None)
    assert status.remaining_fuel_percent is None

    assert 70 == status.remaining_battery_percent
    assert (340, "mi") == status.remaining_range_electric

    assert (340, "mi") == status.remaining_range_total

    assert len(get_deprecation_warning_count(caplog)) == 0


@time_machine.travel("2021-11-28 21:28:59 +0000", tick=False)
@pytest.mark.asyncio
async def test_charging_end_time(caplog):
    """Test if the parsing of mileage and range is working"""
    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_I01_NOREX)

    assert vehicle.fuel_and_battery.charging_end_time == datetime.datetime(
        2021, 11, 28, 23, 27, 59, tzinfo=datetime.timezone.utc
    )
    assert vehicle.fuel_and_battery.charging_status == ChargingState.CHARGING
    assert vehicle.fuel_and_battery.is_charger_connected is True
    assert vehicle.fuel_and_battery.charging_start_time is None

    assert len(get_deprecation_warning_count(caplog)) == 0


@time_machine.travel("2021-11-28 17:28:59 +0000", tick=False)
@pytest.mark.asyncio
async def test_plugged_in_waiting_for_charge_window(caplog):
    """I01_REX is plugged in but not charging, as its waiting for charging window."""
    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_I01_REX)

    assert vehicle.fuel_and_battery.charging_end_time is None
    assert vehicle.fuel_and_battery.charging_status == ChargingState.WAITING_FOR_CHARGING
    assert vehicle.fuel_and_battery.is_charger_connected is True
    assert vehicle.fuel_and_battery.charging_start_time == datetime.datetime(
        2021, 11, 28, 18, 1, tzinfo=account.timezone
    )

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_condition_based_services(caplog):
    """Test condition based service messages."""
    vehicle = (await get_mocked_account()).get_vehicle(VIN_G23)

    cbs = vehicle.condition_based_services.messages
    assert 5 == len(cbs)
    assert ConditionBasedServiceStatus.OK == cbs[0].state
    expected_cbs0 = datetime.datetime(year=2024, month=12, day=1, tzinfo=datetime.timezone.utc)
    assert expected_cbs0 == cbs[0].due_date
    assert (50000, "km") == cbs[0].due_distance

    assert ConditionBasedServiceStatus.OK == cbs[1].state
    expected_cbs1 = datetime.datetime(year=2024, month=12, day=1, tzinfo=datetime.timezone.utc)
    assert expected_cbs1 == cbs[1].due_date
    assert (50000, "km") == cbs[1].due_distance

    assert ConditionBasedServiceStatus.OK == cbs[2].state
    expected_cbs2 = datetime.datetime(year=2024, month=12, day=1, tzinfo=datetime.timezone.utc)
    assert expected_cbs2 == cbs[2].due_date
    assert (50000, "km") == cbs[2].due_distance

    assert vehicle.condition_based_services.is_service_required is False

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_position_generic(caplog):
    """Test generic attributes."""
    status = (await get_mocked_account()).get_vehicle(VIN_G23)

    assert (48.177334, 11.556274) == status.vehicle_location.location
    assert 180 == status.vehicle_location.heading

    assert VehicleLocation.from_vehicle_data(status.data).location == status.vehicle_location.location

    assert VehicleLocation.from_vehicle_data({}) is None

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_vehicle_active(caplog):
    """Test that vehicle_active is always False."""
    account = await get_mocked_account()

    for vehicle in account.vehicles:
        assert vehicle.is_vehicle_active is False

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_parse_f31_no_position(caplog):
    """Test parsing of F31 data with position tracking disabled in the vehicle."""
    vehicle = (await get_mocked_account()).get_vehicle(VIN_F31)

    assert vehicle.vehicle_location.location is None
    assert vehicle.vehicle_location.heading is None

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_parse_gcj02_position(caplog):
    """Test conversion of GCJ02 to WGS84 for china."""
    account = await get_mocked_account(get_region_from_name("china"))
    vehicle = account.get_vehicle(VIN_G01)

    vehicle_test_data = {
        "state": {
            "location": {
                "address": {"formatted": "some_formatted_address"},
                "coordinates": {"latitude": 39.83492, "longitude": 116.23221},
                "heading": 123,
            },
            "lastUpdatedAt": "2021-11-14T20:20:21Z",
        },
    }

    vehicle.update_state(dict(vehicle.data, **vehicle_test_data), {})

    # Update twice to test against slowly crawling position due to GCJ02 to WGS84 conversion
    vehicle.update_state(dict(vehicle.data, **vehicle_test_data), {})

    assert (39.8337, 116.22617) == (
        round(vehicle.vehicle_location.location[0], 5),
        round(vehicle.vehicle_location.location[1], 5),
    )

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_lids(caplog):
    """Test features around lids."""
    # status = (await get_mocked_account()).get_vehicle(VIN_G01).doors_and_windows

    # assert 6 == len(list(status.lids))
    # assert 3 == len(list(status.open_lids))
    # assert status.all_lids_closed is False

    status = (await get_mocked_account()).get_vehicle(VIN_G23).doors_and_windows

    for lid in status.lids:
        assert LidState.CLOSED == lid.state
    assert status.all_lids_closed is True
    assert 6 == len(list(status.lids))

    status = (await get_mocked_account()).get_vehicle(VIN_I01_REX).doors_and_windows

    for lid in status.lids:
        assert LidState.CLOSED == lid.state
    assert status.all_lids_closed is True
    assert 7 == len(list(status.lids))

    assert status.lids[-1].name == "sunRoof"

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_windows_g01(caplog):
    """Test features around windows."""
    status = (await get_mocked_account()).get_vehicle(VIN_G01).doors_and_windows

    for window in status.windows:
        assert LidState.CLOSED == window.state

    assert 5 == len(list(status.windows))
    assert 0 == len(list(status.open_windows))
    assert status.all_windows_closed is True

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_door_locks(caplog):
    """Test the door locks."""
    status = (await get_mocked_account()).get_vehicle(VIN_G01).doors_and_windows

    assert LockState.LOCKED == status.door_lock_state

    status = (await get_mocked_account()).get_vehicle(VIN_I01_REX).doors_and_windows

    assert LockState.UNLOCKED == status.door_lock_state

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_check_control_messages(caplog):
    """Test handling of check control messages.

    F11 is the only vehicle with active Check Control Messages, so we only expect to get something there.
    However we have no vehicle with issues in check control.
    """
    vehicle = (await get_mocked_account()).get_vehicle(VIN_G01)
    assert vehicle.check_control_messages.has_check_control_messages is True

    ccms = vehicle.check_control_messages.messages
    assert 2 == len(ccms)

    assert CheckControlStatus.MEDIUM == ccms[1].state
    assert "ENGINE_OIL" == ccms[1].description_short
    assert None is ccms[1].description_long

    vehicle = (await get_mocked_account()).get_vehicle(VIN_G20)
    assert vehicle.check_control_messages.has_check_control_messages is False

    ccms = vehicle.check_control_messages.messages
    assert 2 == len(ccms)

    assert CheckControlStatus.LOW == ccms[1].state
    assert "ENGINE_OIL" == ccms[1].description_short
    assert None is ccms[1].description_long

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_charging_profile(caplog):
    """Test parsing of the charing profile"""

    charging_profile = (await get_mocked_account()).get_vehicle(VIN_I01_REX).charging_profile
    assert charging_profile.is_pre_entry_climatization_enabled is False

    departure_timer = charging_profile.departure_times[0]
    assert departure_timer.timer_id == 1
    assert departure_timer.start_time == datetime.time(7, 35)
    assert departure_timer.action == "DEACTIVATE"
    assert departure_timer.weekdays == ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]

    assert charging_profile.departure_times[3].start_time is None

    charging_window = charging_profile.preferred_charging_window
    assert charging_window.start_time == datetime.time(18, 1)
    assert charging_window.end_time == datetime.time(1, 30)

    assert len(get_deprecation_warning_count(caplog)) == 0
