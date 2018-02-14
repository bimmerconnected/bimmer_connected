#!/usr/bin/python3
"""Simple executable to demonstrate and test the usage of the library."""

import argparse
import logging
import json
from bimmer_connected import ConnectedDriveAccount


def main():
    """Main function."""
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('password')
    parser.add_argument('country')
    args = parser.parse_args()

    account = ConnectedDriveAccount(args.username, args.password, args.country)

    print('Found {} vehicles: {}'.format(
        len(account.vehicles),
        ','.join([v.modelName for v in account.vehicles])))

    for vehicle in account.vehicles:
        print('VIN: {}'.format(vehicle.vin))
        print('Response from the server:')
        print(json.dumps(vehicle.state.attributes, indent=4))


if __name__ == '__main__':
    main()
