import logging
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
URL_GET_USAGE = "https://app.bchydro.com/evportlet/SystemServices/main?system:runTemplate=html/indicators/AccountProfile.xml"


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
            }, allow_redirects=False)

        return r.cookies

    def latest_usage(self):
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
        root = ET.fromstring(r.text)
        for point in root.findall('Series')[0].findall('Point'):
            if point.get('quality') != 'INVALID':
                latest_usage = point.get('value')

        return latest_usage

    def _call_api(self, method, url, **kwargs):
        payload = kwargs.get("params") or kwargs.get("data")

        _LOGGER.debug("About to call %s with payload=%s", url, payload)

        response = requests.request(method, url, timeout=self._timeout, **kwargs)

        _LOGGER.debug("Received API response: %s, %s",
                      response.status_code,
                      response.content)

        response.raise_for_status()
        return response
