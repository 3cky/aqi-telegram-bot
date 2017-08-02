# -*- coding: utf-8 -*-

import io
import time
import datetime

import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MaxNLocator

import numpy as np

import aqi

from datetime import timedelta

from scipy.stats import binned_statistic

from twisted.internet import defer
from aqimon.monitor import AqiMonitor


class AqiPlot(object):
    '''
    Plot AQI-related data.

    '''
    aqi_colors = ('green', 'gold', 'orange', 'red', 'purple', 'maroon')

    def __init__(self, l10n_support, aqi_storage):
        self.l10n_support = l10n_support
        self.aqi_storage = aqi_storage

    def plot_data(self, ts, data, ts_start, ts_end, n_ts_bins, colors, labels, title, ylabel):
        ts_bins = np.linspace(ts_start, ts_end, n_ts_bins)

        t = [datetime.datetime.fromtimestamp(ts_bin) for ts_bin in ts_bins[1:]]

        d_bins = [binned_statistic(ts, d, 'mean', ts_bins, (ts_start, ts_end))[0] for d in data]

        n_days = (ts_end-ts_start)/86400
        width = n_days*0.75/n_ts_bins

        plt.figure()
        for i, d in enumerate(d_bins):
            color = colors[i]
            if callable(color):
                color = [color(v) for v in np.nan_to_num(d)]
            plt.bar(t, d, width=width, color=color, label=labels[i])
        plt.title(title)
        plt.ylabel(ylabel)
        plt.gca().xaxis_date()
        plt.gca().xaxis.set_major_formatter(DateFormatter('%H:%M'))
        plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.gcf().autofmt_xdate()
        plt.legend(loc=2)
        plt.grid(alpha=0.5)

        buf = io.BytesIO()
        buf.name = "plot.png"
        plt.savefig(buf, format='png')
        buf.seek(0)

        return buf

    def plot_pm_data(self, pm_data, ts_start, ts_end, ts_n_bins, title):
        pm_ts, pm_25, pm_10 = np.transpose(pm_data)
        return self.plot_data(pm_ts, (pm_10, pm_25), ts_start, ts_end, ts_n_bins,
                              ('steelblue', 'firebrick'), ('PM10', 'PM2.5'),
                              title, '$\mu g/m^3$')

    @defer.inlineCallbacks
    def plot_period_pm_data(self, period, n_bins, title):
        pm_data = yield self.aqi_storage.last_period_pm_data(period)

        if not pm_data:
            defer.returnValue(None)

        t_end = time.time()
        t_start = t_end-period

        plot = self.plot_pm_data(pm_data, t_start, t_end, n_bins, title)

        defer.returnValue(plot)

    @defer.inlineCallbacks
    def plot_hourly_pm_data(self):
        period = timedelta(hours=1).total_seconds()
        plot = yield self.plot_period_pm_data(period, 20, _(u'Hourly PM concentrations'))
        defer.returnValue(plot)

    @defer.inlineCallbacks
    def plot_daily_pm_data(self):
        period = timedelta(days=1).total_seconds()
        plot = yield self.plot_period_pm_data(period, 48, _(u'Daily PM concentrations'))
        defer.returnValue(plot)

    def plot_aqi_data(self, aqi_data, ts, ts_start, ts_end, ts_n_bins, title):
        def aqi_color_fn(a):
            return self.aqi_colors[AqiMonitor.aqi_level(a)]

        return self.plot_data(ts, (aqi_data,), ts_start, ts_end, ts_n_bins,
                              (aqi_color_fn,), (None,), title, 'AQI')

    @defer.inlineCallbacks
    def plot_period_aqi_data(self, period, n_bins, title):
        pm_data = yield self.aqi_storage.last_period_pm_data(period)

        if not pm_data:
            defer.returnValue(None)

        t_end = time.time()
        t_start = t_end-period

        t, pm_25, pm_10 = np.transpose(pm_data)

        aqi_data = [int(aqi.to_aqi([(aqi.POLLUTANT_PM25, pm[0]), (aqi.POLLUTANT_PM10, pm[1])]))
                    for pm in zip(pm_25, pm_10)]

        plot = self.plot_aqi_data(aqi_data, t, t_start, t_end, n_bins, title)

        defer.returnValue(plot)

    @defer.inlineCallbacks
    def plot_hourly_aqi_data(self):
        period = timedelta(hours=1).total_seconds()
        plot = yield self.plot_period_aqi_data(period, 20, _(u'Hourly AQI values'))
        defer.returnValue(plot)

    @defer.inlineCallbacks
    def plot_daily_aqi_data(self):
        period = timedelta(days=1).total_seconds()
        plot = yield self.plot_period_aqi_data(period, 48, _(u'Daily AQI values'))
        defer.returnValue(plot)
