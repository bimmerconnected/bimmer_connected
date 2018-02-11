import unittest
from unittest import mock
import datetime
from bimmer_connected.state import VehicleState

TEST_DATA = {'attributesMap': {
                  'door_passenger_front': 'CLOSED',
                  'updateTime_converted': '09.02.2018 19:03',
                  'check_control_messages': '',
                  'trunk_state': 'CLOSED',
                  'gps_lat': '38.416',
                  'updateTime': '09.02.2018 18:03:22 UTC',
                  'head_unit_pu_software': '03/17',
                  'beRemainingRangeFuelKm': '77.0',
                  'head_unit': 'NBTEvo',
                  'updateTime_converted_timestamp': '1518203002000',
                  'mileage': '1766',
                  'unitOfEnergy': 'kWh',
                  'vehicle_tracking': '1',
                  'window_driver_front': 'CLOSED',
                  'gps_lng': '23.99',
                  'door_driver_rear': 'CLOSED',
                  'beRemainingRangeFuelMile': '47.0',
                  'unitOfLength': 'km',
                  'remaining_fuel': '7',
                  'hood_state': 'CLOSED',
                  'lsc_trigger': 'VEHCSHUTDOWN',
                  'window_passenger_front': 'CLOSED',
                  'unitOfCombustionConsumption': 'l/100km',
                  'DCS_CCH_Ongoing ': None,
                  'updateTime_converted_date': '09.02.2018',
                  'door_driver_front': 'CLOSED',
                  'lastUpdateReason': 'VEHCSHUTDOWN',
                  'condition_based_services': '00001,OK,2020-01,28000;00100,OK,2022-01,60000;00003,OK,2021-01,',
                  'unitOfElectricConsumption': 'kWh/100km',
                  'window_driver_rear': 'INTERMEDIATE',
                  'kombi_current_remaining_range_fuel': '77',
                  'heading': '172',
                  'door_passenger_rear': 'CLOSED',
                  'lights_parking': 'OFF',
                  'door_lock_state': 'SECURED',
                  'DCS_CCH_Activation': None,
                  'window_passenger_rear': 'CLOSED',
                  'updateTime_converted_time': '19:03',
                  'beRemainingRangeFuel': '77.0'},
             'vehicleMessages': {
                 'ccmMessages': [],
                 'cbsMessages': [
                     {'messageType': 'CBS',
                      'date': '2020-01',
                      'text': 'Motoröl',
                      'unitOfLengthRemaining': '28000',
                      'id': 1,
                      'description': 'Nächster Service nach der angegebenen Fahrstrecke oder zum angegebenen Termin.',
                      'status': 'OK'},
                     {'messageType': 'CBS',
                      'date': '2022-01',
                      'text': 'Fahrzeug-Check',
                      'unitOfLengthRemaining': '60000',
                      'id': 100,
                      'description': 'Nächste Sichtprüfung nach der angegebenen Fahrstrecke oder zum angegebenen '
                                     'Termin.',
                      'status': 'OK'},
                     {'messageType': 'CBS',
                      'date': '2021-01',
                      'text': 'Bremsflüssigkeit',
                      'id': 3,
                      'description': 'Nächster Wechsel spätestens zum angegebenen Termin.',
                      'status': 'OK'}
                 ]}}


class MockAccount(object):

    def __init__(self):
        self.cache = False
        self.cache_timeout = 600


class TestParsing(unittest.TestCase):

    def test_parse_cache(self):
        """Test if the parsing of the attributes is working."""
        account = MockAccount()
        bc = VehicleState(account, None)
        bc._attributes = TEST_DATA['attributesMap']

        self.assertEqual(1766, bc.mileage)
        self.assertEqual('km', bc.unit_of_length)

        self.assertEqual(datetime.datetime(2018, 2, 9, 20, 3, 22), bc.timestamp)

        self.assertAlmostEqual(38.416, bc.gps_position[0])
        self.assertAlmostEqual(23.99, bc.gps_position[1])

        self.assertAlmostEqual(7, bc.remaining_fuel)
        self.assertEqual('l', bc.unit_of_volume)

        self.assertAlmostEqual(77, bc.remaining_range_fuel)

    def test_missing_attribute(self):
        """Test if error handling is working correctly."""
        account = MockAccount()
        bc = VehicleState(account, None)
        bc._attributes = dict()
        with self.assertRaises(ValueError):
            bc.mileage

    @mock.patch('bimmer_connected.vehicle.VehicleState.update_data')
    def test_no_attributes(self, _):
        """Test if error handling is working correctly."""
        account = MockAccount()
        bc = VehicleState(account, None)
        with self.assertRaises(ValueError):
            bc.mileage

    @mock.patch('bimmer_connected.vehicle.VehicleState.update_data', autospec=True)
    def test_caching(self, mocked_update):
        """Test that data is only updated, when cache is old"""
        account = MockAccount()
        account.cache = True
        account.cache_timeout = 10

        def _mock_update_data(obj):
            obj._attributes = TEST_DATA['attributesMap']
        mocked_update.side_effect = _mock_update_data
        bc = VehicleState(account, None)

        # no data -> read data
        self.assertEqual(1766, bc.mileage)
        self.assertEqual(1, mocked_update.call_count)
        # used cached data
        self.assertEqual(1766, bc.mileage)
        self.assertEqual(1, mocked_update.call_count)

        # cache expired -> read new data
        bc._cache_expiration = datetime.datetime.now() - datetime.timedelta(minutes=5)
        self.assertEqual(1766, bc.mileage)
        self.assertEqual(2, mocked_update.call_count)
