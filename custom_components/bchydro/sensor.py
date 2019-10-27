import logging
import string
import xml.etree.ElementTree as ET

import homeassistant.helpers.config_validation as cv
import requests
import voluptuous as vol
from homeassistant.const import (
    CONF_PASSWORD, CONF_USERNAME, CONF_TIMEOUT)
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'bchydro'

DEFAULT_TIMEOUT = 10
CONF_ACCOUNT_NUMBER = 'account_number'
CONF_SLID = 'slid'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_ACCOUNT_NUMBER): cv.string,
        vol.Optional(CONF_SLID): cv.string,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
    })
}, extra=vol.ALLOW_EXTRA)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the sensor platform."""
    api = Api(config.get(CONF_USERNAME),
              config.get(CONF_PASSWORD),
              config.get(CONF_ACCOUNT_NUMBER),
              config.get(CONF_SLID),
              config.get(CONF_TIMEOUT))
    add_devices([BCHydroUsageSensor(api)], True)


class BCHydroUsageSensor(Entity):
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
URL_GET_USAGE = "https://app.bchydro.com/evportlet/web/account-profile-data.html"
# to get all the usage within a timeframe, use this url instead
url_detailed_usage = "https://app.bchydro.com/evportlet/SystemServices/main?system:runTemplate=html/indicators/Consumption.xml"
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
        _LOGGER.debug("What's the location? %s",r.headers['Location'])

        while r.status_code == 302:
            _LOGGER.debug("While loop is running!")

            redirect_URL2 = r.headers['Location']
            r = requests.get(redirect_URL2, cookies=jar)
            jar.update(r.cookies)
            _LOGGER.debug("While loop: cookie jar %s",jar)
        _LOGGER.debug("Before return: cookie jar %s",jar)
        return jar

    def latest_usage(self):
        """Fetch new state data for the sensor."""
        auth_cookies = self.login()
        _LOGGER.debug("Cookies passing to request: %s",auth_cookies)
        dataDict={                
                "Account": self._account_number,
                "Slid": self._slid,
                "ValidityStart": '2015-09-03T00:00:00.000-07:00',
                "ValidityEnd": '9999-12-31T00:00:00.000-08:00'
            }
        _LOGGER.debug("dataDict passing to post call: %s",dataDict)
        
        r = self._call_api(
            "post",
            URL_GET_USAGE,
            headers={"X-Requested-With": "XMLHttpRequest","Content-Type": "application/x-www-form-urlencoded"},
            data=dataDict, cookies=auth_cookies,allow_redirects=False)

        latest_usage = None
        r = r.text
        resultingCleanString = ''.join(filter(lambda x: x in string.printable, r)) # This is the line that I added (with import above)

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

        _LOGGER.debug("_call_api: About to call %s with payload=%s", url, payload)

        response = requests.request(method, url, timeout=self._timeout, **kwargs)

        _LOGGER.debug("_call_api: Received API response: %s, headers: %s - content: %s",
                      response.status_code,
                      response.headers,
                      response.content)

        response.raise_for_status()
        return response
