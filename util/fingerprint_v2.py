from datetime import datetime
from pathlib import Path
from pkg_resources import packaging
import argparse
import logging
import time

import requests

from bimmer_connected import __version__ as bimmer_connected_version
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.country_selector import get_region_from_name, get_server_url_eadrax, valid_regions

_LOGGER = logging.getLogger(__name__)


def main_parser() -> argparse.ArgumentParser:
    """Creates the ArgumentParser with all relevant subparsers."""
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Save a vehicle fingerprint.')

    _add_default_arguments(parser)
    _add_position_arguments(parser)
    parser.set_defaults(func=fingerprint)

    return parser


def fingerprint(args) -> None:
    """Save the vehicle fingerprint."""
    if not packaging.version.parse(bimmer_connected_version) >= packaging.version.parse('0.7.20'):
        raise NotImplementedError('This requires bimmer_connected>=0.7.20.')

    time_dir = Path.home() / 'vehicle_fingerprint' / time.strftime("%Y-%m-%d_%H-%M-%S")
    time_dir.mkdir(parents=True)

    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region),
                                    log_responses=time_dir)
    server_url = get_server_url_eadrax(get_region_from_name(args.region))

    if args.lat and args.lng:
        account.set_observer_position(args.lat, args.lng)
        for vehicle in account.vehicles:
            vehicle.set_observer_position(args.lat, args.lng)

    utcdiff = round((datetime.now() - datetime.utcnow()).seconds / 60, 0)

    print("Getting 'vehicles'")
    account.send_request_v2(
        "https://{}/eadrax-vcs/v1/vehicles".format(server_url),
        params={"apptimezone": utcdiff, "appDateTime": time.time(), "tireGuardMode": "ENABLED"}
    )

    for vehicle in account.vehicles:
        try:
            print(f"Getting 'charging-sessions' for {vehicle.vin}")
            account.send_request_v2(
                "https://{}/eadrax-chs/v1/charging-sessions".format(server_url),
                params={
                    "vin": vehicle.vin,
                    "maxResults": 40,
                    "include_date_picker": "true"
                },
                logfilename="charging-sessions"
            )
        except requests.HTTPError:
            _LOGGER.info("Vehicle %s does not support 'charging-sessions'.", vehicle.name)

        try:
            print(f"Getting 'charging-statistics' for {vehicle.vin}")
            account.send_request_v2(
                "https://{}/eadrax-chs/v1/charging-statistics".format(server_url),
                params={
                    "vin": vehicle.vin,
                    "currentDate": datetime.utcnow().isoformat()
                },
                logfilename="charging-statistics"
            )
        except requests.HTTPError:
            _LOGGER.info("Vehicle %s does not support 'charging-statistics'.", vehicle.name)

    print('fingerprint of the vehicles written to {}'.format(time_dir))


def _add_default_arguments(parser: argparse.ArgumentParser):
    """Add the default arguments username, password, region to the parser."""
    parser.add_argument('username', help='Connected Drive username')
    parser.add_argument('password', help='Connected Drive password')
    parser.add_argument('region', choices=valid_regions(), help='Region of the Connected Drive account')


def _add_position_arguments(parser: argparse.ArgumentParser):
    """Add the lat and lng attributes to the parser."""
    parser.add_argument('lat', type=float, nargs='?', const=0.0,
                        help='(optional) Your current GPS latitude (as float)')
    parser.add_argument('lng', type=float, nargs='?', const=0.0,
                        help='(optional) Your current GPS longitude (as float)')
    # parser.set_defaults(func=get_status)


def main():
    """Main function."""
    parser = main_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
