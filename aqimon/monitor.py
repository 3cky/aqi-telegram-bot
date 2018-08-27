# -*- coding: utf-8 -*-

import time

from twisted.application import service
from twisted.internet import reactor, defer
from twisted.internet.serialport import SerialPort
from twisted.logger import Logger

from serial.serialutil import SerialException

from telegram.bot import Bot as TelegramBot

import aqi as aqi_calc

from aqimon.sensor import Sds011, SensorDisconnected

log = Logger()


class AqiMonitor(service.Service):
    '''
    AQI monitor service.

    '''
    name = 'aqi_monitor'

    sensor_reconnect_timeout = 5

    def __init__(self, aqi_storage, sensor_device, sensor_baudrate, poll_period, debug=False):
        self.debug = debug
        self.sensor = None
        self.sensor_device = sensor_device
        self.sensor_baudrate = sensor_baudrate
        self.poll_period = poll_period
        self.pm_timestamp = None
        self.pm_25 = None
        self.pm_10 = None
        self.aqi_storage = aqi_storage
        self.listeners = []

    def startService(self):
        self._bot = self.parent.getServiceNamed(TelegramBot.name)
        reactor.callLater(0, self.connect_sensor)  # @UndefinedVariable

    def add_listener(self, listener):
        if listener not in self.listeners:
            self.listeners.append(listener)

    def connect_sensor(self):
        self.sensor = Sds011(self, debug=self.debug)
        try:
            self.serial_port = SerialPort(self.sensor, self.sensor_device, reactor,
                                          baudrate=self.sensor_baudrate)
            self.serial_port.flushInput()
        except SerialException as se:
            log.error("Can't connect to sensor: %s" % se)
            reactor.callLater(self.sensor_reconnect_timeout,  # @UndefinedVariable
                              self.connect_sensor)

    @defer.inlineCallbacks
    def init_sensor(self):
        yield self.sensor.query_data()
        period = yield self.sensor.set_working_period(self.poll_period)
        if self.debug:
            log.debug("Sensor initialized, poll period set to %d minute(s)" % period)

    def sensor_connected(self):
        log.info("Connected to sensor")
        reactor.callLater(1, self.init_sensor)  # @UndefinedVariable

    def sensor_disconnected(self, reason):
        log.warn("Disconnected from sensor, reason: %r" % reason)
        reactor.callLater(self.sensor_reconnect_timeout, self.connect_sensor)  # @UndefinedVariable

    def sensor_data(self, pm_25, pm_10):
        if pm_25 <= 0 or pm_10 <= 0:  # could be at sensor startup
            log.warn("Ignore invalid sensor data: PM2.5: %.1f, PM10: %.1f" % (pm_25, pm_10))
            return
        log.info("Sensor data received, PM2.5: %.1f, PM10: %.1f" % (pm_25, pm_10))
        self.pm_25 = pm_25
        self.pm_10 = pm_10
        self.pm_timestamp = time.time()
        self.aqi_storage.add_pm_data(int(self.pm_timestamp), pm_25, pm_10)
        for listener in self.listeners:
            try:
                listener.pm_data_updated(pm_25, pm_10, self.aqi)
            except Exception:
                log.failure("Can't notify PM data listener {listener}", listener=listener)

    @property
    def sensor_firmware_version(self):
        if self.sensor is None or not self.sensor.connected:
            raise SensorDisconnected("Can't get sensor firmware version: sensor not connected")
        return self.sensor.get_firmware_version()

    @staticmethod
    def to_aqi_level(aqi):
        if aqi <= 50:
            return 0  # Good
        elif aqi <= 100:
            return 1  # Moderate
        elif aqi <= 150:
            return 2  # Unhealthy for Sensitive Groups
        elif aqi <= 200:
            return 3  # Unhealthy
        elif aqi <= 300:
            return 4  # Very Unhealthy
        return 5      # Hazardous

    @property
    def aqi_level(self):
        if self.pm_timestamp is None:
            return None
        return self.to_aqi_level(self.aqi)

    @property
    def aqi(self):
        if self.pm_timestamp is None:
            return None
        return aqi_calc.to_aqi([(aqi_calc.POLLUTANT_PM25, self.pm_25),
                                (aqi_calc.POLLUTANT_PM10, self.pm_10)])

    @property
    def pm(self):
        return self.pm_25, self.pm_10
