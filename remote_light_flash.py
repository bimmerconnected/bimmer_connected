#!/usr/bin/python3
"""Simple executable to demonstrate a remote light flash."""

import argparse
import logging
import time
from bimmer_connected import BimmerConnected
from bimmer_connected.remote_services import ExecutionState


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
    status = bimmer.remote_services.trigger_remote_light_flash()
    while status.state != ExecutionState.EXECUTED:
        status = bimmer.remote_services.get_remote_service_status()
        print(status.state)
        time.sleep(1)


if __name__ == '__main__':
    main()
