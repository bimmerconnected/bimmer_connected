#!/usr/bin/python3

import requests
import urllib
import argparse

AUTHENTICATION_URL = 'https://b2vapi.bmwgroup.us/webapi/oauth/token'
VEHICLES_URL = 'https://www.bmw-connecteddrive.de/api/me/vehicles/v2'


def get_token(username, password):
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    # we really need all of these parameters
    values = {
        'grant_type': 'password',
        'scope': 'authenticate_user vehicle_data remote_services',
        'username': username,
        'password': password,
    }

    data = urllib.parse.urlencode(values)
    response = requests.post(AUTHENTICATION_URL, data=data, headers=headers, allow_redirects=False)
    if response.status_code != 302:
        raise IOError('Unexpected status code: {}'.format(response.status_code))
    print('Response header:')
    print(response.headers)
    print('Response text:')
    print(response.text)
    response_json = response.json()
    token = response_json['access_token']
    return token


def list_vehicles(token):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer {}".format(token),
        "referer": "https://www.bmw-connecteddrive.de/app/index.html",
    }
    response = requests.get(VEHICLES_URL, headers=headers)
    if response.status_code != 200:
        raise IOError('Unexpected status code: {}'.format(response.status_code))
    print('Response header:')
    print(response.headers)
    print('Response text:')
    print(response.text)
    return response.json()


def main(username, password):
    token = get_token(username, password)
    print('Token: {}'.format(token))
    status = list_vehicles(token)
    print(status)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('password')
    args = parser.parse_args()
    main(args.username, args.password)
