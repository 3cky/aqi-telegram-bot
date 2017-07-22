# -*- coding: utf-8 -*-

import time

import babel.dates

from datetime import timedelta

from twisted.internet import defer
from twisted.application import service

from TelegramBot.plugin.bot import BotPlugin


class Bot(service.Service, BotPlugin):
    '''
    Telegram AQI monitor bot part.

    '''
    name = 'aqi_telegram_bot'

    def __init__(self, l10n_support):
        BotPlugin.__init__(self)
        self.l10n_support = l10n_support

    def startService(self):
        self.aqi_monitor = self.parent.getServiceNamed('aqi_monitor')

    @staticmethod
    def format_timedelta(from_timestamp_secs, to_timestamp_secs=None):
        if to_timestamp_secs is None:
            to_timestamp_secs = time.time()
        td = timedelta(seconds=to_timestamp_secs-from_timestamp_secs)
        return babel.dates.format_timedelta(td)

    def on_unknown_command(self, cmd):
        return _(u'Unknown command: /%(cmd)s\n' +
                 u'Please use /help for list of available commands.') % {'cmd': cmd}

    def on_command_start(self, _args, _cmd_msg):
        return _(u"Hello, I'm *AQI monitor bot*.\nFor help, please use /help command.")

    def on_command_help(self, _args, _msg):
        return _(u'*Available commands:*\n\n' +
                 u'/aqi - show current AQI value\n'
                 u'/pm - show current PM values')

    def on_command_aqi(self, _args, _msg):
        data_timestamp = self.aqi_monitor.data_timestamp
        if data_timestamp is None:
            return _(u'No data from PM sensor obtained yet.')
        aqi = self.aqi_monitor.current_aqi()
        rtime = self.format_timedelta(data_timestamp)
        return _(u'AQI: *%(aqi)s* (updated %(rtime)s ago)') % {'aqi': aqi, 'rtime': rtime}

    def on_command_pm(self, _args, _msg):
        data_timestamp = self.aqi_monitor.data_timestamp
        if data_timestamp is None:
            return _(u'No data from PM sensor obtained yet.')
        pm_25, pm_10 = self.aqi_monitor.current_pm()
        rtime = self.format_timedelta(data_timestamp)
        return _(u'PM2.5: *%(pm_25)s* μg/m^3\nPM10: *%(pm_10)s* μg/m^3\n' +
                 u'(updated %(rtime)s ago)') % {'pm_25': pm_25, 'pm_10': pm_10, 'rtime': rtime}

    @defer.inlineCallbacks
    def on_command_sensor_info(self, _args, _msg):
        sensor_fw = yield self.aqi_monitor.sensor_firmware_version()
        defer.returnValue(_(u"PM sensor info:\nFirmware version: *%(fw)s*") % {'fw': sensor_fw})
