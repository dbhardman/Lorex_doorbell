"""API for doorbell."""

from _collections_abc import Callable
import asyncio
import hashlib
import json
import logging
import struct
import sys
from threading import Timer
from typing import Any, Optional

from .const import (
    ALARMLOCAL,
    DAHUA_BUILD_DATE,
    DAHUA_CONFIG_MANAGER_GETCONFIG,
    DAHUA_DEVICE_TYPE,
    DAHUA_EVENT_MANAGER_ATTACH,
    DAHUA_GLOBAL_KEEPALIVE,
    DAHUA_GLOBAL_LOGIN,
    DAHUA_MAGICBOX_GETDEVICETYPE,
    DAHUA_MAGICBOX_GETSOFTWAREVERSION,
    DAHUA_MAGICBOX_GETSYSINFO,
    DAHUA_SERIAL_NUMBER,
    DAHUA_VERSION,
    INTELLIFRAME,
    LOREX_CLIENT,
    LOREX_CONNECTION,
    LOREX_DOORBELL_CODES,
    LOREX_GETTING_EVENTS,
    LOREX_ID,
    LOREX_MODEL,
    LOREX_TIME_STAMP,
    VIDEOMOTION,
)

_LOGGER = logging.getLogger(__name__)


class LorexDoorbellClient(asyncio.Protocol):
    """Handles connection and communication with doorbell."""

    request_id: int
    session_id: int
    keep_alive_interval: int
    realm: Optional[str]
    random: Optional[str]
    dahua_details: dict[str, Any]
    hold_time: int
    data_handlers: dict[Any, Callable[[Any, str], None]]
    dahua_config: dict[str, Any]
    status: dict[str, Any]

    def __init__(self, config: dict[str, Any], on_con_lost) -> None:
        """Init."""
        self.dahua_config = config
        self.dahua_details = {}
        self.realm = None
        self.random = None
        self.request_id = 1
        self.session_id = 0
        self.keep_alive_interval = 0
        self.transport = None
        self.hold_time = 0
        self.data_handlers = {}
        self.on_con_lost = on_con_lost
        self.on_event = config["on_event"]
        self.status = {}
        self.status[LOREX_CONNECTION] = False
        self.status[INTELLIFRAME] = False
        self.status[ALARMLOCAL] = False
        self.status[VIDEOMOTION] = False
        self.status[LOREX_MODEL] = ""
        self.status[LOREX_ID] = ""
        self.status[LOREX_TIME_STAMP] = ""
        self.status[LOREX_GETTING_EVENTS] = False
        self.status[LOREX_CLIENT] = None

    def connection_made(self, transport):
        """Overide of base call will receive message on connect."""
        _LOGGER.debug("Connection established")

        try:
            self.transport = transport

            self.pre_login()

        except Exception as ex:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            _LOGGER.error(
                f"Failed to handle message, error: {ex}, Line: {exc_tb.tb_lineno}"
            )

    # overide of base calls to receive data
    def data_received(self, data):
        """Override of base class. called when data recieved from the server."""
        try:
            message = self.parse_response(data)
            _LOGGER.debug(f"Data received: {message}")
            # print(f"Data: {message}\r\r")

            message_id = message.get("id")

            handler: Callable = self.data_handlers.get(message_id, self.handle_default)
            handler(message)

        except Exception as ex:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            _LOGGER.error(
                f"Failed to handle message, error: {ex}, Line: {exc_tb.tb_lineno}"
            )

    def handle_notify_event_stream(self, params):
        """Process events recieved from doorbell.

        then send an update to the callback with status.
        """
        try:
            _LOGGER.debug(f"Event: {params}")
            event_list = params.get("eventList")

            for message in event_list:
                code = message.get("Code")
                data = message.get("Data")
                if "Action" in data:
                    action = data.get("Action")
                else:
                    action = message.get("Action")
                if code in LOREX_DOORBELL_CODES:
                    self.status[LOREX_TIME_STAMP] = data.get("LocaleTime")
                    if action == "Start":
                        self.status[code] = True
                    elif action == "Stop":
                        self.status[code] = False
                    self.on_event(self.status)

        except Exception as ex:
            exc_type, exc_obj, exc_tb = sys.exc_info()

            _LOGGER.error(
                f"Failed to handle event, error: {ex}, Line: {exc_tb.tb_lineno}"
            )

    def handle_default(self, message):
        """Default message handler."""
        _LOGGER.debug(f"Data received without handler: {message}")

    def eof_received(self):
        _LOGGER.debug("Server sent EOF message")

    def connection_lost(self, exc):
        """Connection lost from server."""
        _LOGGER.error("Server closed the connection")
        self.status[LOREX_CONNECTION] = False
        self.on_event(self.status)
        if not self.on_con_lost.done():
            self.on_con_lost.set_result(True)

    def close_connection(self):
        """Close the connection."""
        self.status[LOREX_CONNECTION] = False
        self.on_event(self.status)
        if not self.on_con_lost.done():
            self.on_con_lost.set_result(True)

    def send(self, action, handler, params=None):
        """Send a command."""
        if params is None:
            params = {}

        self.request_id += 1

        message_data = {
            "id": self.request_id,
            "session": self.session_id,
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
        """Remove junk from data."""
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
        """Send login to doorbell."""
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
                    self.session_id = message.get("session")

                    self.login()

        request_data = {
            "clientType": "",
            "ipAddr": "(null)",
            "loginType": "Direct",
            "userName": self.dahua_config["username"],
            "password": "",
        }

        self.send(DAHUA_GLOBAL_LOGIN, handle_pre_login, request_data)

    def login(self):
        """Respond to login challenge."""
        _LOGGER.debug("Prepare login message")

        def handle_login(message):
            params = message.get("params")
            keep_alive_interval = params.get("keepAliveInterval")
            _LOGGER.debug(f"Login response: {message}")

            if keep_alive_interval is not None:
                self.keep_alive_interval = keep_alive_interval - 5
                self.status[LOREX_CONNECTION] = True
                Timer(self.keep_alive_interval, self.keep_alive).start()
                self.load_version()

        password = self._get_hashed_password(
            self.random,
            self.realm,
            self.dahua_config["username"],
            self.dahua_config["password"],
        )
        self._hashedPassword = password
        request_data = {
            "clientType": "",
            "ipAddr": "(null)",
            "loginType": "Direct",
            "userName": self.dahua_config["username"],
            "password": password,
            "authorityType": "Default",
        }

        self.send(DAHUA_GLOBAL_LOGIN, handle_login, request_data)

    def attach_event_manager(self):
        """Request server send all notifications."""
        _LOGGER.debug("Attach event manager")

        def handle_attach_event_manager(message):
            method = message.get("method")
            params = message.get("params")

            if method == "client.notifyEventStream":
                self.handle_notify_event_stream(params)

        request_data = {"codes": ["All"]}
        self.status[LOREX_GETTING_EVENTS] = True
        self.send(DAHUA_EVENT_MANAGER_ATTACH, handle_attach_event_manager, request_data)

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

    def load_device_type(self):
        _LOGGER.debug("Get device type")

        def handle_device_type(message):
            params = message.get("params")
            device_type = params.get("type")

            self.dahua_details[DAHUA_DEVICE_TYPE] = device_type
            self.status[LOREX_MODEL] = device_type

            _LOGGER.debug(f"Device Type: {device_type}")
            self.load_serial_number()

        self.send(DAHUA_MAGICBOX_GETDEVICETYPE, handle_device_type)

    def load_serial_number(self):
        _LOGGER.debug("Get serial number")

        def handle_serial_number(message):
            params = message.get("params")
            table = params.get("table", {})
            serial_number = table.get("UUID")

            self.dahua_details[DAHUA_SERIAL_NUMBER] = serial_number
            self.status[LOREX_ID] = serial_number

            _LOGGER.debug(f"Serial Number: {serial_number}")
            _LOGGER.debug(f"config: {message}")
            self.status[LOREX_CLIENT] = self
            self.on_event(self.status)
            # self.attach_event_manager()

        request_data = {"name": "T2UServer"}

        self.send(DAHUA_CONFIG_MANAGER_GETCONFIG, handle_serial_number, request_data)

    def keep_alive(self):
        _LOGGER.debug("Keep alive")

        def handle_keep_alive(message):
            Timer(self.keep_alive_interval, self.keep_alive).start()

        request_data = {"timeout": self.keep_alive_interval, "action": True}

        self.send(DAHUA_GLOBAL_KEEPALIVE, handle_keep_alive, request_data)

    def config(self):
        _LOGGER.debug("Getting config")

        def handle_config(message):
            _LOGGER.debug(f"Config: {message}")
            self.attach_event_manager()

        request_data = {}

        self.send(DAHUA_MAGICBOX_GETSYSINFO, handle_config, request_data)

    @staticmethod
    def parse_response(response):
        """Convert received data to json."""
        result = None

        try:
            response_parts = str(response).split("\\x00")
            for response_part in response_parts:
                if response_part.startswith("{") and not response_part.startswith(
                    "{\\x04"
                ):
                    end = response_part.rindex("}") + 1
                    message = response_part[0:end]

                    result = json.loads(message)
                    if len(result):
                        break

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
        random_str = f"{username}:{random}:{password_hash}"
        random_bytes = random_str.encode("utf-8")
        random_hash = hashlib.md5(random_bytes).hexdigest().upper()

        return random_hash
