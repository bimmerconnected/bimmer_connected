"""Test for ChargingProfile"""
import unittest
from unittest import mock
from test import load_response_json
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.state import VehicleState
from bimmer_connected.const import SERVICE_CHARGING_PROFILE
from bimmer_connected.charging_profile import ChargingMode, ChargingPreferences, TimerTypes

I01_TEST_DATA = load_response_json('I01_NOREX/charging_profile.json')


class TestState(unittest.TestCase):
    """Test for ChargingProfile."""

    # pylint: disable=protected-access

    def test_parse_i01(self):
        """Test if the parsing of the attributes is working."""
        account = mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes[SERVICE_CHARGING_PROFILE] = I01_TEST_DATA['weeklyPlanner']
        self.assertTrue(state.charging_profile.is_pre_entry_climatization_enabled)
        self.assertEqual(ChargingMode.DELAYED_CHARGING, state.charging_profile.charging_mode)
        self.assertEqual(ChargingPreferences.CHARGING_WINDOW, state.charging_profile.charging_preferences)

        self.assertTrue(state.charging_profile.pre_entry_climatization_timer[TimerTypes.TIMER_1].timer_enabled)
        self.assertEqual('07:30',
                         state.charging_profile.pre_entry_climatization_timer[TimerTypes.TIMER_1].departure_time)
        self.assertEqual('MONDAY', state.charging_profile.pre_entry_climatization_timer[TimerTypes.TIMER_1].weekdays[0])

        self.assertEqual('05:02', state.charging_profile.preferred_charging_window.start_time)
        self.assertEqual('17:31', state.charging_profile.preferred_charging_window.end_time)

    def test_available_attributes(self):
        """Check available_attributes for charging_profile service."""
        account = mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        expected_attributes = ['is_pre_entry_climatization_enabled', 'pre_entry_climatization_timer',
                               'preferred_charging_window', 'charging_preferences', 'charging_mode']
        existing_attributes = state.charging_profile.available_attributes
        self.assertListEqual(existing_attributes, expected_attributes)
