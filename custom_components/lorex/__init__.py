"""The Lorex integration."""
import asyncio
from typing import Any, Dict
import logging
import time
import threading
import sys

from datetime import timedelta
from collections.abc import Mapping

from aiohttp import ClientError, ClientResponseError
from homeassistant.components.generic.const import CONF_STREAM_SOURCE

# from homeassistant.components.lorex.camera import LorexCamera
from homeassistant.components.stream.const import CONF_RTSP_TRANSPORT
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, PlatformNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_HOST, EVENT_HOMEASSISTANT_STOP
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from .const import *
from .vto import DahuaVTOClient

from .const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    #  CONF_HOST,
    DOMAIN,
    PLATFORMS,
    CONF_RTSP_PORT,
)


SCAN_INTERVAL_SECONDS = timedelta(seconds=30)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: Config):
    """
    Set up this integration with the UI. YAML is not supported.
    https://developers.home-assistant.io/docs/asyncio_working_with_async/
    """
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    host = entry.data.get(CONF_HOST)
    port = int(entry.data.get(CONF_PORT))
    rtsp_port = int(entry.data.get(CONF_RTSP_PORT))
    name = entry.data.get(CONF_NAME)

    lorex_device = LorexDevice(
        hass,
        host,
        port,
        rtsp_port,
        username,
        password,
        name,
        entry,
    )
    # other platforms are called later by the lorex_device
    # due to slow communication responses

    hass.data[DOMAIN][entry.entry_id] = lorex_device

 
    # ensure we stop threads when home assistant stops
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, lorex_device.async_stop)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class LorexDevice(DataUpdateCoordinator):
    """class to manage overall communication with device"""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        rtsp_port: int,
        username: str,
        password: str,
        name: str,
        entry: ConfigEntry,
    ) -> None:
        self.platforms = []
        self.hass = hass
        self.host = host
        self.username = username
        self.password = password
        self.name = name
        self.port = port
        self._motion = False
        self._human_motion = False
        self._button = False
        self.rtsp_port = rtsp_port
        self._deviceType = ""
        self._serialNumber = ""
        self._entry = entry
        # A dictionary of event name (CrossLineDetection, VideoMotion, etc) to a listener for that event
        self._dahua_event_listeners: Dict[str, CALLBACK_TYPE] = dict()
        # add the event listeners mostly default to None except the ones currently requiring response
        # any new events not listed will trigger a debug error in the log
        self.setup_listeners()

        # start the new thread which will communicate with the device
        self.event_listener = DahuaVtoEventThread(
            hass, self.on_event, self.host, 5000, self.username, self.password
        )

        self.initialized = False
        self.model = ""
        self._connected = False
        self.hass = hass

        # last thing is to start the event listener and start recieving events from the device
        self.event_listener.start()
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL_SECONDS
        )

    def on_event(self, event: dict):
        # we only care about motion and door press events
        # and the initial connection event 
        event_type = event["Code"]
        event_action = event["Action"]
        _LOGGER.debug(f"Lorex event: {event_type} Action: {event_action}")
        if event_type == "VideoMotion":
            if event_action == "Start":
                self._motion = True
            else:
                self._motion = False
        # appear to get this message when a person is in view
        if event_type == "IntelliFrame":
            data = event["Data"]
            event_action = data["Action"]
            if event_action == "Start":
                self._human_motion = True
            else:
                self._human_motion = False
        # this message sent when the doorbell button pressed
        if event["Code"] == "AlarmLocal":
            if event_action == "Start":
                self._button = True
            else:
                self._button = False
        # this is a made up message to show that the underlying htread has connectd to the device
        if event_type == "LorexConnected":
            self._deviceType = event.get("deviceType")
            self._serialNumber = event.get("UUID")
            _LOGGER.debug(f"device type: {self._deviceType} Serial#: {self._serialNumber}")
            self._connected = True
            self.hass.bus.fire("lorex_connection_event", event)
        # call the listener for the event  supplied by the entities
        listener = self._dahua_event_listeners[event_type]
        if listener is not None:
            _LOGGER.debug(f"calling lorex listener: {event_type}")
            listener()
        return True

    async def async_stop(self, event: Any):
        """Stop seperate thread"""
        self.event_listener.stop()

    def add_event_listener(self, event_name: str, listener: CALLBACK_TYPE):
        """Adds an event listener for the given event (CrossLineDetection, etc).
        This callback will be called when the event fires"""
        if listener is not None:
          _LOGGER.info(f"Listener added for: {event_name}")
        self._dahua_event_listeners[event_name] = listener

    def camera_device_info(self):
        device_info = {
            "platform": DOMAIN,
            CONF_NAME: self.name,
            CONF_HOST: self.host,
            CONF_USERNAME: self.username,
            CONF_PASSWORD: self.password,
            CONF_STREAM_SOURCE: self.rtsp_url(),
        }
        return device_info

    def rtsp_url(self):
        url = f"rtsp://{self.host}:{self.rtsp_port}/cam/realmonitor?channel=1&subtype=1"
        return url

    async def is_connnected(self):
        return self.connected

    def get_serial_number(self):
        return self._serialNumber

    def get_device_type(self):
        return self._deviceType

    def get_motion(self):
        return self._motion

    def get_pressed(self):
        return self._button
    
    def get_human_motion(self):
        return self._human_motion


    #once we have recieved the connected event from the VTO thread then setup the entities
    def create_entities(self):
        for platform in PLATFORMS:
            # if entry.options.get(platform, True):
            self.platforms.append(platform)
            _LOGGER.info(f"lorex setup platform: {platform}")
            #TODO async_add_job deprecated change to async_run_hass_job
            self.hass.async_add_job(
                self.hass.config_entries.async_forward_entry_setup(self._entry, platform)
            )        

    def setup_listeners(self):
        """Add the event listeners for the events sent by the doorbell
            initially all listeners have a NULL function callback, but they prevent log errors from the vto thread        
        """
        for t in LOREX_EVENTS:
            self.add_event_listener(t, None)
        # add connection listener to create the binary sensors and camera once the device is connected
        self.add_event_listener("LorexConnected", self.create_entities)






class DahuaVtoEventThread(threading.Thread):
    """Connects to device and subscribes to events. To capture motion detection events and doorbell press"""

    def __init__(
        self,
        hass: HomeAssistant,
        on_receive_vto_event,
        host: str,
        port: int,
        username: str,
        password: str,
    ):
        """Construct a thread listening for events."""
        threading.Thread.__init__(self)
        self.hass = hass
        self.stopped = threading.Event()
        self.on_receive_vto_event = on_receive_vto_event
        self.started = False
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._is_ssl = False
        self.vto_client = None

    def run(self):
        """Fetch VTO events"""
        self.started = True
        _LOGGER.debug("Starting DahuaVtoEventThread")

        while True:
            try:
                if not self.started:
                    _LOGGER.debug("Exiting DahuaVtoEventThread")
                    return

                _LOGGER.debug("Connecting to VTO event stream")

                # TODO: How do I integrate this in with the HA loop? Does it even matter? I think so because
                # how well do we know when we are shutting down HA?
                loop = asyncio.new_event_loop()

                def vto_client_lambda():
                    # Notice how we set vto_client client here. This is so nasty, I'm embarrassed to put this into the
                    # code, but I'm not a python expert and it works well enough and this is just a spare time project
                    # so here it is. We need to capture an instance of the DahuaVTOClient so we can use it later on
                    # in switches to execute commands on the VTO. We need the client connected to the event loop
                    # which is done through loop.create_connection. This makes it awkward to capture... which is why
                    # I've done this. I'm sure there's a better way :)
                    self.vto_client = DahuaVTOClient(
                        self._host,
                        self._username,
                        self._password,
                        self._is_ssl,
                        self.on_receive_vto_event,
                    )
                    return self.vto_client

                _LOGGER.info("Lorex: port = %i, host = %s", self._port, self._host)
                client = loop.create_connection(
                    vto_client_lambda, host=self._host, port=self._port
                )

                loop.run_until_complete(client)
                loop.run_forever()
                loop.close()

                _LOGGER.warning(
                    "Disconnected from VTO, will try to connect in 5 seconds"
                )

                time.sleep(5)

            except Exception as ex:
                if not self.started:
                    _LOGGER.debug("Exiting DahuaVtoEventThread")
                    return
                exc_type, exc_obj, exc_tb = sys.exc_info()
                line = exc_tb.tb_lineno
                _LOGGER.error(
                    "Connection to VTO failed will try to connect in 30 seconds, error: {ex}, Line: {line}",
                )

                time.sleep(30)

    def stop(self):
        """Signals to the thread loop that we should stop"""
        if self.started:
            _LOGGER.info("Stopping DahuaVtoEventThread")
            self.stopped.set()
            self.started = False


