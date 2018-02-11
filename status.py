#!/usr/bin/python3
"""Simple executable to demonstrate and test the usage of the library."""

import argparse
import logging
import json
from bimmer_connected import BimmerConnected


def main():
    """Main function."""
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('password')
    parser.add_argument('vin')
    parser.add_argument('country')
    args = parser.parse_args()

    bimmer = BimmerConnected(args.vin, args.username, args.password, args.country)
    bimmer.update_data()

    print('Response from the server:')
    print(json.dumps(bimmer.attributes, indent=4))


if __name__ == '__main__':
    main()
