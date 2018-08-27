# -*- coding: utf-8 -*-

from twisted.internet import reactor
from twisted.application.internet import ClientService, backoffPolicy
from twisted.internet import defer
from twisted.internet.endpoints import clientFromString
from twisted.logger import Logger

from mqtt.client.factory import MQTTFactory

import json

import aqimon

log = Logger()

DEFAULT_BROKER_HOST = 'localhost'
DEFAULT_BROKER_PORT = 1883
DEFAULT_USER = None
DEFAULT_PASSWORD = None
DEFAULT_TOPIC = 'aqimon/pm_data'


class MQTTPublisherPlugin(ClientService):
    '''
    MQTT AQI/PM data publisher plugin.
    '''

    def __init__(self, host, port, topic, user, password):
        self.broker_url = "tcp:%s:%s" % (host, port)
        self.topic = topic
        self.user = user
        self.password = password
        self.connected = False
        factory = MQTTFactory(profile=MQTTFactory.PUBLISHER)
        endpoint = clientFromString(reactor, self.broker_url)
        ClientService.__init__(self, endpoint, factory, retryPolicy=backoffPolicy())

    def startService(self):
        log.info("Starting MQTT publisher plugin")
        # subscribe to AQI updates
        aqi_monitor = self.parent.getServiceNamed(aqimon.AqiMonitor.name)
        aqi_monitor.add_listener(self)
        # invoke whenConnected() inherited method
        self.whenConnected().addCallback(self.connectToBroker)
        ClientService.startService(self)

    @defer.inlineCallbacks
    def connectToBroker(self, protocol):
        self.protocol = protocol
        self.protocol.onDisconnection = self.onDisconnection
        log.info("Connecting to %s..." % self.broker_url)
        try:
            yield self.protocol.connect("aqi-bot", username=self.user, password=self.password,
                                        keepalive=60)
        except Exception as e:
            log.error("Can't connect to %s: %s" % (self.broker_url, e))
        else:
            self.connected = True
            log.info("Connected to %s" % self.broker_url)

    def onDisconnection(self, reason):
        self.connected = False
        log.warn("Connection was lost: %s" % reason)
        self.whenConnected().addCallback(self.connectToBroker)

    @defer.inlineCallbacks
    def pm_data_updated(self, pm_25, pm_10, aqi):
        if not self.connected:
            return
        message = json.dumps({'pm_25': float(pm_25), 'pm_10': float(pm_10), 'aqi': int(aqi)})
        try:
            yield self.protocol.publish(topic=self.topic, message=message)
        except Exception as e:
            log.error("Can't publish updated AQI: %s" % e)
