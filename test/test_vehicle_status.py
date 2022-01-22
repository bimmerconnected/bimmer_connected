"""Test for VehicleState."""

import datetime
import logging

import pytest
import time_machine

from bimmer_connected.api.regions import get_region_from_name
from bimmer_connected.vehicle.vehicle_status import (
    ChargingState,
    ConditionBasedServiceStatus,
    LidState,
    LockState,
)

from . import VIN_F11, VIN_F31, VIN_F48, VIN_G01, VIN_G08, VIN_G30, VIN_I01_REX
from .test_account import get_account, get_mocked_account


@pytest.mark.asyncio
async def test_generic():
    """Test generic attributes."""
    status = (await get_mocked_account()).get_vehicle(VIN_G30).status

    expected = datetime.datetime(
        year=2021, month=11, day=11, hour=8, minute=58, second=53, tzinfo=datetime.timezone.utc
    )
    assert expected == status.timestamp

    assert 7991 == status.mileage[0]
    assert "km" == status.mileage[1]

    assert (12.3456, 34.5678) == status.gps_position
    assert 123 == status.gps_heading


@pytest.mark.asyncio
async def test_range_combustion_no_info():
    """Test if the parsing of mileage and range is working"""
    status = (await get_mocked_account()).get_vehicle(VIN_F31).status

    assert (32, "LITERS") == status.remaining_fuel
    assert status.remaining_range_fuel == (None, None)
    assert status.fuel_percent is None

    assert status.charging_level_hv is None
    assert status.remaining_range_electric == (None, None)

    assert status.remaining_range_total == (None, None)


@pytest.mark.asyncio
async def test_range_combustion():
    """Test if the parsing of mileage and range is working"""
    status = (await get_mocked_account()).get_vehicle(VIN_F48).status

    assert (19, "LITERS") == status.remaining_fuel
    assert (308, "km") == status.remaining_range_fuel
    assert status.fuel_percent is None

    assert status.charging_level_hv is None
    assert status.remaining_range_electric == (None, None)

    assert (308, "km") == status.remaining_range_total


@pytest.mark.asyncio
async def test_range_phev():
    """Test if the parsing of mileage and range is working"""
    status = (await get_mocked_account()).get_vehicle(VIN_G30).status

    assert (11, "LITERS") == status.remaining_fuel
    assert (107, "km") == status.remaining_range_fuel
    assert 28 == status.fuel_percent

    assert 41 == status.charging_level_hv
    assert (9, "km") == status.remaining_range_electric

    assert (116, "km") == status.remaining_range_total

    assert status.remaining_range_fuel[0] + status.remaining_range_electric[0] == status.remaining_range_total[0]


@pytest.mark.asyncio
async def test_range_rex():
    """Test if the parsing of mileage and range is working"""
    status = (await get_mocked_account()).get_vehicle(VIN_I01_REX).status

    assert (5, "LITERS") == status.remaining_fuel
    assert (64, "km") == status.remaining_range_fuel
    assert status.fuel_percent is None

    assert 100 == status.charging_level_hv
    assert (164, "km") == status.remaining_range_electric

    assert (228, "km") == status.remaining_range_total

    assert status.remaining_range_fuel[0] + status.remaining_range_electric[0] == status.remaining_range_total[0]


@pytest.mark.asyncio
async def test_range_electric():
    """Test if the parsing of mileage and range is working"""
    status = (await get_mocked_account()).get_vehicle(VIN_G08).status

    assert (0, "LITERS") == status.remaining_fuel
    assert status.remaining_range_fuel == (None, None)
    assert 0 == status.fuel_percent

    assert 50 == status.charging_level_hv
    assert (179, "km") == status.remaining_range_electric

    assert (179, "km") == status.remaining_range_total


@time_machine.travel(
    datetime.datetime.now().replace(hour=21, minute=28, second=59, microsecond=0, tzinfo=get_account().timezone)
)
@pytest.mark.asyncio
async def test_remaining_charging_time():
    """Test if the parsing of mileage and range is working"""
    account = await get_mocked_account()
    status = account.get_vehicle(VIN_G08).status
    assert 6.53 == status.charging_time_remaining


@time_machine.travel("2011-11-28 21:28:59 +0000", tick=False)
@pytest.mark.asyncio
async def test_charging_end_time():
    """Test if the parsing of mileage and range is working"""
    account = await get_mocked_account()
    status = account.get_vehicle(VIN_G08).status
    assert datetime.datetime(2011, 11, 29, 4, 1, tzinfo=account.timezone) == status.charging_end_time


@pytest.mark.asyncio
async def test_charging_time_label():
    """Test if the parsing of mileage and range is working"""
    account = await get_mocked_account()
    status = account.get_vehicle(VIN_G08).status
    assert "100% at ~04:01 AM" == status.charging_time_label


@pytest.mark.asyncio
async def test_charging_end_time_parsing_failure(caplog):
    """Test if the parsing of mileage and range is working"""
    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_G08)

    vehicle.update_state(
        {
            "status": {
                "fuelIndicators": [
                    {
                        "chargingStatusIndicatorType": "CHARGING",
                        "chargingStatusType": "CHARGING",
                        "infoLabel": "100% at later today...",
                        "rangeIconId": 59683,
                        "rangeUnits": "km",
                        "rangeValue": "179",
                    }
                ]
            },
            "properties": {},
        }
    )
    assert vehicle.status.charging_end_time is None
    assert "100% at later today..." == vehicle.status.charging_time_label
    assert 0 == vehicle.status.charging_time_remaining

    errors = [r for r in caplog.records if r.levelname == "ERROR" and "Error parsing charging end time" in r.message]
    assert len(errors) == 1


@pytest.mark.asyncio
async def test_plugged_in_waiting_for_charge_window():
    """G01 is plugged in but not charging, as its waiting for charging window."""
    # Should be None on G01 as it is only "charging"
    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_G01)

    assert vehicle.status.charging_end_time is None
    assert "Starts at ~ 09:00 AM" == vehicle.status.charging_time_label
    assert 0 == vehicle.status.charging_time_remaining
    assert ChargingState.PLUGGED_IN == vehicle.status.charging_status
    assert "CONNECTED" == vehicle.status.connection_status


@pytest.mark.asyncio
async def test_condition_based_services():
    """Test condition based service messages."""
    status = (await get_mocked_account()).get_vehicle(VIN_G30).status

    cbs = status.condition_based_services
    assert 3 == len(cbs)
    assert ConditionBasedServiceStatus.OK == cbs[0].state
    expected_cbs0 = datetime.datetime(year=2022, month=8, day=1, tzinfo=datetime.timezone.utc)
    assert expected_cbs0 == cbs[0].due_date
    assert (25000, "KILOMETERS") == cbs[0].due_distance

    assert ConditionBasedServiceStatus.OK == cbs[1].state
    expected_cbs1 = datetime.datetime(year=2023, month=8, day=1, tzinfo=datetime.timezone.utc)
    assert expected_cbs1 == cbs[1].due_date
    assert cbs[1].due_distance is None

    assert ConditionBasedServiceStatus.OK == cbs[2].state
    expected_cbs2 = datetime.datetime(year=2024, month=8, day=1, tzinfo=datetime.timezone.utc)
    assert expected_cbs2 == cbs[2].due_date
    assert (60000, "KILOMETERS") == cbs[2].due_distance

    assert status.are_all_cbs_ok is True


@pytest.mark.asyncio
async def test_parse_f31_no_position():
    """Test parsing of F31 data with position tracking disabled in the vehicle."""
    status = (await get_mocked_account()).get_vehicle(VIN_F31).status

    assert status.gps_position == (None, None)
    assert status.gps_heading is None


@pytest.mark.asyncio
async def test_parse_gcj02_position():
    """Test conversion of GCJ02 to WGS84 for china."""
    account = await get_mocked_account(get_region_from_name("china"))
    vehicle = account.get_vehicle(VIN_F48)
    vehicle.update_state(
        {
            "properties": {
                "vehicleLocation": {
                    "address": {"formatted": "some_formatted_address"},
                    "coordinates": {"latitude": 39.83492, "longitude": 116.23221},
                    "heading": 123,
                },
                "lastUpdatedAt": "2021-11-14T20:20:21Z",
            },
            "status": {
                "fuelIndicators": [],
                "lastUpdatedAt": "2021-11-14T20:20:21Z",
            },
        },
    )
    assert (39.8337, 116.22617) == (round(vehicle.status.gps_position[0], 5), round(vehicle.status.gps_position[1], 5))


@pytest.mark.asyncio
async def test_parse_g08():
    """Test if the parsing of the attributes is working."""
    status = (await get_mocked_account()).get_vehicle(VIN_G08).status

    assert (179, "km") == status.remaining_range_electric
    assert (179, "km") == status.remaining_range_total
    assert ChargingState.CHARGING == status.charging_status
    assert 50 == status.charging_level_hv


# def test_missing_attribute():
#     """Test if error handling is working correctly."""
#     account = unittest.mock.MagicMock(ConnectedDriveAccount)
#     state = VehicleState(account, None)
#     state._attributes[SERVICE_STATUS] = {}
#     assert status.mileage is None


@pytest.mark.asyncio
async def test_lids():
    """Test features around lids."""
    status = (await get_mocked_account()).get_vehicle(VIN_G30).status

    assert 6 == len(list(status.lids))
    assert 3 == len(list(status.open_lids))
    assert status.all_lids_closed is False

    status = (await get_mocked_account()).get_vehicle(VIN_G08).status

    for lid in status.lids:
        assert LidState.CLOSED == lid.state
    assert status.all_lids_closed is True
    assert 6 == len(list(status.lids))


@pytest.mark.asyncio
async def test_windows_g31():
    """Test features around windows."""
    status = (await get_mocked_account()).get_vehicle(VIN_G08).status

    for window in status.windows:
        assert LidState.CLOSED == window.state

    assert 5 == len(list(status.windows))
    assert 0 == len(list(status.open_windows))
    assert status.all_windows_closed is True


@pytest.mark.asyncio
async def test_door_locks():
    """Test the door locks."""
    status = (await get_mocked_account()).get_vehicle(VIN_G08).status

    assert LockState.LOCKED == status.door_lock_state

    status = (await get_mocked_account()).get_vehicle(VIN_I01_REX).status

    assert LockState.UNLOCKED == status.door_lock_state


@pytest.mark.asyncio
async def test_empty_status(caplog):
    """Test an empy status."""
    status = (await get_mocked_account()).get_vehicle(VIN_F31).status
    status.properties.pop("inMotion")

    caplog.set_level(logging.DEBUG)
    assert status.is_vehicle_active is None
    debug = [r for r in caplog.records if r.levelname == "DEBUG" and "No data available" in r.message]
    assert len(debug) == 1

    status.properties = None
    status.status = None

    with pytest.raises(ValueError):
        assert status.is_vehicle_active is None


@pytest.mark.asyncio
async def test_check_control_messages():
    """Test handling of check control messages.

    G21 is the only vehicle with active Check Control Messages, so we only expect to get something there.
    However we have no vehicle with issues in check control.
    """
    vehicle = (await get_mocked_account()).get_vehicle(VIN_F11)
    assert vehicle.status.has_check_control_messages is True

    ccms = vehicle.status.check_control_messages
    assert 2 == len(ccms)

    assert "Medium" == ccms[0].state
    assert "229" == ccms[0].ccm_id
    assert (
        "Charge by driving for longer periods or use external charger. "
        "Functions requiring battery will be switched off."
    ) == ccms[0].description_long

    assert "Battery discharged: Start engine" == ccms[0].description_short

    assert "Low" == ccms[1].state
    assert "50" == ccms[1].ccm_id
    assert (
        "System unable to monitor tire pressure. Check tire pressures manually. "
        "Continued driving possible. Consult service center."
    ) == ccms[1].description_long

    assert "Flat Tire Monitor (FTM) inactive" == ccms[1].description_short
