# aqi-telegram-bot
*aqi-telegram-bot* is [AQI](https://en.wikipedia.org/wiki/Air_quality_index) monitoring Telegram bot.
It's written in Python using [Twisted](https://twistedmatrix.com/trac/) framework.

## Sensor
Currently *aqi-telegram-bot* supports [SDS011](http://ecksteinimg.de/Datasheet/SDS011%20laser%20PM2.5%20sensor%20specification-V1.3.pdf) Laser PM2.5 Sensor produced by Nova.

## Installation

*aqi-telegram-bot* runs on Python 3.4 and above.

Clone the repo in the directory of your choice using git:
```
git clone https://github.com/3cky/aqi-telegram-bot aqi-telegram-bot-git
cd aqi-telegram-bot-git
```

Next, install all needed Python requirements using [pip](https://pip.pypa.io/en/latest/) package manager:

`pip install --upgrade -r ./requirements.txt`

Then install *aqi-telegram-bot* itself:

`python setup.py install`

## Configuration

Before run this bot, you will have to create a configuration file. You could use
provided `doc/config.ini` as example. Minimal configuration includes specifying Telegram token and
sensor serial port and speed.

## Run

Run *aqi-telegram-bot* by command `twistd -n aqi-telegram-bot -c /path/to/config.ini`.

## Commands

Use `/help` to get list of available commands.
