# -*- coding: utf-8 -*-

import time

import babel.dates

from datetime import timedelta

from twisted.internet import defer
from twisted.application import service

from TelegramBot.plugin.bot import BotPlugin
from TelegramBotAPI.types import InlineKeyboardMarkup, InlineKeyboardButton
from TelegramBotAPI.types.methods import Method, sendMessage, answerCallbackQuery, \
    deleteMessage, sendPhoto


class Bot(service.Service, BotPlugin):
    '''
    Telegram AQI monitor bot part.

    '''
    name = 'aqi_telegram_bot'

    aqi_symbols = u'😃😐😕☹️😧😵'

    def __init__(self, l10n_support, aqi_plot):
        BotPlugin.__init__(self)
        self.l10n_support = l10n_support
        self.aqi_plot = aqi_plot

    def startService(self):
        self.aqi_monitor = self.parent.getServiceNamed('aqi_monitor')

    def format_timedelta(self, from_timestamp_secs, to_timestamp_secs=None):
        if to_timestamp_secs is None:
            to_timestamp_secs = time.time()
        td = timedelta(seconds=to_timestamp_secs-from_timestamp_secs)
        return babel.dates.format_timedelta(td, locale=self.l10n_support.locale)

    def on_unknown_command(self, cmd):
        return _(u'Unknown command: /%(cmd)s\n' +
                 u'Please use /help for list of available commands.') % \
            {'cmd': cmd.replace('_', '\_')}

    def on_command_start(self, _args, _cmd_msg):
        return _(u"Hello, I'm *AQI monitor bot*.\nFor help, please use /help command.")

    def on_command_help(self, _args, _msg):
        return _(u'*Available commands:*\n\n' +
                 u'/aqi - show current AQI value\n' +
                 u'/pm - show current PM values\n' +
                 u'/sensor\_info - show PM sensor information')

    def cmd_response(self, chat_id, text, cmd):
        m = sendMessage()
        m.chat_id = chat_id
        m.text = text
        m.parse_mode = 'Markdown'
        m.reply_markup = self.cmd_refresh_button(cmd)
        return m

    def cmd_refresh_button(self, cmd):
        keyboard = InlineKeyboardMarkup()
        buttons = []
        b = InlineKeyboardButton()
        b.text = _(u'Refresh')
        b.callback_data = cmd
        buttons.append(b)
        keyboard.inline_keyboard = [buttons]
        return keyboard

    def on_command_aqi(self, _args, msg):
        pm_timestamp = self.aqi_monitor.pm_timestamp
        if pm_timestamp is None:
            return _(u'No data from PM sensor obtained yet.')
        aqi = self.aqi_monitor.current_aqi()
        aqi_symbol = self.aqi_symbols[self.aqi_monitor.current_aqi_level()]
        rtime = self.format_timedelta(pm_timestamp)
        text = _(u'AQI: *%(aqi)s* %(aqi_symbol)s (updated %(rtime)s ago)') % \
            {'aqi': aqi, 'aqi_symbol': aqi_symbol, 'rtime': rtime}
        return self.cmd_response(msg.chat.id, text, 'aqi')

    def on_command_pm(self, _args, msg):
        pm_timestamp = self.aqi_monitor.pm_timestamp
        if pm_timestamp is None:
            return _(u'No data from PM sensor obtained yet.')
        pm_25, pm_10 = self.aqi_monitor.current_pm()
        rtime = self.format_timedelta(pm_timestamp)
        text = _(u'PM2.5: *%(pm_25)s* μg/m^3\nPM10: *%(pm_10)s* μg/m^3\n' +
                 u'(updated %(rtime)s ago)') % {'pm_25': pm_25, 'pm_10': pm_10, 'rtime': rtime}
        return self.cmd_response(msg.chat.id, text, 'pm')

    @defer.inlineCallbacks
    def on_command_pm_hourly(self, _args, msg):
        img = yield self.aqi_plot.plot_hourly_pm_data()
        if img is None:
            return _(u'Hourly PM data is unavailable.')
        m = sendPhoto()
        m.chat_id = msg.chat.id
        m.photo = img
        m.reply_markup = self.cmd_refresh_button('pm_hourly')
        return m

    @defer.inlineCallbacks
    def on_command_pm_daily(self, _args, msg):
        img = yield self.aqi_plot.plot_daily_pm_data()
        if img is None:
            return _(u'Daily PM data is unavailable.')
        m = sendPhoto()
        m.chat_id = msg.chat.id
        m.photo = img
        m.reply_markup = self.cmd_refresh_button('pm_daily')
        return m

    @defer.inlineCallbacks
    def on_command_aqi_hourly(self, _args, msg):
        img = yield self.aqi_plot.plot_hourly_aqi_data()
        if img is None:
            return _(u'Hourly AQI data is unavailable.')
        m = sendPhoto()
        m.chat_id = msg.chat.id
        m.photo = img
        m.reply_markup = self.cmd_refresh_button('aqi_hourly')
        return m

    @defer.inlineCallbacks
    def on_command_aqi_daily(self, _args, msg):
        img = yield self.aqi_plot.plot_daily_aqi_data()
        if img is None:
            return _(u'Daily AQI data is unavailable.')
        m = sendPhoto()
        m.chat_id = msg.chat.id
        m.photo = img
        m.reply_markup = self.cmd_refresh_button('aqi_daily')
        return m

    @defer.inlineCallbacks
    def on_command_sensor_info(self, _args, _msg):
        sensor_fw = yield self.aqi_monitor.sensor_firmware_version()
        defer.returnValue(_(u"PM sensor info:\nFirmware version: *%(fw)s*") % {'fw': sensor_fw})

    @defer.inlineCallbacks
    def on_callback_query(self, callback_query):
        # create callback query result
        m = answerCallbackQuery()
        m.callback_query_id = callback_query.id
        yield self.send_method(m)

        # get callback command result
        cmd = callback_query.data
        msg = callback_query.message
        cmd_result = yield self.on_command(cmd, cmd_msg=msg)

        # delete old message, if possible
        m = deleteMessage()
        m.chat_id = msg.chat.id
        m.message_id = msg.message_id
        try:
            yield self.send_method(m)
        except Exception:
            pass

        # send message with callback command result
        if not isinstance(cmd_result, Method):
            cmd_result = self.cmd_response(msg.chat.id, cmd_result, cmd)
        yield self.send_method(cmd_result)

        defer.returnValue(True)
