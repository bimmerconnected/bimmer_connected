"""Test for Navigation"""
import unittest
from unittest import mock
from test import load_response_json
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.state import VehicleState
from bimmer_connected.const import SERVICE_NAVIGATION

G30_PHEV_OS7_TEST_DATA = load_response_json('G30_PHEV_OS7/navigation.json')


class TestState(unittest.TestCase):
    """Test for Navigation."""

    # pylint: disable=protected-access

    def test_parse_g30_phev_os7(self):
        """Test if the parsing of the attributes is working."""
        account = mock.MagicMock(ConnectedDriveAccount)
        state = VehicleState(account, None)
        state._attributes[SERVICE_NAVIGATION] = G30_PHEV_OS7_TEST_DATA
        self.assertEqual(52.82273, state.navigation.latitude)
        self.assertEqual(8.8276, state.navigation.longitude)
        self.assertEqual('DEU', state.navigation.iso_country_code)
        self.assertEqual(1.4, state.navigation.aux_power_regular)
        self.assertEqual(1.2, state.navigation.aux_power_eco_pro)
        self.assertEqual(0.4, state.navigation.aux_power_eco_pro_plus)
        self.assertEqual(4.98700008381234, state.navigation.soc)
        self.assertEqual(9.48, state.navigation.soc_max)
        self.assertIsNone(state.navigation.eco)
        self.assertIsNone(state.navigation.norm)
        self.assertIsNone(state.navigation.eco_ev)
        self.assertIsNone(state.navigation.norm_ev)
        self.assertIsNone(state.navigation.vehicle_mass)
        self.assertIsNone(state.navigation.k_acc_reg)
        self.assertIsNone(state.navigation.k_dec_reg)
        self.assertIsNone(state.navigation.k_acc_eco)
        self.assertIsNone(state.navigation.k_dec_eco)
        self.assertIsNone(state.navigation.k_up)
        self.assertIsNone(state.navigation.k_down)
        self.assertIsNone(state.navigation.drive_train)
        self.assertFalse(state.navigation.pending_update)
        self.assertFalse(state.navigation.vehicle_tracking)
