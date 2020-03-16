#!/usr/bin/python3
"""Simple executable to demonstrate and test the usage of the library."""

import argparse
import logging
import json
import os
import time
import sys

import requests

from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.country_selector import get_region_from_name, valid_regions
from bimmer_connected.vehicle import VehicleViewDirection, PointOfInterest, Message

FINGERPRINT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'vehicle_fingerprint')


def main() -> None:
    """Main function."""
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='demo script to show usage of the bimmer_connected library')
    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.required = True

    status_parser = subparsers.add_parser('status', description='get current status of the vehicle')
    _add_default_arguments(status_parser)
    _add_position_arguments(status_parser)

    fingerprint_parser = subparsers.add_parser('fingerprint', description='save a vehicle fingerprint')
    _add_default_arguments(fingerprint_parser)
    _add_position_arguments(fingerprint_parser)
    fingerprint_parser.set_defaults(func=fingerprint)

    flash_parser = subparsers.add_parser('lightflash', description='flash the vehicle lights')
    _add_default_arguments(flash_parser)
    flash_parser.add_argument('vin', help='vehicle identification number')
    flash_parser.set_defaults(func=light_flash)

    image_parser = subparsers.add_parser('image', description='download a vehicle image')
    _add_default_arguments(image_parser)
    image_parser.add_argument('vin', help='vehicle identification number')
    image_parser.set_defaults(func=image)

    sendpoi_parser = subparsers.add_parser('sendpoi', description='send a point of interest to the vehicle')
    _add_default_arguments(sendpoi_parser)
    sendpoi_parser.add_argument('vin', help='vehicle identification number')
    sendpoi_parser.add_argument('latitude', help='latitude of the POI', type=float)
    sendpoi_parser.add_argument('longitude', help='longitude of the POI', type=float)
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
                                                        description=('send a point of interest from a street address'
                                                                     ' to the vehicle'))
    _add_default_arguments(sendpoi_from_address_parser)
    sendpoi_from_address_parser.add_argument('vin', help='vehicle identification number')
    sendpoi_from_address_parser.add_argument('-n', '--name', help='(optional, display only) Name of the POI',
                                             nargs='?', default=None)
    sendpoi_from_address_parser.add_argument('-a', '--address', nargs='+',
                                             help="address ('street, city, zip, country' etc)")
    sendpoi_from_address_parser.set_defaults(func=send_poi_from_address)

    message_parser = subparsers.add_parser('sendmessage', description='send a text message to the vehicle')
    _add_default_arguments(message_parser)
    message_parser.add_argument('vin', help='vehicle identification number')
    message_parser.add_argument('text', help='text to be sent')
    message_parser.add_argument('subject', help='(optional) message subject', nargs='?')
    message_parser.set_defaults(func=send_message)

    args = parser.parse_args()
    args.func(args)


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
        print('mileage: {}'.format(vehicle.state.mileage))
        print('vehicle properties:')
        print(json.dumps(vehicle.attributes, indent=4))
        print('vehicle status:')
        print(json.dumps(vehicle.state.attributes, indent=4))


def fingerprint(args) -> None:
    """Save the vehicle fingerprint."""
    time_str = time.strftime("%Y-%m-%d_%H-%M-%S")
    time_dir = os.path.join(FINGERPRINT_DIR, time_str)
    os.makedirs(time_dir)

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
    poi = PointOfInterest(args.latitude, args.longitude, name=args.name,
                          street=args.street, city=args.city, postalCode=args.postalcode, country=args.country)
    msg = Message.from_poi(poi)
    vehicle.send_message(msg)


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
    lat = response["lat"]
    long = response["lon"]
    name = args.name
    address = response.get("address", {})
    street = address.get("road")
    city = address.get("city")
    town = address.get("town")
    city = town if city is None and town is not None else None
    postcode = address.get("postcode")
    country = address.get("country")

    print("\nSending '" + lat, long, name, street, city, postcode, country + "' to your car\n")
    poi = PointOfInterest(lat, long, name=args.name, street=street, city=city, postalCode=postcode, country=country)
    msg = Message.from_poi(poi)
    vehicle.send_message(msg)


def send_message(args) -> None:
    """Send Point Of Interest to car."""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    vehicle = account.get_vehicle(args.vin)
    msg = Message.from_text(args.text, args.subject)
    vehicle.send_message(msg)


def _add_default_arguments(parser: argparse.ArgumentParser):
    """Add the default arguments username, password, region to the parser."""
    parser.add_argument('username', help='Connected Drive user name')
    parser.add_argument('password', help='Connected Drive password')
    parser.add_argument('region', choices=valid_regions(), help='Region of the Connected Drive account')


def _add_position_arguments(parser: argparse.ArgumentParser):
    """Add the lat and lng attributes to the parser."""
    parser.add_argument('lat', type=float, nargs='?', const=0.0,
                        help='optional: your gps latitide (as float)')
    parser.add_argument('lng', type=float, nargs='?', const=0.0,
                        help='optional: your gps longitude (as float)')
    parser.set_defaults(func=get_status)


if __name__ == '__main__':
    main()
