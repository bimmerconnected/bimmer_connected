from enum import Enum
import datetime

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'


class ExecutionState(Enum):
    PENDING = 'PENDING'
    DELIVERED = 'DELIVERED_TO_VEHICLE'
    EXECUTED = 'EXECUTED'


class RemoteServiceStatus(object):

    def __init__(self, response: dict):
        self._response = response
        self.state = ExecutionState(response['remoteServiceStatus'])
        self.timestamp = self._parse_timestamp(response['lastUpdate'])

    @staticmethod
    def _parse_timestamp(timestamp: str) -> datetime.datetime:
        offset = int(timestamp[-3:])
        tz = datetime.timezone(datetime.timedelta(hours=offset))
        result = datetime.datetime.strptime(timestamp[:-3], TIME_FORMAT)
        result.replace(tzinfo=tz)
        return result
