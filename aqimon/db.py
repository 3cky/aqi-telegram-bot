# -*- coding: utf-8 -*-

from twisted.internet import defer


class DataStorage(object):
    '''
    Monitor data storage.

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
            '(id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp INTEGER, pm25 REAL, pm10 REAL)')

    def add_pm_data(self, timestamp, pm_25, pm_10):
        '''
        Add measurement data to database.
        '''
        return self.db_session.runQuery(
            'INSERT INTO pm_data (timestamp, pm25, pm10) VALUES (?, ?, ?)',
            (timestamp, pm_25, pm_10))
