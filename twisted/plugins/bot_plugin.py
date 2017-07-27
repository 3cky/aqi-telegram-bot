# -*- coding: utf-8 -*-

import os
import sys
import logging

from zope.interface import implementer  # @UnresolvedImport

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import service

from TelegramBot.service.bot import BotService
from TelegramBot.client.twistedclient import TwistedClient as TelegramClient

from l10n import L10nSupport
from aqimon.monitor import AqiMonitor
from telegram.bot import Bot
from db import DbSession

from configparser import ConfigParser

import codecs

TAP_NAME = "aqi-telegram-bot"

DEFAULT_NICKNAME = TAP_NAME

DEFAULT_DB_FILENAME = 'db.sqlite'

DEFAULT_SENSOR_DEVICE = '/dev/ttyUSB0'
DEFAULT_SENSOR_BAUDRATE = 9600

DEFAULT_POLL_PERIOD = 3  # 3 min

DEFAULT_LANG = 'en'

LOG_FORMAT = '[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d] %(message)s'


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

        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG if debug else logging.INFO,
                            format=LOG_FORMAT)

        # check configuration file is specified and exists
        if not options["config"]:
            raise ValueError('Configuration file not specified (try to check --help option)')
        cfgFileName = options["config"]
        if not os.path.isfile(cfgFileName):
            raise ConfigurationError('Configuration file not found:', cfgFileName)

        # read configuration file
        cfg = ConfigParser()
        with codecs.open(cfgFileName, 'r', encoding='utf-8') as f:
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
        db_filename = cfg.get('db', 'filename') if cfg.has_option('db', 'filename') \
            else DEFAULT_DB_FILENAME
        db_session = DbSession(db_filename)

        # sensor parameters
        sensor_device = cfg.get('sensor', 'device') \
            if cfg.has_option('sensor', 'device') else DEFAULT_SENSOR_DEVICE
        sensor_baudrate = int(cfg.get('sensor', 'baudrate')) \
            if cfg.has_option('sensor', 'baudrate') else DEFAULT_SENSOR_BAUDRATE

        poll_period = int(cfg.get('sensor', 'poll_period')) \
            if cfg.has_option('sensor', 'poll_period') else DEFAULT_POLL_PERIOD

        aqi_monitor = AqiMonitor(db_session, sensor_device, sensor_baudrate,
                                 poll_period, debug=debug)
        aqi_monitor.setServiceParent(application)

        bot = Bot(l10n_support)
        bot.setServiceParent(application)

        telegramBot = BotService(plugins=[bot])
        telegramBot.setServiceParent(application)

        client = TelegramClient(token, telegramBot.on_update, debug=debug)
        client.setServiceParent(application)

        return serviceCollection


serviceManager = ServiceManager()
