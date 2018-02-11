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
    args = parser.parse_args()

    bimmer = BimmerConnected(args.vin, args.username, args.password)
    bimmer.remote_services.trigger_remote_light_flash()
    completed = False
    while not completed:
        status = bimmer.remote_services.get_remote_service_status()
        print(status.state)
        completed = status.state == ExecutionState.EXECUTED
        time.sleep(1)


if __name__ == '__main__':
    main()
