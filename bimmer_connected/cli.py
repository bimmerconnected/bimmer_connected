#!/usr/bin/python3
"""Simple executable to demonstrate and test the usage of the library."""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

from bimmer_connected.account import MyBMWAccount
from bimmer_connected.api.client import MyBMWClient
from bimmer_connected.api.regions import get_region_from_name, valid_regions
from bimmer_connected.utils import MyBMWJSONEncoder
from bimmer_connected.vehicle import MyBMWVehicle, VehicleViewDirection
from bimmer_connected.vehicle.vehicle import HV_BATTERY_DRIVE_TRAINS

TEXT_VIN = "Vehicle Identification Number"


def main_parser() -> argparse.ArgumentParser:
    """Creates the ArgumentParser with all relevant subparsers."""
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description="A simple executable to use and test the library.")
    subparsers = parser.add_subparsers(dest="cmd")
    subparsers.required = True

    status_parser = subparsers.add_parser("status", description="Get the current status of the vehicle.")
    status_parser.add_argument(
        "-j", "--json", help="Output as JSON only. Removes all other output.", action="store_true"
    )
    _add_default_arguments(status_parser)
    _add_position_arguments(status_parser)

    fingerprint_parser = subparsers.add_parser("fingerprint", description="Save a vehicle fingerprint.")
    _add_default_arguments(fingerprint_parser)
    _add_position_arguments(fingerprint_parser)
    fingerprint_parser.set_defaults(func=fingerprint)

    flash_parser = subparsers.add_parser("lightflash", description="Flash the vehicle lights.")
    _add_default_arguments(flash_parser)
    flash_parser.add_argument("vin", help=TEXT_VIN)
    flash_parser.set_defaults(func=light_flash)

    finder_parser = subparsers.add_parser("vehiclefinder", description="Update the vehicle GPS location.")
    _add_default_arguments(finder_parser)
    finder_parser.add_argument("vin", help=TEXT_VIN)
    _add_position_arguments(finder_parser)
    finder_parser.set_defaults(func=vehicle_finder)

    image_parser = subparsers.add_parser("image", description="Download a vehicle image.")
    _add_default_arguments(image_parser)
    image_parser.add_argument("vin", help=TEXT_VIN)
    image_parser.set_defaults(func=image)

    sendpoi_parser = subparsers.add_parser("sendpoi", description="Send a point of interest to the vehicle.")
    _add_default_arguments(sendpoi_parser)
    sendpoi_parser.add_argument("vin", help=TEXT_VIN)
    sendpoi_parser.add_argument("latitude", help="Latitude of the POI", type=float)
    sendpoi_parser.add_argument("longitude", help="Longitude of the POI", type=float)
    sendpoi_parser.add_argument("--name", help="(optional, display only) Name of the POI", nargs="?", default=None)
    sendpoi_parser.add_argument(
        "--street", help="(optional, display only) Street & House No. of the POI", nargs="?", default=None
    )
    sendpoi_parser.add_argument("--city", help="(optional, display only) City of the POI", nargs="?", default=None)
    sendpoi_parser.add_argument(
        "--postalcode", help="(optional, display only) Postal code of the POI", nargs="?", default=None
    )
    sendpoi_parser.add_argument(
        "--country", help="(optional, display only) Country of the POI", nargs="?", default=None
    )
    sendpoi_parser.set_defaults(func=send_poi)

    sendpoi_from_address_parser = subparsers.add_parser(
        "sendpoi_from_address", description=("Send a point of interest parsed from a street address to the vehicle.")
    )
    _add_default_arguments(sendpoi_from_address_parser)
    sendpoi_from_address_parser.add_argument("vin", help=TEXT_VIN)
    sendpoi_from_address_parser.add_argument(
        "-n", "--name", help="(optional, display only) Name of the POI", nargs="?", default=None
    )
    sendpoi_from_address_parser.add_argument(
        "-a", "--address", nargs="+", help="Address (e.g. 'Street 17, city, zip, country')"
    )
    sendpoi_from_address_parser.set_defaults(func=send_poi_from_address)

    return parser


async def get_status(args) -> None:
    """Get the vehicle status."""
    if args.json:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

    account = MyBMWAccount(args.username, args.password, get_region_from_name(args.region))
    if args.lat and args.lng:
        account.set_observer_position(args.lat, args.lng)
    await account.get_vehicles()

    if args.json:
        print(json.dumps(account.vehicles, cls=MyBMWJSONEncoder))
    else:
        print(f"Found {len(account.vehicles)} vehicles: {','.join([v.name for v in account.vehicles])}")

        for vehicle in account.vehicles:
            print(f"VIN: {vehicle.vin}")
            print(f"Mileage: {vehicle.status.mileage}")
            print("Vehicle data:")
            print(json.dumps(account.vehicles, cls=MyBMWJSONEncoder, indent=4))


def get_vehicle_or_return(account: MyBMWAccount, vin: str) -> MyBMWVehicle:
    """Get a vehicle by VIN or raise if not in account's vehicle list."""
    vehicle = account.get_vehicle(vin)
    if not vehicle:
        valid_vins = ", ".join(v.vin for v in account.vehicles)
        raise KeyError(f"Error: Could not find vehicle for VIN {vin}. Valid VINs are: {valid_vins}")
    return vehicle


async def fingerprint(args) -> None:
    """Save the vehicle fingerprint."""
    time_dir = Path.home() / "vehicle_fingerprint" / time.strftime("%Y-%m-%d_%H-%M-%S")
    time_dir.mkdir(parents=True)

    account = MyBMWAccount(args.username, args.password, get_region_from_name(args.region), log_responses=time_dir)
    if args.lat and args.lng:
        account.set_observer_position(args.lat, args.lng)
    await account.get_vehicles()

    # Patching in new My BMW endpoints for fingerprinting
    for vehicle in account.vehicles:
        if vehicle.drive_train in HV_BATTERY_DRIVE_TRAINS:
            print(f"Getting 'charging-sessions' for {vehicle.vin}")
            async with MyBMWClient(account.mybmw_client_config, brand=vehicle.brand) as client:
                await client.post(
                    "/eadrax-chs/v1/charging-sessions",
                    params={"vin": vehicle.vin, "maxResults": 40, "include_date_picker": "true"},
                )

                print(f"Getting 'charging-statistics' for {vehicle.vin}")
                await client.post(
                    "/eadrax-chs/v1/charging-statistics",
                    params={"vin": vehicle.vin, "currentDate": datetime.utcnow().isoformat()},
                )

    print(f"fingerprint of the vehicles written to {time_dir}")


async def light_flash(args) -> None:
    """Trigger the vehicle to flash its lights."""
    account = MyBMWAccount(args.username, args.password, get_region_from_name(args.region))
    await account.get_vehicles()
    vehicle = get_vehicle_or_return(account, args.vin)
    status = await vehicle.remote_services.trigger_remote_light_flash()
    print(status.state)


async def vehicle_finder(args) -> None:
    """Trigger the vehicle finder to locate it."""
    account = MyBMWAccount(args.username, args.password, get_region_from_name(args.region))
    account.set_observer_position(args.lat, args.lng)
    await account.get_vehicles()
    vehicle = get_vehicle_or_return(account, args.vin)
    status = await vehicle.remote_services.trigger_remote_vehicle_finder()
    print(status.state)
    print({"gps_position": vehicle.status.gps_position, "heading": vehicle.status.gps_heading})


async def image(args) -> None:
    """Download a rendered image of the vehicle."""
    account = MyBMWAccount(args.username, args.password, get_region_from_name(args.region))
    await account.get_vehicles()
    vehicle = get_vehicle_or_return(account, args.vin)

    for viewdirection in VehicleViewDirection:
        filename = str(viewdirection.name).lower() + ".png"
        with open(filename, "wb") as output_file:
            image_data = await vehicle.get_vehicle_image(viewdirection)
            output_file.write(image_data)
        print(f"vehicle image saved to {filename}")


async def send_poi(args) -> None:
    """Send Point Of Interest to car."""
    account = MyBMWAccount(args.username, args.password, get_region_from_name(args.region))
    await account.get_vehicles()
    vehicle = get_vehicle_or_return(account, args.vin)

    poi_data = {
        "lat": args.latitude,
        "lon": args.longitude,
        "name": args.name,
        "street": args.street,
        "city": args.city,
        "postal_code": args.postalcode,
        "country": args.country,
    }
    await vehicle.remote_services.trigger_send_poi(poi_data)


async def send_poi_from_address(args) -> None:
    """Create Point of Interest from OSM Nominatim and send to car."""
    account = MyBMWAccount(args.username, args.password, get_region_from_name(args.region))
    await account.get_vehicles()
    vehicle = get_vehicle_or_return(account, args.vin)

    query = [(str(" ".join(args.address)))]
    try:
        async with httpx.AsyncClient() as client:
            response: httpx.Response = await client.get(
                "https://nominatim.openstreetmap.org",
                params={"q": query, "format": "json", "addressdetails": 1, "limit": 1},
            )
            response_json = response.json()[0]
    except IndexError:
        print("\nAddress not found")
        sys.exit(1)
    address = response_json.get("address", {})
    city = address.get("city")
    town = address.get("town")

    poi_data = {
        "lat": response_json["lat"],
        "lon": response_json["lon"],
        "name": args.name,
        "street": address.get("road"),
        "city": town if city is None and town is not None else None,
        "postal_code": address.get("postcode"),
        "country": address.get("country"),
    }
    await vehicle.remote_services.trigger_send_poi(poi_data)


def _add_default_arguments(parser: argparse.ArgumentParser):
    """Add the default arguments username, password, region to the parser."""
    parser.add_argument("username", help="Connected Drive username")
    parser.add_argument("password", help="Connected Drive password")
    parser.add_argument("region", choices=valid_regions(), help="Region of the Connected Drive account")


def _add_position_arguments(parser: argparse.ArgumentParser):
    """Add the lat and lng attributes to the parser."""
    parser.add_argument("lat", type=float, nargs="?", const=0.0, help="(optional) Your current GPS latitude (as float)")
    parser.add_argument(
        "lng", type=float, nargs="?", const=0.0, help="(optional) Your current GPS longitude (as float)"
    )
    parser.set_defaults(func=get_status)


def main():
    """Main function."""
    parser = main_parser()
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(args.func(args))


if __name__ == "__main__":
    main()
