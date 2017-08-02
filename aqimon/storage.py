# -*- coding: utf-8 -*-

import time

from twisted.internet import defer


class AqiStorage(object):
    '''
    AQI-related data storage.

    '''
    def __init__(self, db_session):
        # open database
        self.db_session = db_session
        # create tables, if needed
        self._create_tables()

    @defer.inlineCallbacks
    def _create_tables(self):
        # create PM data table
        yield self.db_session.runQuery(
            'CREATE TABLE IF NOT EXISTS pm_data ' +
            '(id INTEGER PRIMARY KEY AUTOINCREMENT, tstamp INTEGER, pm25 REAL, pm10 REAL)')
        yield self.db_session.runQuery(
            'CREATE INDEX IF NOT EXISTS pm_data_tstamp_idx ON pm_data (tstamp)')

    def add_pm_data(self, tstamp, pm_25, pm_10):
        '''
        Add PM measurement data to database.
        '''
        return self.db_session.runQuery(
            'INSERT INTO pm_data (tstamp, pm25, pm10) VALUES (?, ?, ?)',
            (tstamp, pm_25, pm_10))

    def last_period_pm_data(self, period):
        '''
        Get last PM measurement data for given period (in seconds).
        '''
        return self.db_session.runQuery(
            'SELECT tstamp, pm25, pm10 FROM pm_data WHERE tstamp > ?',
            (int(time.time()-period),))
