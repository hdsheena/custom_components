import logging
import string
import xml.etree.ElementTree as ET
import sys


import requests


_LOGGER = logging.getLogger(__name__)
c_handler = logging.StreamHandler(sys.stdout)
c_handler.setLevel(logging.DEBUG)

_LOGGER.addHandler(c_handler)
logging.basicConfig(level=logging.DEBUG)

DOMAIN = 'bchydro'

DEFAULT_TIMEOUT = 10
CONF_ACCOUNT_NUMBER = 'account_number'
CONF_SLID = 'slid'
bchydro_username = "email"
bchydro_password = "pw"
bchydro_account_number = "acctnum"
bchydro_slid = "slid"

def setup_platform( add_devices, discovery_info=None):
    """Setup the sensor platform."""
    api = Api(bchydro_username,
              bchydro_password,
              bchydro_account_number,
              bchydro_slid,
              DEFAULT_TIMEOUT)
    add_devices([BCHydroUsageSensor(api)], True)

class BCHydroUsageSensor():
    def __init__(self, api):
        """Initialize the sensor."""
        self._api = api
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'BC Hydro Usage'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        return 'kWh'

    def update(self):
        """Fetch new state data for the sensor."""
        self._state = self._api.latest_usage()


URL_LOGIN = "https://app.bchydro.com/sso/UI/Login"
URL_GET_USAGE = "https://app.bchydro.com/evportlet/SystemServices/main?system:runTemplate=html/indicators/AccountProfile.xml"
# to get all the usage within a timeframe, use this url instead
#url_detailed_usage = "https://app.bchydro.com/evportlet/SystemServices/main?system:runTemplate=html/indicators/Consumption.xml"
URL_GET_USAGE = "https://app.bchydro.com/evportlet/web/account-profile-data.html"
# probably not all these fields are needed..
# Slid: self._slid
# Account: self._account_number
# ChartType: column
# Granularity: hourly
# Overlays: <OverlayId>none</OverlayId>
# StartDateTime: 2019-08-05T00:00:00-07:00
# EndDateTime: 2019-08-05T23:59:59-07:00
# DateRange: currentBill
# HeatingType: N
# PremiseType: 10
# PostalCode: <<DEFINE>>
# BillingArea: <<TWO DIGIT NUMBER>>
# ValidityStart: 2018-04-27T00:00:00-07:00
# ValidityEnd: 9999-12-31T00:00:00-08:00
# MRU: <<Some letters and numbers>>
# BillingClass: Residential
# EnablementDate: <<account start date?>>
# UserClick: 
# RateGroup: RES1

class Api:
    def __init__(self, username, password, account_number, slid, timeout=10):
        """Initialize the sensor."""
        self._username = username
        self._password = password
        self._account_number = account_number
        self._slid = slid
        self._timeout = timeout

    def login(self):
        r = self._call_api(
            "post",
            URL_LOGIN,
            data={
                "realm": "bch-ps",
                'email': self._username,
                'password': self._password,
                'gotoUrl':"https://app.bchydro.com:443/BCHCustomerPortal/web/login.html"

            }, allow_redirects=False)
        jar = r.cookies
        iterationNumber = 1

        while r.status_code == 302:
            print("-----------JAR   "+str(iterationNumber))
            print(jar)            
            print("-----------HEADERS   "+str(iterationNumber))

            print(r.headers)
            redirect_URL2 = r.headers['Location']
            r = requests.get(redirect_URL2, cookies=jar)
            jar.update(r.cookies)
            iterationNumber += 1
    
        return jar

    def latest_usages(self):
        """Fetch new state data for the sensor."""
        auth_cookies = self.login()
        r = self._call_api(
            "post",
            URL_GET_USAGE,
            data={
                "Slid": self._slid,
                "Account": self._account_number,
                "ValidityStart": '2015-09-03T00:00:00.000-07:00',
                "ValidityEnd": '9999-12-31T00:00:00.000-08:00'
            }, cookies=auth_cookies)

        latest_usage = None
        r = r.text
        resultingCleanString = ''.join(filter(lambda x: x in string.printable, r)) # This is the line that I added (with import above)
        print(resultingCleanString)
        root = ET.fromstring(resultingCleanString)
        # run through all the "points" in the series one at a time.
        for point in root.findall('Series')[0].findall('Point'):
            # By checking for invalid, you're reassigning this variable for each point, until 
            # they're invalid, which means you're getting the last valid point. This strikes me as a terribly inelegant
            # solution but what do i know?
            if point.get('quality') != 'INVALID':
                latest_usage = point.get('value')

        return latest_usage

    def _call_api(self, method, url, **kwargs):
        payload = kwargs.get("params") or kwargs.get("data")

        _LOGGER.info("About to call %s with payload=%s", url, payload)

        response = requests.request(method, url, timeout=self._timeout, **kwargs)

        _LOGGER.debug("Received API response: %s, %s",
                      response.status_code,
                      response.headers)

        response.raise_for_status()
        return response



def loginista(self):
        r = self._call_api(
            "post",
            URL_LOGIN,
            data={
                "realm": "bch-ps",
                'email': bchydro_username,
                'password': bchydro_password,
                'gotoUrl':"https://app.bchydro.com:443/BCHCustomerPortal/web/login.html"
            }, allow_redirects=False)
        _LOGGER.debug("%s",r.cookies)
        return r.cookies

def latest_usage(self):
        """Fetch new state data for the sensor."""
        auth_cookies = self.login()
        print("Here is a cookie ----------------------------------")
        print(auth_cookies)
        print("That was a cookie ----------------------------------")

        r = self._call_api(
            "get",
            URL_GET_USAGE,
             headers={"X-Requested-With": "XMLHttpRequest","Content-Type": "application/x-www-form-urlencoded"},data={
                "Slid": bchydro_slid,
                "Account": bchydro_account_number,
                "ValidityStart": '2015-09-03T00:00:00.000-07:00',
                "ValidityEnd": '9999-12-31T00:00:00.000-08:00'
            }, cookies=auth_cookies,allow_redirects=False)

        latest_usage = None
        #print(r)
        r = r.text
        print(r)
        resultingCleanString = ''.join(filter(lambda x: x in string.printable, r)) # This is the line that I added (with import above)
        #print(resultingCleanString)
        root = ET.fromstring(resultingCleanString)
        # run through all the "points" in the series one at a time.
        for point in root.findall('Series')[0].findall('Point'):
            # By checking for invalid, you're reassigning this variable for each point, until 
            # they're invalid, which means you're getting the last valid point. This strikes me as a terribly inelegant
            # solution but what do i know?
            if point.get('quality') != 'INVALID':
                latest_usage = point.get('value')
                print(latest_usage)

        return latest_usage

def call_api(self, method, url, **kwargs):
        payload = kwargs.get("params") or kwargs.get("data")

        _LOGGER.debug("About to call %s with payload=%s", url, payload)

        response = requests.request(method, url, timeout=self._timeout, **kwargs)

        _LOGGER.debug("Received API response: %s, %s",
                      response.status_code,
                      response.headers)

        response.raise_for_status()

        return response

x = Api(bchydro_username, bchydro_password, bchydro_account_number, bchydro_slid, timeout=10)
print(latest_usage(x))
