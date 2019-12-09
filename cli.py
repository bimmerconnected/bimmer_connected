#!/usr/bin/python3
"""Simple executable to demonstrate and test the usage of the library."""

import argparse
import logging
import json
import os
import time
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.country_selector import get_region_from_name, valid_regions
from bimmer_connected.vehicle import VehicleViewDirection, PointOfInterest

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

    chargenow_parser = subparsers.add_parser('chargenow', description='start vehicle charing immediately')
    _add_default_arguments(chargenow_parser)
    chargenow_parser.add_argument('vin', help='vehicle identification number')
    chargenow_parser.set_defaults(func=charge_now)

    getlasttrip_parser = subparsers.add_parser('lasttrip', description='get last trip details')
    _add_default_arguments(getlasttrip_parser)
    getlasttrip_parser.add_argument('vin', help='vehicle identification number')
    getlasttrip_parser.set_defaults(func=get_last_trip)
    
    getalltrips_parser = subparsers.add_parser('alltrips', description='get all trips efficiency data')
    _add_default_arguments(getalltrips_parser)
    getalltrips_parser.add_argument('vin', help='vehicle identification number')
    getalltrips_parser.set_defaults(func=get_all_trips)

    getchargingprofile_parser = subparsers.add_parser('chargingprofile', description='get charging schedules')
    _add_default_arguments(getchargingprofile_parser)
    getchargingprofile_parser.add_argument('vin', help='vehicle identification number')
    getchargingprofile_parser.set_defaults(func=get_vehicle_charging_profile)
    
    getdestinations_parser = subparsers.add_parser('destinations', description='get all destinations')
    _add_default_arguments(getdestinations_parser)
    getdestinations_parser.add_argument('vin', help='vehicle identification number')
    getdestinations_parser.set_defaults(func=get_vehicle_destinations)
   
    getrangemap_parser = subparsers.add_parser('rangemap', description='get range map')
    _add_default_arguments(getrangemap_parser)
    getrangemap_parser.add_argument('vin', help='vehicle identification number')
    getrangemap_parser.set_defaults(func=get_vehicle_rangemap)

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


def charge_now(args) -> None:
    """Trigger the vehicle to charge immediately."""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    vehicle = account.get_vehicle(args.vin)
    if not vehicle:
        valid_vins = ", ".join(v.vin for v in account.vehicles)
        print('Error: Could not find vehicle for VIN "{}". Valid VINs are: {}'.format(args.vin, valid_vins))
        return
    status = vehicle.remote_services.trigger_remote_charge_now()
    print(status.state)


def image(args) -> None:
    """Download a rendered image of the vehicle."""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    vehicle = account.get_vehicle(args.vin)

    with open('image.png', 'wb') as output_file:
        image_data = vehicle.get_vehicle_image(400, 400, VehicleViewDirection.FRONT)
        output_file.write(image_data)
    print('vehicle image saved to image.png')

def get_last_trip(args) -> None:
    """Downlad details of last trip"""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    vehicle = account.get_vehicle(args.vin)
    if not vehicle:
        valid_vins = ", ".join(v.vin for v in account.vehicles)
        print('Error: Could not find vehicle for VIN "{}". Valid VINs are: {}'.format(args.vin, valid_vins))
        return
    print(json.dumps(vehicle.get_vehicle_lasttrip(),indent=4))    

def get_all_trips(args) -> None:
    """Downlad statistics of all trips"""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    vehicle = account.get_vehicle(args.vin)
    if not vehicle:
        valid_vins = ", ".join(v.vin for v in account.vehicles)
        print('Error: Could not find vehicle for VIN "{}". Valid VINs are: {}'.format(args.vin, valid_vins))
        return
    print(json.dumps(vehicle.get_vehicle_alltrips(),indent=4))

def get_vehicle_charging_profile(args) -> None:
    """Download one-time and weekly charging schedules and settings"""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    vehicle = account.get_vehicle(args.vin)
    if not vehicle:
        valid_vins = ", ".join(v.vin for v in account.vehicles)
        print('Error: Could not find vehicle for VIN "{}". Valid VINs are: {}'.format(args.vin, valid_vins))
        return
    print(json.dumps(vehicle.get_vehicle_charging_profile(),indent=4))

def get_vehicle_destinations(args) -> None:
    """Shows the destinations you've previously sent to the car."""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    vehicle = account.get_vehicle(args.vin)
    if not vehicle:
        valid_vins = ", ".join(v.vin for v in account.vehicles)
        print('Error: Could not find vehicle for VIN "{}". Valid VINs are: {}'.format(args.vin, valid_vins))
        return
    print(json.dumps(vehicle.get_vehicle_destinations(),indent=4))

def get_vehicle_rangemap(args) -> None:
    """Get a set of lat/lon points defining a polygon bounding vehicle range"""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    vehicle = account.get_vehicle(args.vin)
    if not vehicle:
        valid_vins = ", ".join(v.vin for v in account.vehicles)
        print('Error: Could not find vehicle for VIN "{}". Valid VINs are: {}'.format(args.vin, valid_vins))
        return
    print(json.dumps(vehicle.get_vehicle_rangemap(),indent=4))


def send_poi(args) -> None:
    """Send Point Of Interest to car."""
    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
    vehicle = account.get_vehicle(args.vin)
    poi = PointOfInterest(args.latitude, args.longitude, name=args.name,
                          street=args.street, city=args.city, postalCode=args.postalcode, country=args.country)
    vehicle.send_poi(poi)


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
