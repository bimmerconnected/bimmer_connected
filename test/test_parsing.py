import unittest
import datetime
import bimmer_connected

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


class TestParsing(unittest.TestCase):

    def test_parse(self):
        """Test if the parsing of the attributes is working."""
        bc = bimmer_connected.BimmerConnected('', '', '')
        bc.attributes = TEST_DATA['attributesMap']

        self.assertEqual(1766, bc.mileage)
        self.assertEqual(datetime.datetime(2018, 2, 9, 20, 3, 22), bc.timestamp)
        self.assertAlmostEqual(23.99, bc.gps_longitude)

    def test_missing_attribute(self):
        bc = bimmer_connected.BimmerConnected('', '', '')
        bc.attributes = dict()
        self.assertIsNone(bc.mileage)
