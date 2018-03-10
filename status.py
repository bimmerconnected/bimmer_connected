#!/usr/bin/python3
"""Simple executable to demonstrate and test the usage of the library."""

import argparse
import logging
import json
from bimmer_connected.account import ConnectedDriveAccount
from bimmer_connected.country_selector import get_region_from_name, valid_regions


def main():
    """Main function."""
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('password')
    parser.add_argument('region', choices=valid_regions())
    args = parser.parse_args()

    account = ConnectedDriveAccount(args.username, args.password, get_region_from_name(args.region))
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
        #print('vehicle specs:')
        #print(json.dumps(vehicle.specs.attributes, indent=4))


if __name__ == '__main__':
    main()
