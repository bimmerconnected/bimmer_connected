from bimmer_connected.const import LAST_TRIP_URL


class LastTrip(object):
    """Models the last trip of a vehicle."""

    def __init__(self, account, vehicle):
        """Constructor."""
        self._account = account
        self._vehicle = vehicle
        self._attributes = None

    def update_data(self):
        """Load the vehicle statistics from the server."""
        url = LAST_TRIP_URL.format(vin=self._vehicle.vin, server=self._account.server_url)
        response = self._account.send_request(url, logfilename='last_trip')
        self._attributes = response.json()['lastTrip']

    @property
    def attributes(self) -> dict:
        """Retrieve all attributes from the sever.

        This does not parse the results in any way.
        """
        return self._attributes
