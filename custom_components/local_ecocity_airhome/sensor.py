"""
Support for Luftdaten sensors.

Copyright (c) 2020 Mario Villavecchia

Licensed under MIT. All rights reserved.

https://github.com/lichtteil/local_luftdaten/

Support for Ecocity Airhome sensors.

Mykhailo G


"""

import logging
import asyncio
import aiohttp
import async_timeout
import aqi

import json

from datetime import timedelta

import requests
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME, CONF_RESOURCE, CONF_VERIFY_SSL, CONF_MONITORED_CONDITIONS,
    TEMP_CELSIUS)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv


_LOGGER = logging.getLogger(__name__)

VOLUME_MICROGRAMS_PER_CUBIC_METER = 'µg/m3'

DOMAIN = "local_ecocity_airhome"


SENSOR_BME280_TEMPERATURE = 'BME280_temperature'
SENSOR_BME280_HUMIDITY = 'BME280_humidity'
SENSOR_BME280_PRESSURE = 'BME280_pressure'

SENSOR_PM0 = 'PMS_P0'
SENSOR_PM1 = 'PMS_P1'
SENSOR_PM2 = 'PMS_P2'

SENSOR_CO2 = 'CO2'

SENSOR_WIFI_SIGNAL = 'signal'


SENSOR_TYPES = {

    SENSOR_BME280_TEMPERATURE: ['Temperature', TEMP_CELSIUS, 'temperature'],
    SENSOR_BME280_HUMIDITY: ['Humidity', '%', 'humidity'],
    SENSOR_BME280_PRESSURE: ['Pressure', 'Pa', 'pressure'],

    SENSOR_PM0: ['PM1', VOLUME_MICROGRAMS_PER_CUBIC_METER, None],
    SENSOR_PM1: ['PM2.5', VOLUME_MICROGRAMS_PER_CUBIC_METER, None],
    SENSOR_PM2: ['PM10', VOLUME_MICROGRAMS_PER_CUBIC_METER, None],

    SENSOR_CO2: ['CO2', 'ppm', None],

    SENSOR_WIFI_SIGNAL: ['Wifi signal', 'dBm', 'signal_strength'],


}

DEFAULT_NAME = 'Ecocity Airhome'
DEFAULT_RESOURCE = 'http://{}/data.json'
DEFAULT_VERIFY_SSL = True

CONF_HOST = 'host'

SCAN_INTERVAL = timedelta(minutes=3)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_MONITORED_CONDITIONS):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_RESOURCE, default=DEFAULT_RESOURCE): cv.string,
    vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean
})



async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Luftdaten sensor."""
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    verify_ssl = config.get(CONF_VERIFY_SSL)

    resource = config.get(CONF_RESOURCE).format(host)

    session = async_get_clientsession(hass, verify_ssl)
    rest_client = LuftdatenClient(hass.loop, session, resource)

    devices = []
    for variable in config[CONF_MONITORED_CONDITIONS]:
        devices.append(LuftdatenSensor(rest_client, name, variable))

    devices.append(AqiCalculator(rest_client, name, variable))
    async_add_devices(devices, True)

class AqiCalculator(Entity):


    def __init__(self, rest_client, name, sensor_type):
        """Initialize the AQI Calculator."""
        self.rest_client = rest_client
        self._name = name
        self._state = None
        self.sensor_type = 'AQI'
        self._unit_of_measurement = 'AQI'
        self._device_class = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{} {}'.format(self._name,'AQI')

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def device_class(self):
        """Return the device class of this entity, if any."""
        return self._device_class

    async def async_update(self):
        """Get the latest data from REST API and update the state."""
        try:
            await self.rest_client.async_update()
        except LuftdatenError:
            value = None
            return
        value = self.rest_client.data

        try:
            parsed_json = json.loads(value)
            if not isinstance(parsed_json, dict):
                _LOGGER.warning("JSON result was not a dictionary")
                return
        except ValueError:
            _LOGGER.warning("REST result could not be parsed as JSON")
            _LOGGER.debug("Erroneous JSON: %s", value)
            return
        sensordata_values = parsed_json['sensordatavalues']
        pm25 = 0
        pm10 = 0
        for sensordata_value in sensordata_values:
           if sensordata_value['value_type'] == 'PMS_P1':
             pm25 = sensordata_value['value']
           elif sensordata_value['value_type'] =='PMS_P2':
             pm10 = sensordata_value['value']

        self._state = int(aqi.to_aqi([
            (aqi.POLLUTANT_PM25, pm25),
            (aqi.POLLUTANT_PM10, pm10),
        ]))



class LuftdatenSensor(Entity):
    """Implementation of a LuftdatenSensor sensor."""

    def __init__(self, rest_client, name, sensor_type):
        """Initialize the LuftdatenSensor sensor."""
        self.rest_client = rest_client
        self._name = name
        self._state = None
        self.sensor_type = sensor_type
        self._unit_of_measurement = SENSOR_TYPES[sensor_type][1]
        self._device_class = SENSOR_TYPES[sensor_type][2]

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{} {}'.format(self._name, SENSOR_TYPES[self.sensor_type][0])

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def device_class(self):
        """Return the device class of this entity, if any."""
        return self._device_class

    async def async_update(self):
        """Get the latest data from REST API and update the state."""
        try:
            await self.rest_client.async_update()
        except LuftdatenError:
            value = None
            return
        value = self.rest_client.data

        try:
            parsed_json = json.loads(value)
            if not isinstance(parsed_json, dict):
                _LOGGER.warning("JSON result was not a dictionary")
                return
        except ValueError:
            _LOGGER.warning("REST result could not be parsed as JSON")
            _LOGGER.debug("Erroneous JSON: %s", value)
            return

        sensordata_values = parsed_json['sensordatavalues']
        for sensordata_value in sensordata_values:
            if sensordata_value['value_type'] == self.sensor_type:
                self._state = sensordata_value['value']


class LuftdatenError(Exception):
    pass


class LuftdatenClient(object):
    """Class for handling the data retrieval."""

    def __init__(self, loop, session, resource):
        """Initialize the data object."""
        self._loop = loop
        self._session = session
        self._resource = resource
        self.data = None
        self.timeout = 10

    async def async_update(self):
        """Get the latest data from Luftdaten service."""
        _LOGGER.debug("Get data from %s", str(self._resource))
        try:
            async with async_timeout.timeout(self.timeout):
               response = await self._session.get(self._resource)
            self.data = await response.text()
            _LOGGER.debug("Received data: %s", str(self.data))
        except aiohttp.ClientError as err:
            _LOGGER.warning("REST request error: {0}".format(err))
            self.data = None
            raise LuftdatenError
        except asyncio.TimeoutError:
            _LOGGER.warning("REST request timeout")
            self.data = None
            raise LuftdatenError
