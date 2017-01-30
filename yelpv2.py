# -*- coding: utf-8 -*-
"""
Yelp Fusion API code sample.

This program demonstrates the capability of the Yelp Fusion API
by using the Search API to query for businesses by a search term and location,
and the Business API to query additional information about the top result
from the search query.

Please refer to http://www.yelp.com/developers/v3/documentation for the API
documentation.

This program requires the Python requests library, which you can install via:
`pip install -r requirements.txt`.

Sample usage of the program:
`python sample.py --term="bars" --location="San Francisco, CA"`
"""
from __future__ import print_function

import argparse
import json
import pprint
import requests
import sys
import urllib
from oauth2client.service_account import ServiceAccountCredentials
import datetime
from oauth2client.file import Storage
import os
import httplib2
import codecs
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
import time





# This client code can run on Python 2.x or 3.x.  Your imports can be
# simpler if you only need one of those.
try:
    # For Python 3.0 and later
    from urllib.error import HTTPError
    from urllib.parse import quote
    from urllib.parse import urlencode
except ImportError:
    # Fall back to Python 2's urllib2 and urllib
    from urllib2 import HTTPError
    from urllib import quote
    from urllib import urlencode


flags = None

# OAuth credential placeholders that must be filled in by users.
# You can find them on
# https://www.yelp.com/developers/v3/manage_app
CLIENT_ID = '0VmmLZDQ6ne5f3zB8grdPw'
CLIENT_SECRET = 'jWzfg0b12qvvx9Tsyeil4qeL3BZPsvtPOhFpNr1Y0feQX1IZsZF70RtmFErwzfuC'


# API constants, you shouldn't have to change these.
API_HOST = 'https://api.yelp.com'
SEARCH_PATH = '/v3/businesses/search'
BUSINESS_PATH = '/v3/businesses/'  # Business ID will come after slash.
TOKEN_PATH = '/oauth2/token'
GRANT_TYPE = 'client_credentials'


# Defaults for our simple example.
DEFAULT_TERM = 'cocktail bars'
DEFAULT_CATEGORY = 'Home Cleaning'
DEFAULT_LOCATION = 'San Francisco, CA'
DEFAULT_SORT = 2
SEARCH_LIMIT = 50
SEARCH_OFFSET = SEARCH_LIMIT * 1
#Default for google spreadsheets
DEFAULT_SHEET = 'default'
DEFAULT_GOOGLE_CREDENTIALS_FILENAME = 'client_secret.json'
SCOPES = 'https://www.googleapis.com/auth/drive'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Scraper'
SPREADSHEET_ID = "1oCjKJWRWPODDobGfoCLnCYzvCx37EoMdWVX7fNTMfWU"


def obtain_bearer_token(host, path):
    """Given a bearer token, send a GET request to the API.

    Args:
        host (str): The domain host of the API.
        path (str): The path of the API after the domain.
        url_params (dict): An optional set of query parameters in the request.

    Returns:
        str: OAuth bearer token, obtained using client_id and client_secret.

    Raises:
        HTTPError: An error occurs from the HTTP request.
    """
    url = '{0}{1}'.format(host, quote(path.encode('utf8')))
    assert CLIENT_ID, "Please supply your client_id."
    assert CLIENT_SECRET, "Please supply your client_secret."
    data = urlencode({
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': GRANT_TYPE,
    })
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
    }
    response = requests.request('POST', url, data=data, headers=headers)
    bearer_token = response.json()['access_token']
    return bearer_token


def request(host, path, bearer_token, url_params=None):
    """Given a bearer token, send a GET request to the API.

    Args:
        host (str): The domain host of the API.
        path (str): The path of the API after the domain.
        bearer_token (str): OAuth bearer token, obtained using client_id and client_secret.
        url_params (dict): An optional set of query parameters in the request.

    Returns:
        dict: The JSON response from the request.

    Raises:
        HTTPError: An error occurs from the HTTP request.
    """
    url_params = url_params or {}
    url = '{0}{1}'.format(host, quote(path.encode('utf8')))
    headers = {
        'Authorization': 'Bearer %s' % bearer_token,
    }

    print(u'Querying {0} ...'.format(url))

    response = requests.request('GET', url, headers=headers, params=url_params)

    return response.json()


def search(bearer_token, term, location):
    """Query the Search API by a search term and location.

    Args:
        term (str): The search term passed to the API.
        location (str): The search location passed to the API.

    Returns:
        dict: The JSON response from the request.
    """

    url_params = {
        'term': term.replace(' ', '+'),
        'location': location.replace(' ', '+'),
        #'category_filter': DEFAULT_CATEGORY,
        'sort':  DEFAULT_SORT,
        'limit': SEARCH_LIMIT,
        'offset': SEARCH_OFFSET
    }
    return request(API_HOST, SEARCH_PATH, bearer_token, url_params=url_params)


def get_business(bearer_token, business_id):
    """Query the Business API by a business ID.

    Args:
        business_id (str): The ID of the business to query.

    Returns:
        dict: The JSON response from the request.
    """
    business_path = BUSINESS_PATH + business_id

    return request(API_HOST, business_path, bearer_token)


def query_api(term, location,filename):
    """Queries the API by the input values from the user.

    Args:
        term (str): The search term to query.
        location (str): The location of the business to query.
    """
    bearer_token = obtain_bearer_token(API_HOST, TOKEN_PATH)

    response = search(bearer_token, term, location)

    businesses = response.get('businesses')

    if not businesses:
        print(u'No businesses for {0} in {1} found.'.format(term, location))
        return

    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)
    headers = []
    for k,v in sorted(businesses[0].iteritems()):
        if k=='location':
            headers.extend(['city','display_adress','zip_code','state'])
        elif k=='categories':
            headers.extend(['categories title'])
        elif k=='image_url':
            pass
        else:
            headers.append(k)

    append_to_google_spreadsheet(service,term,filename,headers)
    for business in businesses:
        ret = []
        for k,v in sorted(business.iteritems()):
            if k=='location':
                ret.extend(
                    [v['city'],
                    " ".join(v['display_address']),
                    v['zip_code'],
                    v['state']])
            elif k=='categories':
                ret.extend([",".join([i['title'] for i in v])])
            elif k=='image_url':
                pass
            else:
                ret.append(str(v))

        #here is the call to more info on yelp, but they looks the same like the global api call so I would suggest we dont call that because of API limitations
        #bussnies_info = get_business(bearer_token,business['id'])
        append_to_google_spreadsheet(service,term,filename,ret)

def append_to_google_spreadsheet(service,term,filename,row):
    time.sleep(1) #add sleep because of google api

    values =  [row]
    body ={'values':values}
    rangeName = "%s"%filename
    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        body=body,
        range=rangeName,
        includeValuesInResponse='false',
        valueInputOption='RAW'
        ).execute()


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    credential_path = os.path.join(os.path.abspath("."),'sheets.googleapis.com-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    try:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
    except:
        print("%s file not found(exiting)"%CLIENT_SECRET_FILE)
        import sys
        sys.exit()

    flow.user_agent = APPLICATION_NAME
    if not credentials or credentials.invalid:
        flags = tools.argparser.parse_args(args=[])
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store,flags)
        print('Storing credentials to ' + credential_path)
    return credentials


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-q', '--term', dest='term', default=DEFAULT_TERM,
                        type=str, help='Search term (default: %(default)s)')
    parser.add_argument('-l', '--location', dest='location',
                        default=DEFAULT_LOCATION, type=str,
                        help='Search location (default: %(default)s)')
    parser.add_argument('-gs','--google_sheet',dest='google_sheet',
                        default=DEFAULT_SHEET,type=str,help='Sheet name(default: %(default)s)'
                        )

    input_values = parser.parse_args()

    try:
        query_api(input_values.term, input_values.location,input_values.google_sheet)
    except HTTPError as error:
        sys.exit(
            'Encountered HTTP error {0} on {1}:\n {2}\nAbort program.'.format(
                error.code,
                error.url,
                error.read(),
            )
        )


if __name__ == '__main__':
    main()



#
# row = len(wks.col_values(1))+1
# wks.update_cell(row, 1, name)
