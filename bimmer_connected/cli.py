#!/usr/bin/python3
"""Simple executable to demonstrate and test the usage of the library."""

import argparse
import logging
import json
import time
import sys

from pathlib import Path

import requests

from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.country_selector import get_region_from_name, valid_regions
from bimmer_connected.vehicle import VehicleViewDirection

TEXT_VIN = 'Vehicle Identification Number'


def main_parser() -> argparse.ArgumentParser:
    """Creates the ArgumentParser with all relevant subparsers."""
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='A simple executable to use and test the library.')
    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.required = True

    status_parser = subparsers.add_parser('status', description='Get the current status of the vehicle.')
    _add_default_arguments(status_parser)
    _add_position_arguments(status_parser)

    fingerprint_parser = subparsers.add_parser('fingerprint', description='Save a vehicle fingerprint.')
    _add_default_arguments(fingerprint_parser)
    _add_position_arguments(fingerprint_parser)
    fingerprint_parser.set_defaults(func=fingerprint)

    flash_parser = subparsers.add_parser('lightflash', description='Flash the vehicle lights.')
    _add_default_arguments(flash_parser)
    flash_parser.add_argument('vin', help=TEXT_VIN)
    flash_parser.set_defaults(func=light_flash)

    finder_parser = subparsers.add_parser('vehiclefinder', description='Update the vehicle GPS location.')
    _add_default_arguments(finder_parser)
    finder_parser.add_argument('vin', help=TEXT_VIN)
    finder_parser.set_defaults(func=vehicle_finder)

    image_parser = subparsers.add_parser('image', description='Download a vehicle image.')
    _add_default_arguments(image_parser)
    image_parser.add_argument('vin', help=TEXT_VIN)
    image_parser.set_defaults(func=image)

    sendpoi_parser = subparsers.add_parser('sendpoi', description='Send a point of interest to the vehicle.')
    _add_default_arguments(sendpoi_parser)
    sendpoi_parser.add_argument('vin', help=TEXT_VIN)
    sendpoi_parser.add_argument('latitude', help='Latitude of the POI', type=float)
    sendpoi_parser.add_argument('longitude', help='Longitude of the POI', type=float)
    sendpoi_parser.add_argument('--name', help='(optional, display only) Name of the POI', nargs='?', default=None)
    sendpoi_parser.add_argument('--street', help='(optional, display only) Street & House No. of the POI',
                                nargs='?', default=None)
    sendpoi_parser.add_argument('--city', help='(optional, display only) City of the POI', nargs='?', default=None)
    sendpoi_parser.add_argument('--postalcode', help='(optional, display only) Postal code of the POI',
                                nargs='?', default=None)
    sendpoi_parser.add_argument('--country', help='(optional, display only) Country of the POI',
                                nargs='?', default=None)
    sendpoi_parser.set_defaults(func=send_poi)

    sendpoi_from_address_parser = subparsers.add_parser('sendpoi_from_address',
                                                        description=('Send a point of interest parsed from a'
                                                                     ' street address to the vehicle.'))
    _add_default_arguments(sendpoi_from_address_parser)
    sendpoi_from_address_parser.add_argument('vin', help=TEXT_VIN)
    sendpoi_from_address_parser.add_argument('-n', '--name', help='(optional, display only) Name of the POI',
                                             nargs='?', default=None)
    sendpoi_from_address_parser.add_argument('-a', '--address', nargs='+',
                                             help="Address (e.g. 'Street 17, city, zip, country')")
    sendpoi_from_address_parser.set_defaults(func=send_poi_from_address)

    message_parser = subparsers.add_parser('sendmessage', description='Send a text message to the vehicle.')
    _add_default_arguments(message_parser)
    message_parser.add_argument('vin', help=TEXT_VIN)
    message_parser.add_argument('text', help='Text to be sent.')
    message_parser.add_argument('subject', help='(optional) Message subject', nargs='?')
    message_parser.set_defaults(func=send_message)

    return parser


def get_status(args) -> None:
    """Get the vehicle status."""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    if args.lat and args.lng:
        for vehicle in account.vehicles:
            vehicle.set_observer_position(args.lat, args.lng)
    account.update_vehicle_states()

    print('Found {} vehicles: {}'.format(
        len(account.vehicles),
        ','.join([v.name for v in account.vehicles])))

    for vehicle in account.vehicles:
        print('VIN: {}'.format(vehicle.vin))
        print('Mileage: {}'.format(vehicle.state.vehicle_status.mileage))
        print('Vehicle properties:')
        print(json.dumps(vehicle.attributes, indent=4))
        print('Vehicle status:')
        print(json.dumps(vehicle.state.vehicle_status.attributes, indent=4))


def fingerprint(args) -> None:
    """Save the vehicle fingerprint."""
    time_dir = Path.home() / 'vehicle_fingerprint' / time.strftime("%Y-%m-%d_%H-%M-%S")
    time_dir.mkdir(parents=True)

    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region),
                                    log_responses=time_dir)
    account.set_observer_position(args.lat, args.lng)
    if args.lat and args.lng:
        for vehicle in account.vehicles:
            vehicle.set_observer_position(args.lat, args.lng)
    account.update_vehicle_states()

    print('fingerprint of the vehicles written to {}'.format(time_dir))


def light_flash(args) -> None:
    """Trigger the vehicle to flash its lights."""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    vehicle = account.get_vehicle(args.vin)
    if not vehicle:
        valid_vins = ", ".join(v.vin for v in account.vehicles)
        print('Error: Could not find vehicle for VIN "{}". Valid VINs are: {}'.format(args.vin, valid_vins))
        return
    status = vehicle.remote_services.trigger_remote_light_flash()
    print(status.state)


def vehicle_finder(args) -> None:
    """Trigger the vehicle finder to locate it."""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    vehicle = account.get_vehicle(args.vin)
    if not vehicle:
        valid_vins = ", ".join(v.vin for v in account.vehicles)
        print('Error: Could not find vehicle for VIN "{}". Valid VINs are: {}'.format(args.vin, valid_vins))
        return
    status = vehicle.remote_services.trigger_remote_vehicle_finder()
    print(status.state)


def image(args) -> None:
    """Download a rendered image of the vehicle."""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    vehicle = account.get_vehicle(args.vin)

    with open('image.png', 'wb') as output_file:
        image_data = vehicle.get_vehicle_image(400, 400, VehicleViewDirection.FRONT)
        output_file.write(image_data)
    print('vehicle image saved to image.png')


def send_poi(args) -> None:
    """Send Point Of Interest to car."""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    vehicle = account.get_vehicle(args.vin)
    poi_data = dict(
        lat=args.latitude,
        lon=args.longitude,
        name=args.name,
        street=args.street,
        city=args.city,
        postal_code=args.postalcode,
        country=args.country
    )
    vehicle.remote_services.trigger_send_poi(poi_data)


def send_poi_from_address(args) -> None:
    """Create Point of Interest from OSM Nominatim and send to car."""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    vehicle = account.get_vehicle(args.vin)
    address = [(str(' '.join(args.address)))]
    try:
        response = requests.get("https://nominatim.openstreetmap.org",
                                params={
                                    "q": address,
                                    "format": "json",
                                    "addressdetails": 1,
                                    "limit": 1
                                }).json()[0]
    except IndexError:
        print('\nAddress not found')
        sys.exit(1)
    address = response.get("address", {})
    city = address.get("city")
    town = address.get("town")

    poi_data = dict(
        lat=response["lat"],
        lon=response["lon"],
        name=args.name,
        street=address.get("road"),
        city=town if city is None and town is not None else None,
        postal_code=address.get("postcode"),
        country=address.get("country")
    )
    vehicle.remote_services.trigger_send_poi(poi_data)


def send_message(args) -> None:
    """Send a message to car."""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    vehicle = account.get_vehicle(args.vin)
    msg_data = dict(
        text=args.text,
        subject=args.subject
    )
    vehicle.remote_services.trigger_send_message(msg_data)


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
    parser.set_defaults(func=get_status)


def main():
    """Main function."""
    parser = main_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
