# -*- coding: utf-8 -*-

import os

from zope.interface import implementer  # @UnresolvedImport

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import service

from TelegramBot.service.bot import BotService
from TelegramBot.client.twistedclient import TwistedClient as TelegramClient

from l10n import L10nSupport
from aqimon import AqiMonitor, AqiStorage, AqiPlot
from aqimon.plugins import mqtt
from telegram.bot import Bot
from db import DbSession

from configparser import ConfigParser

import codecs

TAP_NAME = "aqi-telegram-bot"

DEFAULT_NICKNAME = TAP_NAME

DEFAULT_DB_FILENAME = 'db.sqlite'

DEFAULT_SENSOR_DEVICE = '/dev/ttyUSB0'
DEFAULT_SENSOR_BAUDRATE = 9600
DEFAULT_SENSOR_POLL_PERIOD = 3  # 3 min

DEFAULT_LANG = 'en'


class ConfigurationError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Options(usage.Options):
    optFlags = [["debug", "d", "Enable debug output"]]
    optParameters = [["config", "c", None, 'Configuration file name']]


@implementer(IServiceMaker, IPlugin)
class ServiceManager(object):
    tapname = TAP_NAME
    description = "AQI monitor Telegram bot."
    options = Options
    apps = []

    def makeService(self, options):
        # create Twisted application
        application = service.Application(TAP_NAME)
        serviceCollection = service.IServiceCollection(application)

        debug = options['debug']

        # check configuration file is specified and exists
        if not options["config"]:
            raise ValueError('Configuration file not specified (try to check --help option)')
        cfg_file_name = options["config"]
        if not os.path.isfile(cfg_file_name):
            raise ConfigurationError('Configuration file not found:', cfg_file_name)

        # read configuration file
        cfg = ConfigParser()
        with codecs.open(cfg_file_name, 'r', encoding='utf-8') as f:
            cfg.readfp(f)

        # get Telegram token from configuration
        if not cfg.has_option('telegram', 'token'):
            raise ConfigurationError('Telegram API token must be specified ' +
                                     'in configuration file [telegram] section')
        token = cfg.get('telegram', 'token')

        # initialize l10n
        lang = DEFAULT_LANG
        if cfg.has_option('telegram', 'lang'):
            lang = cfg.get('telegram', 'lang')
        l10n_support = L10nSupport(lang)

        # initialize database session
        db_filename = cfg.get('db', 'filename', fallback=DEFAULT_DB_FILENAME)
        db_session = DbSession(db_filename)

        # sensor parameters
        sensor_device = cfg.get('sensor', 'device', fallback=DEFAULT_SENSOR_DEVICE)
        sensor_baudrate = int(cfg.get('sensor', 'baudrate', fallback=DEFAULT_SENSOR_BAUDRATE))
        sensor_poll_period = int(cfg.get('sensor', 'poll_period',
                                         fallback=DEFAULT_SENSOR_POLL_PERIOD))

        if cfg.has_section('mqtt'):
            mqtt_section = cfg['mqtt']
            mqtt_host = mqtt_section.get('host', mqtt.DEFAULT_BROKER_HOST)
            mqtt_port = int(mqtt_section.get('port', mqtt.DEFAULT_BROKER_PORT))
            mqtt_topic = mqtt_section.get('topic', mqtt.DEFAULT_TOPIC)
            mqtt_user = mqtt_section.get('user', mqtt.DEFAULT_USER)
            mqtt_password = mqtt_section.get('password', mqtt.DEFAULT_PASSWORD)
            plugin = mqtt.MQTTPublisherPlugin(mqtt_host, mqtt_port, mqtt_topic,
                                              mqtt_user, mqtt_password)
            plugin.setServiceParent(application)

        aqi_storage = AqiStorage(db_session)
        aqi_monitor = AqiMonitor(aqi_storage, sensor_device, sensor_baudrate,
                                 sensor_poll_period, debug=debug)
        aqi_monitor.setServiceParent(application)

        aqi_plot = AqiPlot(l10n_support, aqi_storage)

        bot = Bot(l10n_support, aqi_plot)
        bot.setServiceParent(application)

        telegramBot = BotService(plugins=[bot])
        telegramBot.setServiceParent(application)

        client = TelegramClient(token, telegramBot.on_update, debug=debug)
        client.setServiceParent(application)

        return serviceCollection


serviceManager = ServiceManager()
