# -*- coding: utf-8 -*-

from twisted.enterprise import adbapi


class DbSession(object):
    '''
    Database session.

    '''
    def __init__(self, db_filename):
        # open database
        self._pool = adbapi.ConnectionPool("sqlite3", db_filename, check_same_thread=False)

    def runQuery(self, *args, **kw):
        """
        Execute an SQL query and return the result.

        @return: a L{Deferred} which will fire the return value of a DB-API
            cursor's 'fetchall' method, or a L{twisted.python.failure.Failure}.
        """
        return self._pool.runQuery(*args, **kw)
