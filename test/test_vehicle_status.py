"""Test for VehicleState."""

import datetime

import pytest
import time_machine

from bimmer_connected.api.regions import get_region_from_name
from bimmer_connected.vehicle.doors_windows import LidState, LockState
from bimmer_connected.vehicle.fuel_and_battery import ChargingState, FuelAndBattery
from bimmer_connected.vehicle.location import VehicleLocation
from bimmer_connected.vehicle.reports import CheckControlStatus, ConditionBasedServiceStatus

from . import VIN_F11, VIN_F31, VIN_F48, VIN_G01, VIN_G08, VIN_G23, VIN_G30, VIN_I01_REX, get_deprecation_warning_count
from .test_account import get_mocked_account


@pytest.mark.asyncio
async def test_generic(caplog):
    """Test generic attributes."""
    status = (await get_mocked_account()).get_vehicle(VIN_G30)

    expected = datetime.datetime(year=2021, month=11, day=11, hour=8, minute=58, second=53)
    assert expected == status.timestamp

    assert 7991 == status.mileage[0]
    assert "km" == status.mileage[1]

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_range_combustion_no_info(caplog):
    """Test if the parsing of mileage and range is working"""
    vehicle = (await get_mocked_account()).get_vehicle(VIN_F31)
    status = vehicle.fuel_and_battery

    assert (32, "LITERS") == status.remaining_fuel
    assert status.remaining_range_fuel == (None, None)
    assert status.remaining_fuel_percent is None

    assert status.remaining_battery_percent is None
    assert status.remaining_range_electric == (None, None)

    assert status.remaining_range_total == (None, None)

    status_from_vehicle_data = FuelAndBattery.from_vehicle_data(vehicle.data)
    status_from_vehicle_data.account_timezone = status.account_timezone
    assert status_from_vehicle_data == status
    assert FuelAndBattery.from_vehicle_data({}) is None

    # pylint: disable=protected-access
    assert FuelAndBattery._parse_to_tuple({"rangeValue": "seventeen", "rangeUnit": "mi"}) == (None, None)

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_range_combustion(caplog):
    """Test if the parsing of mileage and range is working"""
    status = (await get_mocked_account()).get_vehicle(VIN_F48).fuel_and_battery

    assert (19, "LITERS") == status.remaining_fuel
    assert (308, "km") == status.remaining_range_fuel
    assert status.remaining_fuel_percent is None

    assert status.remaining_battery_percent is None
    assert status.remaining_range_electric == (None, None)

    assert (308, "km") == status.remaining_range_total

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_range_phev(caplog):
    """Test if the parsing of mileage and range is working"""
    status = (await get_mocked_account()).get_vehicle(VIN_G30).fuel_and_battery

    assert (11, "LITERS") == status.remaining_fuel
    assert (107, "km") == status.remaining_range_fuel
    assert 28 == status.remaining_fuel_percent

    assert 41 == status.remaining_battery_percent
    assert (9, "km") == status.remaining_range_electric

    assert (116, "km") == status.remaining_range_total

    assert status.remaining_range_fuel[0] + status.remaining_range_electric[0] == status.remaining_range_total[0]

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_range_rex(caplog):
    """Test if the parsing of mileage and range is working"""
    status = (await get_mocked_account()).get_vehicle(VIN_I01_REX).fuel_and_battery

    assert (5, "LITERS") == status.remaining_fuel
    assert (64, "km") == status.remaining_range_fuel
    assert status.remaining_fuel_percent is None

    assert 100 == status.remaining_battery_percent
    assert (164, "km") == status.remaining_range_electric

    assert (228, "km") == status.remaining_range_total

    assert status.remaining_range_fuel[0] + status.remaining_range_electric[0] == status.remaining_range_total[0]

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_range_electric(caplog):
    """Test if the parsing of mileage and range is working"""
    status = (await get_mocked_account()).get_vehicle(VIN_G08).fuel_and_battery

    assert (0, "LITERS") == status.remaining_fuel
    assert status.remaining_range_fuel == (None, None)
    assert status.remaining_fuel_percent is None

    assert 50 == status.remaining_battery_percent
    assert (179, "km") == status.remaining_range_electric

    assert (179, "km") == status.remaining_range_total

    assert len(get_deprecation_warning_count(caplog)) == 0


@time_machine.travel("2011-11-28 21:28:59 +0000", tick=False)
@pytest.mark.asyncio
async def test_charging_end_time(caplog):
    """Test if the parsing of mileage and range is working"""
    account = await get_mocked_account()
    status = account.get_vehicle(VIN_G08).fuel_and_battery
    assert datetime.datetime(2011, 11, 29, 4, 1, tzinfo=account.timezone) == status.charging_end_time

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_charging_time_label(caplog):
    """Test if the parsing of mileage and range is working"""
    account = await get_mocked_account()
    status = account.get_vehicle(VIN_G08).fuel_and_battery
    assert "100% at ~04:01 AM" == status.charging_time_label

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_charging_end_time_parsing_failure(caplog):
    """Test if the parsing of mileage and range is working"""
    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_G08)

    vehicle.update_state(
        dict(
            vehicle.data,
            **{
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
            },
        )
    )
    assert vehicle.fuel_and_battery.charging_end_time is None
    assert "100% at later today..." == vehicle.fuel_and_battery.charging_time_label

    errors = [r for r in caplog.records if r.levelname == "ERROR" and "Error parsing charging end time" in r.message]
    assert len(errors) == 1

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_plugged_in_waiting_for_charge_window(caplog):
    """G01 is plugged in but not charging, as its waiting for charging window."""
    # Should be None on G01 as it is only "charging"
    account = await get_mocked_account()
    vehicle = account.get_vehicle(VIN_G01)

    assert vehicle.fuel_and_battery.charging_end_time is None
    assert "Starts at ~ 09:00 AM" == vehicle.fuel_and_battery.charging_time_label
    assert ChargingState.PLUGGED_IN == vehicle.fuel_and_battery.charging_status
    assert vehicle.fuel_and_battery.is_charger_connected is True

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_condition_based_services(caplog):
    """Test condition based service messages."""
    vehicle = (await get_mocked_account()).get_vehicle(VIN_G30)

    cbs = vehicle.condition_based_services.messages
    assert 3 == len(cbs)
    assert ConditionBasedServiceStatus.OK == cbs[0].state
    expected_cbs0 = datetime.datetime(year=2022, month=8, day=1)
    assert expected_cbs0 == cbs[0].due_date
    assert (25000, "KILOMETERS") == cbs[0].due_distance

    assert ConditionBasedServiceStatus.OK == cbs[1].state
    expected_cbs1 = datetime.datetime(year=2023, month=8, day=1)
    assert expected_cbs1 == cbs[1].due_date
    assert (None, None) == cbs[1].due_distance

    assert ConditionBasedServiceStatus.OK == cbs[2].state
    expected_cbs2 = datetime.datetime(year=2024, month=8, day=1)
    assert expected_cbs2 == cbs[2].due_date
    assert (60000, "KILOMETERS") == cbs[2].due_distance

    assert vehicle.condition_based_services.is_service_required is False

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_position_generic(caplog):
    """Test generic attributes."""
    status = (await get_mocked_account()).get_vehicle(VIN_G30)

    assert (12.3456, 34.5678) == status.vehicle_location.location
    assert 123 == status.vehicle_location.heading

    assert VehicleLocation.from_vehicle_data(status.data).location == status.vehicle_location.location

    assert VehicleLocation.from_vehicle_data({}) is None

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_parse_f31_no_position(caplog):
    """Test parsing of F31 data with position tracking disabled in the vehicle."""
    vehicle = (await get_mocked_account()).get_vehicle(VIN_F31)

    assert vehicle.vehicle_location.location == (None, None)
    assert vehicle.vehicle_location.heading is None

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_parse_gcj02_position(caplog):
    """Test conversion of GCJ02 to WGS84 for china."""
    account = await get_mocked_account(get_region_from_name("china"))
    vehicle = account.get_vehicle(VIN_F48)

    vehicle_test_data = {
        "properties": {
            "vehicleLocation": {
                "address": {"formatted": "some_formatted_address"},
                "coordinates": {"latitude": 39.83492, "longitude": 116.23221},
                "heading": 123,
            },
            "lastUpdatedAt": "2021-11-14T20:20:21Z",
        },
        "status": {
            "FuelAndBattery": [],
            "lastUpdatedAt": "2021-11-14T20:20:21Z",
        },
    }

    vehicle.update_state(dict(vehicle.data, **vehicle_test_data))

    # Update twice to test against slowly crawling position due to GCJ02 to WGS84 conversion
    vehicle.update_state(dict(vehicle.data, **vehicle_test_data))

    assert (39.8337, 116.22617) == (
        round(vehicle.vehicle_location.location[0], 5),
        round(vehicle.vehicle_location.location[1], 5),
    )

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_parse_g08(caplog):
    """Test if the parsing of the attributes is working."""
    status = (await get_mocked_account()).get_vehicle(VIN_G08).fuel_and_battery

    assert (179, "km") == status.remaining_range_electric
    assert (179, "km") == status.remaining_range_total
    assert ChargingState.CHARGING == status.charging_status
    assert 50 == status.remaining_battery_percent

    assert len(get_deprecation_warning_count(caplog)) == 0


# def test_missing_attribute(caplog):
#     """Test if error handling is working correctly."""
#     account = unittest.mock.MagicMock(MyBMWAccount)
#     state = VehicleState(account, None)
#     state._attributes[SERVICE_STATUS] = {}
#     assert status.mileage is None


@pytest.mark.asyncio
async def test_lids(caplog):
    """Test features around lids."""
    status = (await get_mocked_account()).get_vehicle(VIN_G30).doors_and_windows

    assert 6 == len(list(status.lids))
    assert 3 == len(list(status.open_lids))
    assert status.all_lids_closed is False

    status = (await get_mocked_account()).get_vehicle(VIN_G08).doors_and_windows

    for lid in status.lids:
        assert LidState.CLOSED == lid.state
    assert status.all_lids_closed is True
    assert 6 == len(list(status.lids))

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_windows_g31(caplog):
    """Test features around windows."""
    status = (await get_mocked_account()).get_vehicle(VIN_G08).doors_and_windows

    for window in status.windows:
        assert LidState.CLOSED == window.state

    assert 5 == len(list(status.windows))
    assert 0 == len(list(status.open_windows))
    assert status.all_windows_closed is True

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_convertible_roof_g23(caplog):
    """Test features around windows."""
    status = (await get_mocked_account()).get_vehicle(VIN_G23).doors_and_windows

    assert status.convertible_top == LidState.OPEN

    assert len(get_deprecation_warning_count(caplog)) == 0


@pytest.mark.asyncio
async def test_door_locks(caplog):
    """Test the door locks."""
    status = (await get_mocked_account()).get_vehicle(VIN_G08).doors_and_windows

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
    vehicle = (await get_mocked_account()).get_vehicle(VIN_F11)
    assert vehicle.check_control_messages.has_check_control_messages is True

    ccms = vehicle.check_control_messages.messages
    assert 2 == len(ccms)

    assert CheckControlStatus.MEDIUM == ccms[0].state
    assert (
        "Charge by driving for longer periods or use external charger. "
        "Functions requiring battery will be switched off."
    ) == ccms[0].description_long

    assert "Battery discharged: Start engine" == ccms[0].description_short

    assert CheckControlStatus.LOW == ccms[1].state
    assert (
        "System unable to monitor tire pressure. Check tire pressures manually. "
        "Continued driving possible. Consult service center."
    ) == ccms[1].description_long

    assert "Flat Tire Monitor (FTM) inactive" == ccms[1].description_short

    assert len(get_deprecation_warning_count(caplog)) == 0
