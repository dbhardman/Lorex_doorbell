"""
Copied and modified from https://github.com/elad-bar/DahuaVTO2MQTT
Thanks to @elad-bar
"""
import struct
import sys
import logging
import json
import asyncio
import hashlib
import time
from threading import Timer
from typing import Optional, Callable, Dict, Any
import requests
from requests.auth import HTTPDigestAuth

PROTOCOLS = {True: "https", False: "http"}

_LOGGER: logging.Logger = logging.getLogger(__package__)

DAHUA_DEVICE_TYPE = "deviceType"
DAHUA_SERIAL_NUMBER = "serialNumber"
DAHUA_UUID = "UUID"
DAHUA_VERSION = "version"
DAHUA_BUILD_DATE = "buildDate"
DAHUA_CONSOLE_RUN_CMD = "console.runCmd"
DAHUA_GLOBAL_LOGIN = "global.login"
DAHUA_GLOBAL_KEEPALIVE = "global.keepAlive"
DAHUA_EVENT_MANAGER_ATTACH = "eventManager.attach"
DAHUA_CONFIG_MANAGER_GETCONFIG = "configManager.getConfig"
DAHUA_MAGICBOX_GETSOFTWAREVERSION = "magicBox.getSoftwareVersion"
DAHUA_MAGICBOX_GETDEVICETYPE = "magicBox.getDeviceType"
DAHUA_MAGICBOX_GETSYSINFO = "magicBox.getSystemInfo"

DAHUA_ALLOWED_DETAILS = [DAHUA_DEVICE_TYPE, DAHUA_UUID]


class DahuaVTOClient(asyncio.Protocol):
    """This class connects to the doorbell and receives event notifications"""

    requestId: int
    sessionId: int
    username: str
    password: str
    is_ssl: bool
    keep_alive_interval: int
    realm: Optional[str]
    random: Optional[str]
    dahua_details: Dict[str, Any]
    hold_time: int
    data_handlers: Dict[Any, Callable[[Any, str], None]]

    def __init__(self, host: str, username: str, password: str, is_ssl: bool, on_event):
        self.dahua_details = {}
        self.host = host
        self.username = username
        self.password = password
        self.is_ssl = is_ssl
        self.realm = None
        self.random = None
        self.request_id = 1
        self.sessionId = 0
        self.keep_alive_interval = 0
        self.transport = None
        self.hold_time = 0
        self.lock_status = {}
        self.data_handlers = {}
        self._connected = False

        # hook back to HA
        self._loop = asyncio.get_event_loop()
        self._on_event = on_event

    def connection_made(self, transport):
        _LOGGER.debug("Connection established")
        self._connected = True
        try:
            self.transport = transport
            self.pre_login()

        except Exception as ex:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            _LOGGER.error(
                f"Failed to handle message, error: {ex}, Line: {exc_tb.tb_lineno}"
            )

    def data_received(self, data):
        try:
            message = self.parse_response(data)

            message_id = message.get("id")

            handler: Callable = self.data_handlers.get(message_id, self.handle_default)
            handler(message)

        except Exception as ex:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            _LOGGER.error(
                f"Failed to handle message, error: {ex}, Line: {exc_tb.tb_lineno}"
            )

    def handle_notify_event_stream(self, params):
        try:
            _LOGGER.debug(f"Lorex Event: {params}")
            event_list = params.get("eventList")

            for message in event_list:
                for k in self.dahua_details:
                    if k in DAHUA_ALLOWED_DETAILS:
                        message[k] = self.dahua_details.get(k)

                self._on_event(message)

        except Exception as ex:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            _LOGGER.error(
                f"Failed to handle event, error: {ex}, Line: {exc_tb.tb_lineno}"
            )

    def handle_default(self, message):
        _LOGGER.debug(f"Data received without handler: {message}")

    def eof_received(self):
        _LOGGER.debug("Server sent EOF message")

        self._loop.stop()

    def connection_lost(self, exc):
        _LOGGER.error("server closed the connection")

        self._loop.stop()

    def send(self, action, handler, params=None):
        if params is None:
            params = {}

        self.request_id += 1

        message_data = {
            "id": self.request_id,
            "session": self.sessionId,
            "magic": "0x1234",
            "method": action,
            "params": params,
        }

        self.data_handlers[self.request_id] = handler

        if not self.transport.is_closing():
            message = self.convert_message(message_data)

            self.transport.write(message)

    @staticmethod
    def convert_message(data):
        message_data = json.dumps(data, indent=4)

        header = struct.pack(">L", 0x20000000)
        header += struct.pack(">L", 0x44484950)
        header += struct.pack(">d", 0)
        header += struct.pack("<L", len(message_data))
        header += struct.pack("<L", 0)
        header += struct.pack("<L", len(message_data))
        header += struct.pack("<L", 0)

        message = header + message_data.encode("utf-8")

        return message

    def pre_login(self):
        _LOGGER.debug("Prepare pre-login message")

        def handle_pre_login(message):
            error = message.get("error")
            params = message.get("params")
            _LOGGER.debug(f"Message: {message}")

            if error is not None:
                error_message = error.get("message")

                if error_message == "Component error: login challenge!":
                    self.random = params.get("random")
                    self.realm = params.get("realm")
                    self.sessionId = message.get("session")

                    self.login()

        request_data = {
            "clientType": "",
            "ipAddr": "(null)",
            "loginType": "Direct",
            "userName": self.username,
            "password": "",
        }

        self.send(DAHUA_GLOBAL_LOGIN, handle_pre_login, request_data)

    def login(self):
        _LOGGER.debug("Prepare login message")

        def handle_login(message):
            params = message.get("params")
            keep_alive_interval = params.get("keepAliveInterval")
            _LOGGER.debug(f"Login response: {message}")

            if keep_alive_interval is not None:
                self.keep_alive_interval = keep_alive_interval - 5
                # move these so they go sequential one after another
                # after event manager started no other info comes from camera
                # version->devicetype->serial_number->access_control->eventmanager
                self._connected = True
                self.load_version()
                # self.load_serial_number()
                # self.load_device_type()
                # self.load_access_control()
                # self.attach_event_manager()

                Timer(self.keep_alive_interval, self.keep_alive).start()

        password = self._get_hashed_password(
            self.random,
            self.realm,
            self.username,
            self.password,
        )
        request_data = {
            "clientType": "",
            "ipAddr": "(null)",
            "loginType": "Direct",
            "userName": self.username,
            "password": password,
            "authorityType": "Default",
        }

        self.send(DAHUA_GLOBAL_LOGIN, handle_login, request_data)

    def attach_event_manager(self):
        _LOGGER.debug("Attach event manager")

        def handle_attach_event_manager(message):
            method = message.get("method")
            params = message.get("params")

            if method == "client.notifyEventStream":
                self.handle_notify_event_stream(params)

        request_data = {"codes": ["All"]}

        self.send(DAHUA_EVENT_MANAGER_ATTACH, handle_attach_event_manager, request_data)

    # request the version and build date from the device
    def load_version(self):
        _LOGGER.debug("Get version")

        def handle_version(message):
            params = message.get("params")
            version_details = params.get("version", {})
            build_date = version_details.get("BuildDate")
            version = version_details.get("Version")

            self.dahua_details[DAHUA_VERSION] = version
            self.dahua_details[DAHUA_BUILD_DATE] = build_date

            _LOGGER.debug(f"Version: {version}, Build Date: {build_date}")
            # call next item
            self.load_device_type()

        self.send(DAHUA_MAGICBOX_GETSOFTWAREVERSION, handle_version)

    # request the deviceType ie model of the device
    def load_device_type(self):
        _LOGGER.debug("Get device type")

        def handle_device_type(message):
            params = message.get("params")
            device_type = params.get("type")

            self.dahua_details[DAHUA_DEVICE_TYPE] = device_type

            _LOGGER.debug(f"Device Type: {device_type}")
            self.load_serial_number()

        self.send(DAHUA_MAGICBOX_GETDEVICETYPE, handle_device_type)

    # this does not actually load the serial number but the UUID of the device
    def load_serial_number(self):
        _LOGGER.debug("Get serial number")

        def handle_serial_number(message):
            params = message.get("params")
            table = params.get("table", {})
            serial_number = table.get("UUID")

            self.dahua_details[DAHUA_UUID] = serial_number

            _LOGGER.debug(f"UUID: {serial_number}")
            # _LOGGER.debug(f"config: {message}")
            # self.attach_event_manager()
            self.config()

        request_data = {"name": "T2UServer"}

        self.send(DAHUA_CONFIG_MANAGER_GETCONFIG, handle_serial_number, request_data)

    def keep_alive(self):
        _LOGGER.debug("Keep alive")

        def handle_keep_alive(message):
            Timer(self.keep_alive_interval, self.keep_alive).start()

        request_data = {"timeout": self.keep_alive_interval, "action": True}

        self.send(DAHUA_GLOBAL_KEEPALIVE, handle_keep_alive, request_data)

    def run_cmd_mute(self, payload: dict):
        _LOGGER.debug("Keep alive")

        def handle_run_cmd_mute(message):
            _LOGGER.debug("Call was muted")

        request_data = {"command": "hc"}

        self.send(DAHUA_CONSOLE_RUN_CMD, handle_run_cmd_mute, request_data)

    # gets config data for the devic which includes the "real" serialNumber
    # once we have that info we can send a connected message and attach
    # the event stream
    def config(self):
        _LOGGER.debug("Getting config")

        def handle_config(message):
            _LOGGER.debug(f"Config: {message}")
            params = message.get("params")
            serial_number = params.get("serialNumber")
            self.dahua_details[DAHUA_SERIAL_NUMBER] = serial_number
            # send a message that we are connected before we attach the event manager
            self.handle_notify_event_stream(self.create_connect_message())
            self.attach_event_manager()

        self.send(DAHUA_MAGICBOX_GETSYSINFO, handle_config)

    # create a message to notify that we are connected and give the device type and UUID
    def create_connect_message(self):
        ctime = time.time()
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ctime))
        data = {"ID": [0], "localeTime": time_str, "UTC": round(ctime, 1)}
        body = {"Action": "Start", "Code": "LorexConnected", "Data": data}
        message = {"SID": 513, "eventList": [body]}
        return message

    @property
    def is_connected(self):
        return self._connected

    @staticmethod
    def parse_response(response):
        result = None

        try:
            response_parts = str(response).split("\\x00")
            for response_part in response_parts:
                if response_part.startswith("{"):
                    end = response_part.rindex("}") + 1
                    message = response_part[0:end]

                    result = json.loads(message)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            _LOGGER.error(
                f"Failed to read data: {response}, error: {e}, Line: {exc_tb.tb_lineno}"
            )

        return result

    @staticmethod
    def _get_hashed_password(random, realm, username, password):
        password_str = f"{username}:{realm}:{password}"
        password_bytes = password_str.encode("utf-8")
        password_hash = hashlib.md5(password_bytes).hexdigest().upper()
        # added this to remove - from the random from 2k camera
        # change the random_str line to newRandom to have the - removed
        char_to_remove = "-"
        newRandom = ""
        for character in random:
            if character != char_to_remove:
                newRandom += character

        random_str = f"{username}:{random}:{password_hash}"
        random_bytes = random_str.encode("utf-8")
        random_hash = hashlib.md5(random_bytes).hexdigest().upper()

        return random_hash
