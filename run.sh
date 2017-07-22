#!/bin/sh
source ../../venv/aqi-telegram-bot/bin/activate
PYTHONPATH=../../other/txTelegramBot:../../other/TelegramBotAPI:$PYTHONPATH twistd -n aqi-telegram-bot --config ./config.ini --debug
