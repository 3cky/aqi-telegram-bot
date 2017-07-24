# -*- coding: utf-8 -*-

import time

import babel.dates

import markdown2

from bs4 import BeautifulSoup

from datetime import timedelta

from twisted.internet import defer
from twisted.application import service

from TelegramBot.plugin.bot import BotPlugin
from TelegramBotAPI.types import InlineKeyboardMarkup, InlineKeyboardButton
from TelegramBotAPI.types.methods import sendMessage, answerCallbackQuery, editMessageText


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

    def format_timedelta(self, from_timestamp_secs, to_timestamp_secs=None):
        if to_timestamp_secs is None:
            to_timestamp_secs = time.time()
        td = timedelta(seconds=to_timestamp_secs-from_timestamp_secs)
        return babel.dates.format_timedelta(td, locale=self.l10n_support.locale)

    def on_unknown_command(self, cmd):
        return _(u'Unknown command: /%(cmd)s\n' +
                 u'Please use /help for list of available commands.') % {'cmd': cmd}

    def on_command_start(self, _args, cmd_msg):
        m = sendMessage()
        m.chat_id = cmd_msg.chat.id
        m.text = _(u"Hello, I'm *AQI monitor bot*.\nFor help, please use /help command.")
        m.parse_mode = 'Markdown'
        m.reply_markup = self.inline_keyboard()
        return m

    def on_command_help(self, _args, _msg):
        return _(u'*Available commands:*\n\n' +
                 u'/aqi - show current AQI value\n' +
                 u'/pm - show current PM values\n' +
                 u'/sensor\_info - show PM sensor information')

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

    @defer.inlineCallbacks
    def on_callback_query(self, callback_query):
        # create callback query result
        m = answerCallbackQuery()
        m.callback_query_id = callback_query.id
        yield self.send_method(m)

        # update message with command result (if text updated)
        text = yield self.on_command(callback_query.data)
        plain_text = BeautifulSoup(markdown2.markdown(text), "html.parser").get_text().strip()
        if plain_text != callback_query.message.text:
            m = editMessageText()
            m.chat_id = callback_query.message.chat.id
            m.message_id = callback_query.message.message_id
            m.text = text
            m.parse_mode = 'Markdown'
            m.reply_markup = self.inline_keyboard()
            yield self.send_method(m)

        defer.returnValue(True)

    def inline_keyboard(self):
        keyboard = InlineKeyboardMarkup()
        buttons = []
        b = InlineKeyboardButton()
        b.text = 'AQI'
        b.callback_data = 'aqi'
        buttons.append(b)
        b = InlineKeyboardButton()
        b.text = 'PM'
        b.callback_data = 'pm'
        buttons.append(b)
        keyboard.inline_keyboard = [buttons]
        return keyboard
