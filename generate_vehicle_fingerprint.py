#!/usr/bin/python3
"""Store all responses from the backend in log files for later analysis."""

import argparse
import logging
import os
import shutil

from bimmer_connected import ConnectedDriveAccount

FINGERPRINT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'vehicle_fingerprint')


def main():
    """Store all responses from the backend in log files for later analysis."""
    logging.basicConfig(level=logging.WARNING)
    print('Generating vehicle fingerprint...')

    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('password')
    parser.add_argument('country')
    args = parser.parse_args()

    if os.path.exists(FINGERPRINT_DIR):
        shutil.rmtree(FINGERPRINT_DIR)

    os.mkdir(FINGERPRINT_DIR)

    account = ConnectedDriveAccount(args.username, args.password, args.country, log_responses=FINGERPRINT_DIR)
    account.update_vehicle_states()

    print('fingerprint of the vehicles written to {}'.format(FINGERPRINT_DIR))


if __name__ == '__main__':
    main()
