# -*- coding: utf-8 -*-
import struct

from twisted.python import log, failure

from twisted.internet.protocol import Protocol
from twisted.internet import defer, reactor
from queue import Queue


class AsyncRequest(object):
    timeout = 5

    def __init__(self, cmd, d):
        self.cmd = cmd
        self.d = d


class AsyncRequestTimeout(Exception):
    pass


class UnexpectedResponse(Exception):
    pass


class SensorDisconnected(Exception):
    pass


class Sds011(Protocol):
    '''
    SDS011 particulate matter sensor protocol.
    '''

    # Request/response message head byte
    MSG_HEAD = 0xAA
    # Request/response message tail byte
    MSG_TAIL = 0xAB

    # Request type flag (second message byte)
    REQ_TYPE = 0xB4

    # Request data block length in bytes
    REQ_DATA_LENGTH = 11

    # Request mode flag byte: GET
    REQ_MODE_GET = 0
    # Request mode flag byte: SET
    REQ_MODE_SET = 1

    # Response length in bytes
    RESP_LENGTH = 10
    # Response type flag position in response
    RESP_TYPE_POS = 1
    # Data block position in response
    RESP_DATA_START = 2
    # Length of data block in response in bytes
    RESP_DATA_LENGTH = 6
    # Checksum byte position in response
    RESP_CHECKSUM_POS = 8

    # Response type flag for messages in active mode (second message byte)
    RESP_TYPE_ACTIVE = 0xC0
    # Response type flag for query reply messages (second message byte)
    RESP_TYPE_QUERY = 0xC5

    # Request command: Data reporting mode
    CMD_REPORT_MODE = 2
    # Request command: Query data command
    CMD_QUERY = 4
    # Request command: Set Device ID
    CMD_DEVICE_ID = 5
    # Request command: Set sleep and work
    CMD_STATE = 6
    # Request command: Check firmware version
    CMD_FIRMWARE = 7
    # Request command: Working period
    CMD_WORKING_PERIOD = 8

    # Report mode flag byte: ACTIVE
    REPORT_MODE_ACTIVE = 0
    # Report mode flag byte: QUERY
    REPORT_MODE_QUERY = 1

    # State flag byte: SLEEP
    STATE_SLEEP = 0
    # State flag byte: AWAKE
    STATE_AWAKE = 1

    def __init__(self, event_handler, debug=False):
        self.event_handler = event_handler
        self.debug = debug
        self.sleep = False
        self.connected = False

    def connectionMade(self):
        self.connected = True
        self.buf = b''
        self.req_queue = Queue()
        self.event_handler.sensor_connected()

    def connectionLost(self, reason):
        self.connected = False
        # cancel pending async requests
        q = self.req_queue
        while not q.empty():
            try:
                req = q.get(False)
                req.d.errback(failure.Failure(SensorDisconnected(reason)))
            except:  # @IgnorePep8
                continue
        self.event_handler.sensor_disconnected(reason)

    def dataReceived(self, data):
        self.buf += data
        disp = 0
        while disp <= len(self.buf)-self.RESP_LENGTH:
            if self.check_message(self.buf, disp):
                self.message_received(self.buf[disp:disp+self.RESP_LENGTH])
                disp += self.RESP_LENGTH
            else:
                disp += 1
        if disp > 0:
            self.buf = self.buf[disp:]

    def check_message(self, buf, start):
        return len(buf)-start >= self.RESP_LENGTH and buf[start] == self.MSG_HEAD \
            and buf[start+self.RESP_LENGTH-1] == self.MSG_TAIL

    def message_received(self, msg):
        if self.debug:
            log.msg("Received message: %s" % self._to_hex(msg))
        msg_type = msg[self.RESP_TYPE_POS]
        msg_data = msg[self.RESP_DATA_START:self.RESP_DATA_START+self.RESP_DATA_LENGTH]
        msg_checksum = msg[self.RESP_CHECKSUM_POS]
        data_checksum = self._checksum(msg_data)
        if data_checksum != msg_checksum:
            log.msg("ERROR: Corrupted message: %s (checksum computed 0x%02x, expected 0x%02x)" %
                    (self._to_hex(msg), data_checksum, msg_checksum))
        elif msg_type == self.RESP_TYPE_ACTIVE:
            pm_25, pm_10 = self._pm_data(msg_data)
            self.event_handler.sensor_data(pm_25, pm_10)
        elif msg_type == self.RESP_TYPE_QUERY:
            self.response_received(msg_data)
        else:
            log.msg("ERROR: Unknown response type: 0x%02x, msg_data: %s" %
                    (msg_type, self._to_hex(msg_data)))

    def response_received(self, resp_data):
        resp_cmd = resp_data[0]
        if self.debug:
            log.msg("Received response to cmd: 0x%02x, data: %s" %
                    (resp_cmd, self._to_hex(resp_data[1:])))
        req = self.req_queue.get(False)
        if resp_cmd != req.cmd:
            err_text = "Response cmd: 0x%02x, expected: 0x%02x" % (resp_cmd, req.cmd)
            log.msg("ERROR: Unexpected response: %s", err_text)
            req.d.errback(failure.Failure(UnexpectedResponse(err_text)))
            return
        if resp_cmd == self.CMD_STATE or resp_cmd == self.CMD_REPORT_MODE or \
                resp_cmd == self.CMD_WORKING_PERIOD:
            req.d.callback(resp_data[2])
        elif resp_cmd == self.CMD_FIRMWARE:
            req.d.callback("%02d%02d%02d" % (resp_data[1], resp_data[2], resp_data[3]))
        else:
            log.msg("ERROR: Unknown response cmd: 0x%02x" % resp_cmd)

    def send_message(self, cmd, mode, value=0):
        checksum = self._checksum(struct.pack('<3B10x2B', cmd, mode, value, 0xFF, 0xFF))
        msg = struct.pack('<5B10x4B', self.MSG_HEAD, self.REQ_TYPE, cmd, mode, value,
                          0xff, 0xff, checksum, self.MSG_TAIL)
        self.transport.write(msg)
        if self.debug:
            log.msg("Sent message: %s" % self._to_hex(msg))

    @staticmethod
    def _to_hex(data):
        return ":".join("{:02x}".format(c).upper() for c in data)

    @staticmethod
    def _pm_data(data):
        pm_data = struct.unpack('<HHcc', data)
        pm_25 = float(pm_data[0])/10.
        pm_10 = float(pm_data[1])/10.
        return pm_25, pm_10

    @staticmethod
    def _checksum(data):
        return sum(data) & 0xFF

    def queue_async_request(self, req_cmd):
        d = defer.Deferred()
        req = AsyncRequest(req_cmd, d)
        d.addTimeout(req.timeout, reactor, onTimeoutCancel=self._async_request_cancel_timeout)
        self.req_queue.put(req)
        return d

    @staticmethod
    def _async_request_cancel_timeout(value, _timeout):
        if isinstance(value, failure.Failure):
            value.trap(defer.CancelledError)
            raise AsyncRequestTimeout("Command execution timeout")
        return value

    def _check_connected(self):
        if not self.connected:
            raise SensorDisconnected("Sensor not connected")

    def sync_request(self, cmd, mode, value=0):
        self._check_connected()
        self.send_message(cmd, mode, value)

    def async_request(self, cmd, mode, value=0):
        self._check_connected()
        d = self.queue_async_request(cmd)
        self.send_message(cmd, mode, value)
        return d

    def get_state(self):
        """
        Get sensor state.

        @return: Sensor state (L{Sds011.STATE_SLEEP}/L{Sds011.STATE_AWAKE}).
        """
        return self.STATE_SLEEP if self.sleep else self.STATE_AWAKE

    def set_state(self, state):
        """
        Set sensor state.

        @param state: State to set (L{Sds011.STATE_SLEEP}/L{Sds011.STATE_AWAKE})

        @return: Sensor state wrapped in a L{Deferred}.
        """
        self.sleep = (state == self.STATE_SLEEP)
        return self.async_request(self.CMD_STATE, self.REQ_MODE_SET, state)

    def get_firmware_version(self):
        """
        Get sensor firmware version.

        @return: Sensor firmware version string in format YYMMDD wrapped in a L{Deferred}.
        """
        return self.async_request(self.CMD_FIRMWARE, self.REQ_MODE_GET)

    def get_report_mode(self):
        """
        Get sensor report mode.

        @return: Sensor report mode (L{Sds011.REPORT_MODE_ACTIVE}/L{Sds011.REPORT_MODE_QUERY})
        wrapped in a L{Deferred}.
        """
        return self.async_request(self.CMD_REPORT_MODE, self.REQ_MODE_GET)

    def set_report_mode(self, mode):
        """
        Set sensor report mode.

        @param mode: Report mode to set (L{Sds011.REPORT_MODE_ACTIVE}/L{Sds011.REPORT_MODE_QUERY})

        @return: Sensor report mode wrapped in a L{Deferred}.
        """
        return self.async_request(self.CMD_REPORT_MODE, self.REQ_MODE_SET, mode)

    def get_working_period(self):
        """
        Get sensor working period.

        @return: Sensor working period wrapped in a L{Deferred}.
        """
        return self.async_request(self.CMD_WORKING_PERIOD, self.REQ_MODE_GET)

    def set_working_period(self, period):
        """
        Set sensor working period.

        @param period: Working period to set, in minutes (0-30)

        @return: Sensor working period wrapped in a L{Deferred}.
        """
        period = max(0, min(30, period))
        return self.async_request(self.CMD_WORKING_PERIOD, self.REQ_MODE_SET, period)

    def query_data(self):
        """
        Query sensor data. Response will be sent to sensor event handler.
        """
        self.sync_request(self.CMD_QUERY, self.REQ_MODE_GET)
