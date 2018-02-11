import unittest
import datetime
from bimmer_connected.RemoteServices import RemoteServiceStatus, ExecutionState

EXECUTION_PENDING = {
    "remoteServiceType": "RLF",
    "remoteServiceStatus": "PENDING",
    "eventId": "312C393332416584180B5E25@bmw.de",
    "created": "2018-02-11T15:10:39.465+01",
    "lastUpdate": "2018-02-11T15:10:39.465+01"
}

EXECUTION_DELIVERED = {
    "remoteServiceType": "RLF",
    "remoteServiceStatus": "DELIVERED_TO_VEHICLE",
    "eventId": "312C393332416584180B5E25@bmw.de",
    "created": "2018-02-11T15:10:39.465+01",
    "lastUpdate": "2018-02-11T15:10:48.220+01"
}

EXECUTION_EXECUTED = {
    "remoteServiceType": "RLF",
    "remoteServiceStatus": "EXECUTED",
    "eventId": "312C393332416584180B5E25@bmw.de",
    "created": "2018-02-11T15:10:39.465+01",
    "lastUpdate": "2018-02-11T15:10:58.583+01"
}


class TestRemoteServices(unittest.TestCase):

    def test_parse_timestamp(self):
        dt = RemoteServiceStatus._parse_timestamp("2018-02-11T15:10:39.465+01")
        expected = datetime.datetime(year=2018, month=2, day=11, hour=15, minute=10, second=39, microsecond=465000)
        self.assertEqual(expected, dt)

    def test_states(self):
        rss = RemoteServiceStatus(EXECUTION_PENDING)
        self.assertEqual(ExecutionState.PENDING, rss.state)

        rss = RemoteServiceStatus(EXECUTION_DELIVERED)
        self.assertEqual(ExecutionState.DELIVERED, rss.state)

        rss = RemoteServiceStatus(EXECUTION_EXECUTED)
        self.assertEqual(ExecutionState.EXECUTED, rss.state)
