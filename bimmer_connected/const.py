"""Version numbers of bimmer_connected."""
MAJOR_VERSION = 0
MINOR_VERSION = 4
PATCH_VERSION = '2'

__short_version__ = '{}.{}'.format(MAJOR_VERSION, MINOR_VERSION)
__version__ = '{}.{}'.format(__short_version__, PATCH_VERSION)


"""urls for different services."""

COUNTRY_SELECTION_URL = 'https://www.bmw-connecteddrive.com/cms/default/default/country-selection.json'
AUTH_URL_REST_OF_WORLD = 'https://customer.bmwgroup.com/gcdm/oauth/authenticate'

#: so far only Canada seems to have a separate url for user authentication
AUTH_URL_DICT = {
    'Canada': 'https://crm.bmw.ca/en-CA/ConnectedDrive/Account',
}

REMOTE_SERVICE_URL = '{server}/api/vehicle/remoteservices/v1/{vin}/{service}'
VEHICLE_STATE_URL = '{server}/api/vehicle/dynamic/v1/{vin}'
VEHICLE_SPECS_URL = '{server}/api/vehicle/specs/v1/{vin}'
LIST_VEHICLES_URL = '{server}/api/me/vehicles/v2'
