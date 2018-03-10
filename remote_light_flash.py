#!/usr/bin/python3
"""Simple executable to demonstrate a remote light flash."""

import argparse
import logging
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.country_selector import Regions

def main():
    """Main function."""
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('password')
    parser.add_argument('vin')
    args = parser.parse_args()

    account = ConnectedDriveAccount(args.username, args.password, Regions.REST_OF_WORLD)
    vehicle = account.get_vehicle(args.vin)

    status = vehicle.remote_services.trigger_remote_light_flash()
    print(status.state)


if __name__ == '__main__':
    main()
