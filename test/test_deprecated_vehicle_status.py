"""Test for deprecated VehicleState."""

import datetime

import pytest
import time_machine

from bimmer_connected.api.regions import get_region_from_name
from bimmer_connected.vehicle.doors_windows import LidState, LockState
from bimmer_connected.vehicle.fuel_and_battery import ChargingState
from bimmer_connected.vehicle.reports import CheckControlStatus, ConditionBasedServiceStatus
from bimmer_connected.vehicle.vehicle import ConnectedDriveVehicle

from . import VIN_F31, VIN_G01, VIN_G20, VIN_G23, VIN_I01_NOREX, VIN_I01_REX, VIN_I20, get_deprecation_warning_count
from .test_account import get_mocked_account


@pytest.mark.asyncio
async def test_generic(caplog):
    """Test generic attributes."""
    status = (await get_mocked_account()).get_vehicle(VIN_G23).status

    expected = datetime.datetime(year=2023, month=1, day=4, hour=14, minute=57, second=6, tzinfo=datetime.timezone.utc)
    assert expected == status.timestamp

    assert 1121 == status.mileage[0]
    assert "km" == status.mileage[1]

    assert (48.177334, 11.556274) == status.gps_position
    assert 180 == status.gps_heading

    assert status.is_vehicle_active is False
    assert status.fuel_indicator_count is None
    assert hasattr(status, "last_update_reason") is True
    assert status.last_update_reason is None
    assert status.has_parking_light_state is False

    assert len(get_deprecation_warning_count(caplog)) == 10


@pytest.mark.asyncio
async def test_range_combustion_no_info(caplog):
    """Test if the parsing of mileage and range is working"""
    status = (await get_mocked_account()).get_vehicle(VIN_F31).status

    assert (14, "L") == status.remaining_fuel
    assert status.remaining_range_fuel == (None, None)
    assert status.fuel_percent is None

    assert status.charging_level_hv is None
    assert status.remaining_range_electric == (None, None)

    assert status.remaining_range_total == (None, None)

    assert len(get_deprecation_warning_count(caplog)) == 6


@pytest.mark.asyncio
async def test_range_combustion(caplog):
    """Test if the parsing of mileage and range is working"""
    status = (await get_mocked_account()).get_vehicle(VIN_G20).status

    assert (40, "L") == status.remaining_fuel
    assert (629, "km") == status.remaining_range_fuel
    assert status.fuel_percent == 80

    assert status.charging_level_hv is None
    assert status.remaining_range_electric == (None, None)

    assert (629, "km") == status.remaining_range_total

    assert len(get_deprecation_warning_count(caplog)) == 6


@pytest.mark.asyncio
async def test_range_phev(caplog):
    """Test if the parsing of mileage and range is working"""
    status = (await get_mocked_account()).get_vehicle(VIN_G01).status

    assert (40, "L") == status.remaining_fuel
    assert (476, "km") == status.remaining_range_fuel
    assert 80 == status.fuel_percent

    assert 80 == status.charging_level_hv
    assert (40, "km") == status.remaining_range_electric

    assert (516, "km") == status.remaining_range_total

    assert status.remaining_range_fuel[0] + status.remaining_range_electric[0] == status.remaining_range_total[0]

    assert len(get_deprecation_warning_count(caplog)) == 9


@pytest.mark.asyncio
async def test_range_rex(caplog):
    """Test if the parsing of mileage and range is working"""
    status = (await get_mocked_account()).get_vehicle(VIN_I01_REX).status

    assert (6, "L") == status.remaining_fuel
    assert (105, "km") == status.remaining_range_fuel
    assert status.fuel_percent is None

    assert 82 == status.charging_level_hv
    assert (174, "km") == status.remaining_range_electric

    assert (279, "km") == status.remaining_range_total

    assert status.remaining_range_fuel[0] + status.remaining_range_electric[0] == status.remaining_range_total[0]

    assert len(get_deprecation_warning_count(caplog)) == 9


@pytest.mark.asyncio
async def test_range_electric(caplog):
    """Test if the parsing of mileage and range is working"""
    status = (await get_mocked_account()).get_vehicle(VIN_G23).status

    assert status.remaining_fuel == (None, None)
    assert status.remaining_range_fuel == (None, None)
    assert status.fuel_percent is None

    assert 80 == status.charging_level_hv
    assert (472, "km") == status.remaining_range_electric

    assert (472, "km") == status.remaining_range_total

    assert len(get_deprecation_warning_count(caplog)) == 6


@time_machine.travel("2021-11-28 21:28:59 +0000", tick=False)
@pytest.mark.asyncio
async def test_charging_end_time(caplog):
    """Test if the parsing of mileage and range is working"""
    account = await get_mocked_account()
    status = account.get_vehicle(VIN_I01_NOREX).status
    assert datetime.datetime(2021, 11, 28, 23, 27, 59, tzinfo=datetime.timezone.utc) == status.charging_end_time

    warnings = [r for r in caplog.records if r.levelname == "WARNING" and "DeprecationWarning" in r.message]
    assert len(warnings) == 1


@pytest.mark.asyncio
async def test_charging_time_label(caplog):
    """Test if the parsing of mileage and range is working"""
    account = await get_mocked_account()
    status = account.get_vehicle(VIN_I20).status
    assert None is status.charging_time_label

    assert len(get_deprecation_warning_count(caplog)) == 1


@pytest.mark.asyncio
async def test_plugged_in_waiting_for_charge_window(caplog):
    """G01 is plugged in but not charging, as its waiting for charging window."""
    # Should be None on G01 as it is only "charging"
    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_I01_REX)

    assert vehicle.status.charging_end_time is None
    assert ChargingState.WAITING_FOR_CHARGING == vehicle.status.charging_status
    assert "CONNECTED" == vehicle.status.connection_status

    assert len(get_deprecation_warning_count(caplog)) == 3


@pytest.mark.asyncio
async def test_condition_based_services(caplog):
    """Test condition based service messages."""
    status = (await get_mocked_account()).get_vehicle(VIN_G23).status

    cbs = status.condition_based_services
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

    assert status.are_all_cbs_ok is True

    assert len(get_deprecation_warning_count(caplog)) == 2


@pytest.mark.asyncio
async def test_parse_f31_no_position(caplog):
    """Test parsing of F31 data with position tracking disabled in the vehicle."""
    status = (await get_mocked_account()).get_vehicle(VIN_F31).status

    assert status.gps_position is None
    assert status.gps_heading is None

    assert len(get_deprecation_warning_count(caplog)) == 2


@pytest.mark.asyncio
async def test_parse_gcj02_position(caplog):
    """Test conversion of GCJ02 to WGS84 for china."""
    account = await get_mocked_account(get_region_from_name("china"))
    vehicle = account.get_vehicle(VIN_G01)
    vehicle = ConnectedDriveVehicle(account, vehicle.data)
    vehicle.update_state(
        dict(
            vehicle.data,
            **{
                "state": {
                    "location": {
                        "address": {"formatted": "some_formatted_address"},
                        "coordinates": {"latitude": 39.83492, "longitude": 116.23221},
                        "heading": 123,
                    },
                    "lastUpdatedAt": "2021-11-14T20:20:21Z",
                }
            },
        )
    )
    assert (39.8337, 116.22617) == (round(vehicle.status.gps_position[0], 5), round(vehicle.status.gps_position[1], 5))

    assert len(get_deprecation_warning_count(caplog)) == 3


@pytest.mark.asyncio
async def test_lids(caplog):
    """Test features around lids."""
    # status = (await get_mocked_account()).get_vehicle(VIN_G30).status

    # assert 6 == len(list(status.lids))
    # assert 3 == len(list(status.open_lids))
    # assert status.all_lids_closed is False

    status = (await get_mocked_account()).get_vehicle(VIN_G23).status

    for lid in status.lids:
        assert LidState.CLOSED == lid.state
    assert status.all_lids_closed is True
    assert 0 == len(status.open_lids)
    assert 6 == len(list(status.lids))

    assert len(get_deprecation_warning_count(caplog)) == 4


@pytest.mark.asyncio
async def test_windows_g31(caplog):
    """Test features around windows."""
    status = (await get_mocked_account()).get_vehicle(VIN_G01).status

    for window in status.windows:
        assert LidState.CLOSED == window.state

    assert 5 == len(list(status.windows))
    assert 0 == len(list(status.open_windows))
    assert status.all_windows_closed is True

    assert len(get_deprecation_warning_count(caplog)) == 4


@pytest.mark.asyncio
async def test_door_locks(caplog):
    """Test the door locks."""
    status = (await get_mocked_account()).get_vehicle(VIN_G01).status

    assert LockState.LOCKED == status.door_lock_state

    status = (await get_mocked_account()).get_vehicle(VIN_I01_REX).status

    assert LockState.UNLOCKED == status.door_lock_state

    assert len(get_deprecation_warning_count(caplog)) == 2


@pytest.mark.asyncio
async def test_check_control_messages(caplog):
    """Test handling of check control messages.

    F11 is the only vehicle with active Check Control Messages, so we only expect to get something there.
    However we have no vehicle with issues in check control.
    """
    vehicle = (await get_mocked_account()).get_vehicle(VIN_G01)
    assert vehicle.status.has_check_control_messages is True

    ccms = vehicle.status.check_control_messages
    assert 2 == len(ccms)

    assert CheckControlStatus.MEDIUM == ccms[1].state
    assert "ENGINE_OIL" == ccms[1].description_short
    assert None is ccms[1].description_long

    assert len(get_deprecation_warning_count(caplog)) == 2


@pytest.mark.asyncio
async def test_functions_without_data(caplog):
    """Test functions that do not return any result anymore."""
    status = (await get_mocked_account()).get_vehicle(VIN_G01).status

    assert status.last_charging_end_result is None
    assert status.parking_lights is None
    assert status.are_parking_lights_on is None
    assert status.max_range_electric is None
    assert status.charging_time_remaining is None
    assert status.charging_start_time is None

    assert len(get_deprecation_warning_count(caplog)) == 6
