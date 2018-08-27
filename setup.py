from setuptools import setup

setup(
    name='aqi-telegram-bot',
    packages=[
        'aqimon',
        'aqimon.plugins',
        'telegram',
        'db',
        'l10n',
        "twisted.plugins",
    ],
    package_data={'l10n': ['locales/en_US/LC_MESSAGES/messages.mo',
                           'locales/ru_RU/LC_MESSAGES/messages.mo']},
    include_package_data=True,
    zip_safe=False,
    version='0.1.0',
)

# Make Twisted regenerate the dropin.cache, if possible.  This is necessary
# because in a site-wide install, dropin.cache cannot be rewritten by
# normal users.
try:
    from twisted.plugin import IPlugin, getPlugins
except ImportError:
    pass
else:
    list(getPlugins(IPlugin))
