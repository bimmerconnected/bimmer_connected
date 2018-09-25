"""Version numbers of bimmer_connected."""
MAJOR_VERSION = 0
MINOR_VERSION = 5
PATCH_VERSION = 3

__short_version__ = '{}.{}'.format(MAJOR_VERSION, MINOR_VERSION)
__version__ = '{}.{}'.format(__short_version__, PATCH_VERSION)


"""urls for different services."""

AUTH_URL = 'https://{server}/gcdm/oauth/token'
BASE_URL = 'https://{server}/webapi/v1'

VEHICLES_URL = BASE_URL + '/user/vehicles'
VEHICLE_VIN_URL = VEHICLES_URL + '/{vin}'
VEHICLE_STATUS_URL = VEHICLE_VIN_URL + '/status'
REMOTE_SERVICE_STATUS_URL = VEHICLE_VIN_URL + '/serviceExecutionStatus?serviceType={service_type}'
REMOTE_SERVICE_URL = VEHICLE_VIN_URL + "/executeService"
VEHICLE_IMAGE_URL = VEHICLE_VIN_URL + "/image?width={width}&height={height}&view={view}"
