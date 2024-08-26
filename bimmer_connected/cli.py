#!/usr/bin/python3
"""Simple executable to demonstrate and test the usage of the library."""

import argparse
import asyncio
import contextlib
import json
import logging
import sys
import time
from pathlib import Path

import httpx

from bimmer_connected import __version__ as VERSION
from bimmer_connected.account import MyBMWAccount
from bimmer_connected.api.regions import get_region_from_name, valid_regions
from bimmer_connected.const import DEFAULT_POI_NAME
from bimmer_connected.utils import MyBMWJSONEncoder, log_response_store_to_file
from bimmer_connected.vehicle import MyBMWVehicle, VehicleViewDirection
from bimmer_connected.vehicle.charging_profile import ChargingMode

TEXT_VIN = "Vehicle Identification Number"


def main_parser() -> argparse.ArgumentParser:
    """Create the ArgumentParser with all relevant subparsers."""
    parser = argparse.ArgumentParser(
        description=(f"Connect to MyBMW/MINI API and interact with your vehicle.\n\nVersion: {VERSION}"),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--debug", help="Print debug logs.", action="store_true")
    parser.add_argument(
        "--oauth-store",
        help="Path to the OAuth2 storage file. Defaults to $HOME/.bimmer_connected.json.",
        nargs="?",
        metavar="FILE",
        type=Path,
        default=Path.home() / ".bimmer_connected.json",
    )
    parser.add_argument("--disable-oauth-store", help="Disable storing the OAuth2 tokens.", action="store_true")

    subparsers = parser.add_subparsers(dest="cmd")
    subparsers.required = True

    status_parser = subparsers.add_parser("status", description="Get the current status of the vehicle.")
    status_parser.add_argument(
        "-j", "--json", help="Output as JSON only. Removes all other output.", action="store_true"
    )
    status_parser.add_argument("-v", "--vin", help="Output data for specified VIN only.", type=str, nargs="?")

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

    horn_parser = subparsers.add_parser("horn", description="Trigger the vehicle horn")
    _add_default_arguments(horn_parser)
    horn_parser.add_argument("vin", help=TEXT_VIN)
    horn_parser.set_defaults(func=horn)

    finder_parser = subparsers.add_parser("vehiclefinder", description="Update the vehicle GPS location.")
    _add_default_arguments(finder_parser)
    finder_parser.add_argument("vin", help=TEXT_VIN)
    _add_position_arguments(finder_parser)
    finder_parser.set_defaults(func=vehicle_finder)

    chargingsettings_parser = subparsers.add_parser("chargingsettings", description="Set vehicle charging settings.")
    _add_default_arguments(chargingsettings_parser)
    chargingsettings_parser.add_argument("vin", help=TEXT_VIN)
    chargingsettings_parser.add_argument("--target-soc", help="Desired charging target SoC", nargs="?", type=int)
    chargingsettings_parser.add_argument("--ac-limit", help="Maximum AC limit", nargs="?", type=int)
    chargingsettings_parser.set_defaults(func=chargingsettings)

    chargingprofile_parser = subparsers.add_parser("chargingprofile", description="Set vehicle charging profile.")
    _add_default_arguments(chargingprofile_parser)
    chargingprofile_parser.add_argument("vin", help=TEXT_VIN)
    chargingprofile_parser.add_argument(
        "--charging-mode",
        help="Desired charging mode",
        nargs="?",
        type=ChargingMode,
        choices=[cm.value for cm in ChargingMode if cm != ChargingMode.UNKNOWN],
    )
    chargingprofile_parser.add_argument(
        "--precondition-climate", help="Precondition climate on charging windows", nargs="?", type=bool
    )
    chargingprofile_parser.set_defaults(func=chargingprofile)

    charge_parser = subparsers.add_parser("charge", description="Start/stop charging on enabled vehicles.")
    _add_default_arguments(charge_parser)
    charge_parser.add_argument("vin", help=TEXT_VIN)
    charge_parser.add_argument("action", type=str, choices=["start", "stop"])
    charge_parser.set_defaults(func=charge)

    image_parser = subparsers.add_parser("image", description="Download a vehicle image.")
    _add_default_arguments(image_parser)
    image_parser.add_argument("vin", help=TEXT_VIN)
    image_parser.set_defaults(func=image)

    sendpoi_parser = subparsers.add_parser("sendpoi", description="Send a point of interest to the vehicle.")
    _add_default_arguments(sendpoi_parser)
    sendpoi_parser.add_argument("vin", help=TEXT_VIN)
    sendpoi_parser.add_argument("latitude", help="Latitude of the POI", type=float)
    sendpoi_parser.add_argument("longitude", help="Longitude of the POI", type=float)
    sendpoi_parser.add_argument("--name", help="Name of the POI", nargs="?", default=DEFAULT_POI_NAME)
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


async def get_status(account: MyBMWAccount, args) -> None:
    """Get the vehicle status."""
    if args.json:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

    await account.get_vehicles()

    if args.json:
        if args.vin:
            print(json.dumps(get_vehicle_or_return(account, args.vin), cls=MyBMWJSONEncoder))
        else:
            print(json.dumps(account.vehicles, cls=MyBMWJSONEncoder))
    else:
        print(f"Found {len(account.vehicles)} vehicles: {','.join([v.name for v in account.vehicles])}")

        for vehicle in account.vehicles:
            if args.vin and vehicle.vin != args.vin:
                continue
            print(f"VIN: {vehicle.vin}")
            print(f"Mileage: {vehicle.mileage.value} {vehicle.mileage.unit}")
            print("Vehicle data:")
            print(json.dumps(account.vehicles, cls=MyBMWJSONEncoder, indent=4))


def get_vehicle_or_return(account: MyBMWAccount, vin: str) -> MyBMWVehicle:
    """Get a vehicle by VIN or raise if not in account's vehicle list."""
    vehicle = account.get_vehicle(vin)
    if not vehicle:
        valid_vins = ", ".join(v.vin for v in account.vehicles)
        raise KeyError(f"Error: Could not find vehicle for VIN {vin}. Valid VINs are: {valid_vins}")
    return vehicle


async def fingerprint(account: MyBMWAccount, args) -> None:
    """Save the vehicle fingerprint."""
    time_dir = Path.home() / "vehicle_fingerprint" / time.strftime("%Y-%m-%d_%H-%M-%S")
    time_dir.mkdir(parents=True)

    account.config.log_responses = True
    await account.get_vehicles()

    log_response_store_to_file(account.get_stored_responses(), time_dir)
    print(f"fingerprint of the vehicles written to {time_dir}")


async def light_flash(account: MyBMWAccount, args) -> None:
    """Trigger the vehicle to flash its lights."""
    await account.get_vehicles()
    vehicle = get_vehicle_or_return(account, args.vin)
    status = await vehicle.remote_services.trigger_remote_light_flash()
    print(status.state)


async def horn(account: MyBMWAccount, args) -> None:
    """Trigger the vehicle to horn."""
    await account.get_vehicles()
    vehicle = get_vehicle_or_return(account, args.vin)
    status = await vehicle.remote_services.trigger_remote_horn()
    print(status.state)


async def vehicle_finder(account: MyBMWAccount, args) -> None:
    """Trigger the vehicle finder to locate it."""
    account.set_observer_position(args.lat, args.lng)
    await account.get_vehicles()
    vehicle = get_vehicle_or_return(account, args.vin)
    status = await vehicle.remote_services.trigger_remote_vehicle_finder()
    print(status.state)
    print({"gps_position": vehicle.vehicle_location.location, "heading": vehicle.vehicle_location.heading})


async def chargingsettings(account: MyBMWAccount, args) -> None:
    """Trigger a change to charging settings."""
    if not args.target_soc and not args.ac_limit:
        raise ValueError("At least one of 'charging-target' and 'ac-limit' has to be provided.")
    await account.get_vehicles()
    vehicle = get_vehicle_or_return(account, args.vin)
    status = await vehicle.remote_services.trigger_charging_settings_update(
        target_soc=args.target_soc, ac_limit=args.ac_limit
    )
    print(status.state)


async def chargingprofile(account: MyBMWAccount, args) -> None:
    """Trigger a change to charging profile."""
    if not args.charging_mode and not args.precondition_climate:
        raise ValueError("At least one of 'charging-mode' and 'precondition-climate' has to be provided.")
    await account.get_vehicles()
    vehicle = get_vehicle_or_return(account, args.vin)
    status = await vehicle.remote_services.trigger_charging_profile_update(
        charging_mode=args.charging_mode, precondition_climate=args.precondition_climate
    )
    print(status.state)


async def charge(account: MyBMWAccount, args) -> None:
    """Trigger a vehicle to start or stop charging."""
    await account.get_vehicles()
    vehicle = get_vehicle_or_return(account, args.vin)
    status = await getattr(vehicle.remote_services, f"trigger_charge_{args.action.lower()}")()
    print(status.state)


async def image(account: MyBMWAccount, args) -> None:
    """Download a rendered image of the vehicle."""
    await account.get_vehicles()
    vehicle = get_vehicle_or_return(account, args.vin)

    for viewdirection in VehicleViewDirection:
        if viewdirection == VehicleViewDirection.UNKNOWN:
            continue
        filename = (Path.cwd() / str(viewdirection.name).lower()).with_suffix(".png")
        await asyncio.to_thread(filename.write_bytes, await vehicle.get_vehicle_image(viewdirection))
        print(f"vehicle image saved to {filename}")


async def send_poi(account: MyBMWAccount, args) -> None:
    """Send Point Of Interest to car."""
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


async def send_poi_from_address(account: MyBMWAccount, args) -> None:
    """Create Point of Interest from OSM Nominatim and send to car."""
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
    """Get arguments from parser and run function in event loop."""
    parser = main_parser()
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger("asyncio").setLevel(logging.WARNING)

    account = MyBMWAccount(args.username, args.password, get_region_from_name(args.region))

    if args.oauth_store.exists():
        with contextlib.suppress(json.JSONDecodeError):
            account.set_refresh_token(**json.loads(args.oauth_store.read_text()))

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(args.func(account, args))
    except Exception as ex:  # pylint: disable=broad-except
        sys.stderr.write(f"{type(ex).__name__}: {ex}\n")
        sys.exit(1)

    if args.disable_oauth_store:
        return

    args.oauth_store.parent.mkdir(parents=True, exist_ok=True)
    args.oauth_store.write_text(
        json.dumps(
            {
                "refresh_token": account.config.authentication.refresh_token,
                "gcid": account.config.authentication.gcid,
                "access_token": account.config.authentication.access_token,
            }
        ),
    )


if __name__ == "__main__":
    main()
