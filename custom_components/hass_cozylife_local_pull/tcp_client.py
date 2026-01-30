# -*- coding: utf-8 -*-
import json
import socket
import time
from typing import Optional, Union, Any
import logging
from .utils import get_pid_list, get_sn
import threading

CMD_INFO = 0
CMD_QUERY = 2
CMD_SET = 3
CMD_PUSH = 10  # Device-initiated push notification
CMD_LIST = [CMD_INFO, CMD_QUERY, CMD_SET]
_LOGGER = logging.getLogger(__name__)


class tcp_client(object):
    """
    Represents a device
    send:{"cmd":0,"pv":0,"sn":"1636463553873","msg":{}}
    receiver:{"cmd":0,"pv":0,"sn":"1636463553873","msg":{"did":"629168597cb94c4c1d8f","dtp":"02","pid":"e2s64v",
    "mac":"7cb94c4c1d8f","ip":"192.168.123.57","rssi":-33,"sv":"1.0.0","hv":"0.0.1"},"res":0}

    send:{"cmd":2,"pv":0,"sn":"1636463611798","msg":{"attr":[0]}}
    receiver:{"cmd":2,"pv":0,"sn":"1636463611798","msg":{"attr":[1,2,3,4,5,6],"data":{"1":0,"2":0,"3":1000,"4":1000,
    "5":65535,"6":65535}},"res":0}
    
    send:{"cmd":3,"pv":0,"sn":"1636463662455","msg":{"attr":[1],"data":{"1":0}}}
    receiver:{"cmd":3,"pv":0,"sn":"1636463662455","msg":{"attr":[1],"data":{"1":0}},"res":0}
    receiver:{"cmd":10,"pv":0,"sn":"1636463664000","res":0,"msg":{"attr":[1,2,3,4,5,6],"data":{"1":0,"2":0,"3":1000,
    "4":1000,"5":65535,"6":65535}}}
    """
    _ip = str
    _port = 5555
    _connect = socket
    
    _device_id = str
    # _device_key = str
    _pid = str
    _device_type_code = str
    _icon = str
    _device_model_name = str
    _dpid = []
    # last sn
    _sn = str
    
    def __init__(self, ip):
        try:
            self._ip = ip
            self._connect = None  # Initialize _connect as None
            self._device_type_code = None
            self._device_model_name = None
            self._device_id = None
            self._pid = None
            self._icon = None
            self._reconnecting = False  # Flag to track reconnection state
            self._device_state = {}  # Shared state dictionary from device updates
            self._state_lock = threading.Lock()  # Thread-safe access to state
            self._listener_running = False
            self._listener_thread = None
            _LOGGER.info(f'Initializing tcp_client for {self._ip}')
            self._close_connection()
            self._reconnect()
            _LOGGER.info(f'tcp_client __init__ complete for {self._ip}')
        except Exception as e:
            _LOGGER.error(f'Error in tcp_client __init__ for {self._ip}: {e}', exc_info=True)
    
    def _close_connection(self):
        # Stop listener thread
        if self._listener_running:
            _LOGGER.info(f'Stopping listener for {self._ip}')
            self._listener_running = False
            # Give thread time to exit gracefully
            if self._listener_thread and self._listener_thread.is_alive():
                self._listener_thread.join(timeout=2)

        # Close socket
        if self._connect:
            try:
                self._connect.close()
            except Exception as e:
                _LOGGER.error(f'Error while closing the connection: {e}')
            self._connect = None

        # Reset reconnecting flag so reconnection can be attempted
        self._reconnecting = False
        
    def _reconnect(self):
        # Don't start a new reconnection if already reconnecting
        if self._reconnecting:
            _LOGGER.debug(f'Already reconnecting to {self._ip}, skipping')
            return

        def reconnect_thread():
            self._reconnecting = True
            _LOGGER.info(f'Starting connection to {self._ip}:{self._port}')

            while True:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(10)  # Timeout for connect and all operations
                    _LOGGER.info(f'Attempting to connect to {self._ip}:{self._port}')
                    s.connect((self._ip, self._port))
                    _LOGGER.info(f'Connected to {self._ip}:{self._port}, getting device info')
                    self._connect = s
                    # Ensure timeout is set after connection
                    self._connect.settimeout(10)
                    self._device_info()
                    _LOGGER.info(f'Successfully connected and retrieved device info for {self._ip}')
                    self._reconnecting = False
                    return
                except Exception as e:
                    _LOGGER.warning(f'Connection to {self._ip}:{self._port} failed: {e}')
                    if s:
                        try:
                            s.close()
                        except:
                            pass
                    time.sleep(10)  # Reduced from 60 to 10 seconds for faster recovery

        thread = threading.Thread(target=reconnect_thread)
        thread.daemon = True  # This makes the thread exit when the main program exits
        thread.start()


    @property
    def check(self) -> bool:
        """
        Determine whether the device is filtered
        :return:
        """
        return True
    
    @property
    def dpid(self):
        return self._dpid
    
    @property
    def device_model_name(self):
        return self._device_model_name
    
    @property
    def icon(self):
        return self._icon
    
    @property
    def device_type_code(self) -> str:
        return self._device_type_code

    @property
    def ip(self):
        return self._ip

    @property
    def device_id(self):
        return self._device_id
    
    def _device_info(self) -> None:
        """
        get info for device model
        :return:
        """
        try:
            if self._connect is None:
                _LOGGER.warning('Connection is None in _device_info')
                return None

            # Set timeout for recv operations
            self._connect.settimeout(10)

            # Send CMD_INFO
            self._connect.send(self._get_package(CMD_INFO, {}))

            # Receive response
            resp = self._connect.recv(1024)
            resp_json = json.loads(resp.strip())
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            _LOGGER.warning(f'Connection error in _device_info: {e}')
            return None
        except Exception as e:
            _LOGGER.info(f'_device_info error: {e}')
            return None
        
        if resp_json.get('msg') is None or type(resp_json['msg']) is not dict:
            _LOGGER.info('_device_info.recv.error1')
            
            return None
        
        if resp_json['msg'].get('did') is None:
            _LOGGER.info('_device_info.recv.error2')
            
            return None

        self._device_id = resp_json['msg']['did']

        # Get device type code directly from device response (dtp field)
        if resp_json['msg'].get('dtp') is not None:
            self._device_type_code = resp_json['msg']['dtp']
            _LOGGER.info(f'Device type code from device: {self._device_type_code}')

        if resp_json['msg'].get('pid') is None:
            _LOGGER.info('_device_info.recv.error3')
            return None

        self._pid = resp_json['msg']['pid']
        pid_list = get_pid_list()

        for item in pid_list:
            match = False
            for item1 in item['m']:
                if item1['pid'] == self._pid:
                    match = True
                    self._icon = item1['i']
                    self._device_model_name = item1['n']
                    self._dpid = item1['dpid']
                    break

            if match:
                # Override device type code from API if found (more detailed info)
                # But we already have it from device response above
                if not self._device_type_code:
                    self._device_type_code = item['c']
                break

        # Set default model name if not found in API
        if not self._device_model_name:
            device_type_names = {
                '00': 'Switch',
                '01': 'Light',
                '02': 'Energy Storage'
            }
            self._device_model_name = device_type_names.get(self._device_type_code, 'CozyLife Device')

        # _LOGGER.info(pid_list)
        _LOGGER.info(f'Device ID: {self._device_id}')
        _LOGGER.info(f'Device Type Code: {self._device_type_code}')
        _LOGGER.info(f'PID: {self._pid}')
        _LOGGER.info(f'Device Model Name: {self._device_model_name}')
        if self._icon:
            _LOGGER.info(f'Icon: {self._icon}')

        # Start listener thread for continuous updates
        self._start_listener()

        # Send initial query to populate state
        try:
            _LOGGER.info(f'Sending initial query to {self._ip}')
            self._connect.send(self._get_package(CMD_QUERY, {}))
        except Exception as e:
            _LOGGER.warning(f'Failed to send initial query to {self._ip}: {e}')
    
    def _get_package(self, cmd: int, payload: dict) -> bytes:
        """
        package message
        :param cmd:int:
        :param payload:
        :return:
        """
        self._sn = get_sn()
        if CMD_SET == cmd:
            message = {
                'pv': 0,
                'cmd': cmd,
                'sn': self._sn,
                'msg': {
                    'attr': [int(item) for item in payload.keys()],
                    'data': payload,
                }
            }
        elif CMD_QUERY == cmd:
            message = {
                'pv': 0,
                'cmd': cmd,
                'sn': self._sn,
                'msg': {
                    'attr': [0],
                }
            }
        elif CMD_INFO == cmd:
            message = {
                'pv': 0,
                'cmd': cmd,
                'sn': self._sn,
                'msg': {}
            }
        else:
            raise Exception('CMD is not valid')
        
        payload_str = json.dumps(message, separators=(',', ':',))
        _LOGGER.info(f'_package={payload_str}')
        return bytes(payload_str + "\r\n", encoding='utf8')
    
    def _send_receiver(self, cmd: int, payload: dict) -> Union[dict, Any]:
        """
        send & receiver
        :param cmd:
        :param payload:
        :return:
        """
        try:
            if self._connect is None:
                if not self._reconnecting:
                    _LOGGER.debug(f'Connection to {self._ip} is None, not connected yet')
                return {}

            self._connect.send(self._get_package(cmd, payload))

            i = 10
            while i > 0:
                res = self._connect.recv(1024)
                # print(f'res={res},sn={self._sn},{self._sn in str(res)}')
                i -= 1
                #only allow same sn
                if self._sn in str(res):
                    payload = json.loads(res.strip())
                    if payload is None or len(payload) == 0:
                        return {}

                    if payload.get('msg') is None or type(payload['msg']) is not dict:
                        return {}

                    if payload['msg'].get('data') is None or type(payload['msg']['data']) is not dict:
                        return {}

                    return payload['msg']['data']

            return {}

        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            _LOGGER.warning(f'Connection error during send/recv: {e}')
            self._close_connection()
            self._reconnect()
            return {}
        except Exception as e:
            _LOGGER.error(f'Unexpected error in _send_receiver: {e}')
            return {}
    
    def _only_send(self, cmd: int, payload: dict) -> None:
        """
        send but not receiver
        :param cmd:
        :param payload:
        :return:
        """
        try:
            if self._connect is None:
                if not self._reconnecting:
                    _LOGGER.debug(f'Connection to {self._ip} is None, not connected yet')
                return

            self._connect.send(self._get_package(cmd, payload))
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            _LOGGER.warning(f'Connection error during send: {e}')
            self._close_connection()
            self._reconnect()
        except Exception as e:
            _LOGGER.error(f'Unexpected error in _only_send: {e}')
    
    def control(self, payload: dict) -> bool:
        """
        Control device using dpid.
        Updates local state optimistically (will be confirmed by device response).
        :param payload:
        :return:
        """
        # Send command
        self._only_send(CMD_SET, payload)

        # Optimistically update local state
        with self._state_lock:
            self._device_state.update(payload)

        return True
    
    def query(self) -> dict:
        """
        Query device state from cached values (no network call).
        State is updated by the listener thread.
        :return:
        """
        with self._state_lock:
            return self._device_state.copy()

    def _start_listener(self):
        """Start background thread to continuously read from socket"""
        if self._listener_running:
            _LOGGER.debug(f'Listener already running for {self._ip}')
            return

        def listener_thread():
            self._listener_running = True
            _LOGGER.info(f'Listener thread started for {self._ip}')
            buffer = ""

            while self._listener_running and self._connect:
                try:
                    # Read data from socket
                    data = self._connect.recv(1024)
                    if not data:
                        _LOGGER.warning(f'Socket closed by {self._ip}')
                        break

                    buffer += data.decode('utf-8')

                    # Process complete messages (terminated by \r\n)
                    while '\r\n' in buffer:
                        line, buffer = buffer.split('\r\n', 1)
                        if line:
                            self._process_message(line)

                except socket.timeout:
                    # Timeout is OK, just continue listening
                    continue
                except (BrokenPipeError, ConnectionResetError, OSError) as e:
                    _LOGGER.warning(f'Listener connection error for {self._ip}: {e}')
                    break
                except Exception as e:
                    _LOGGER.error(f'Listener error for {self._ip}: {e}', exc_info=True)
                    break

            _LOGGER.info(f'Listener thread stopped for {self._ip}')
            self._listener_running = False
            self._close_connection()
            self._reconnect()

        self._listener_thread = threading.Thread(target=listener_thread)
        self._listener_thread.daemon = True
        self._listener_thread.start()

    def _process_message(self, message: str):
        """Process incoming message from device"""
        try:
            data = json.loads(message)
            cmd = data.get('cmd')

            # Handle both query responses (CMD 2) and push notifications (CMD 10)
            if cmd in [CMD_QUERY, CMD_PUSH]:
                if data.get('msg') and isinstance(data['msg'], dict):
                    if data['msg'].get('data') and isinstance(data['msg']['data'], dict):
                        # Update shared state
                        with self._state_lock:
                            self._device_state.update(data['msg']['data'])
                        _LOGGER.debug(f'State updated for {self._ip}: {data["msg"]["data"]}')

        except json.JSONDecodeError as e:
            _LOGGER.warning(f'Invalid JSON from {self._ip}: {message[:100]}')
        except Exception as e:
            _LOGGER.error(f'Error processing message from {self._ip}: {e}')