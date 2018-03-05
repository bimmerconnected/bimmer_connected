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
        'username': username,
        'password': password,
        # not sure what this id really means, random numbers do no work here.
        'client_id': 'dbf0a542-ebd1-4ff0-a9a7-55172fbfce35',
        # you might have to change this for the Canadian site
        'redirect_uri': 'https://www.bmw-connecteddrive.com/app/default/static/external-dispatch.html',
        'response_type': 'token',
        'scope': 'authenticate_user fupo',
        # random 79 characters
        'state': 'ez8nx9wn8a48s058hp9vj8mhs9sg9ltbp6yqg84pk7s3miev3omvi7bg6epp3gpuphxyvd6wiaz3zoq'
    }

    data = urllib.parse.urlencode(values)
    response = requests.post(AUTHENTICATION_URL, data=data, headers=headers, allow_redirects=False)
    if response.status_code != 302:
        raise IOError('Unexpected status code: {}'.format(response.status_code))
    print('Response header:')
    print(response.headers)
    print('Response text:')
    print(response.text)
    url_with_token = urllib.parse.parse_qs(response.headers['Location'])
    token = url_with_token['access_token'][0]
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
