"""The Lorex integration."""

from _collections_abc import Callable
import asyncio
from datetime import timedelta
import logging
import sys
from threading import Timer
from typing import Any

from homeassistant.components.generic.const import CONF_STREAM_SOURCE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Config, HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import (
    ALARMLOCAL,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    INTELLIFRAME,
    LOREX_CLIENT,
    LOREX_CONNECTION,
    LOREX_GETTING_EVENTS,
    LOREX_ID,
    LOREX_MODEL,
    LOREX_TIME_STAMP,
    PLATFORMS,
    STARTUP_MESSAGE,
    VIDEOMOTION,
)
from .lorex_doorbell_client import LorexDoorbellClient

SCAN_INTERVAL_SECONDS = timedelta(seconds=30)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration with the UI. YAML is not supported.

    https://developers.home-assistant.io/docs/asyncio_working_with_async/
    """
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    lorex_coor = LorexCoordinator(
        hass,
        entry,
    )

    # Wait on connection before configuring entities
    await lorex_coor.is_connected()

    hass.data[DOMAIN][entry.entry_id] = lorex_coor

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # ensure we stop threads when home assistant stops
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, lorex_coor.async_stop)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


class LorexCoordinator:
    """Manage overall communication with device."""

    data: dict[str, Any]
    entity_callbacks: dict[str, Callable]

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise coordinator."""

        # self.platforms = []
        self.hass = hass
        self.host = entry.data[CONF_HOST]
        self.username = entry.data[CONF_USERNAME]
        self.password = entry.data[CONF_PASSWORD]
        self.name = entry.data[CONF_NAME]
        self.port = 5000
        self.rtsp_port = 554
        self._deviceType = "doorbell"
        self._entry = entry
        self._failed_connection = False
        self._connected = False
        self._hass_closing = False
        self.reconnect_interval = 60
        # self._dahua_event_listeners: dict[str, CALLBACK_TYPE] = dict()
        self.entity_callbacks = set()
        self.data = {}
        self.data[LOREX_CONNECTION] = False
        self.data[INTELLIFRAME] = False
        self.data[ALARMLOCAL] = False
        self.data[VIDEOMOTION] = False
        self.data[LOREX_MODEL] = ""
        self.data[LOREX_ID] = ""
        self.data[LOREX_TIME_STAMP] = ""

        # last thing is to start the doorbell and start recieving events from the device
        asyncio.run_coroutine_threadsafe(self.run_doorbell(), self.hass.loop)

    def on_event(self, event: dict[str, Any]):
        """Recieve callback from doorbell device."""
        self.data = event.copy()
        if event[LOREX_CONNECTION] and not event[LOREX_GETTING_EVENTS]:
            event[LOREX_CLIENT].attach_event_manager()
        self._connected = event[LOREX_CONNECTION]
        # if something has changed call the approriate callback
        for cb in self.entity_callbacks:
            cb()
        _LOGGER.debug("Event received from API: %s", self.data)
        # if the connection has closed.  try connect again after interval
        if not self._connected and not self._hass_closing:
            Timer(self.reconnect_interval, self.reconnect).start()
        return True

    async def async_stop(self, event: Any):
        """Stop seperate thread.

        remove callbacks and close the connection.
        """
        self._failed_connection = True
        self._hass_closing = True
        self.data[LOREX_CLIENT].close_connection()

    def add_callback(self, to_call: Callable[[], None]):
        """Add call back from entity."""
        if to_call is not None:
            self.entity_callbacks.add(to_call)

    def remove_callback(self, to_call: Callable[[], None]):
        """Remove entity callback."""
        self.entity_callbacks.discard(to_call)

    def camera_device_info(self):
        """Return camera information."""
        return {
            "platform": DOMAIN,
            CONF_HOST: self.host,
            CONF_USERNAME: self.username,
            CONF_PASSWORD: self.password,
            CONF_STREAM_SOURCE: self.rtsp_url(),
        }

    def rtsp_url(self) -> str:
        """Camera URL."""
        return (
            f"rtsp://{self.host}:{self.rtsp_port}/cam/realmonitor?channel=1&subtype=1"
        )

    async def is_connected(self):
        """Connect state."""
        while not self._connected and not self._failed_connection:
            await asyncio.sleep(0.2)
        _LOGGER.info("Doorbell connected")
        return self._connected

    async def _async_update_data(self):
        """Not needed?."""
        try:
            if not self.data[LOREX_CONNECTION]:
                await self.is_connected()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        return self.data

    def reconnect(self):
        """Reconnect if Home Assistant not closing.

        Limit retries to once per hour.
        """
        self.reconnect_interval += 60
        if self.reconnect_interval > 3600:
            self.reconnect_interval = 3600
        if not self._connected and not self._hass_closing:
            asyncio.run_coroutine_threadsafe(self.run_doorbell(), self.hass.loop)

    async def run_doorbell(self):
        """Run the doorbell client receive messages from client at on_event."""
        cd = {}
        cd["username"] = self.username
        cd["password"] = self.password
        cd["port"] = 5000
        cd["host"] = self.host
        cd["on_event"] = self.on_event

        loop = asyncio.get_running_loop()
        on_con_lost = loop.create_future()

        transport, protocol = await loop.create_connection(
            lambda: LorexDoorbellClient(cd, on_con_lost), cd["host"], cd["port"]
        )

        try:
            await on_con_lost

        except Exception as ex:  # noqa: BLE001
            exc_type, exc_obj, exc_tb = sys.exc_info()
            if not self.started:
                _LOGGER.debug("Exiting Lorex doorbell Client")
                # return
            line = exc_tb.tb_lineno
            _LOGGER.error(
                "Connection to Lorex doorbell failed. error: %s, Line: %s", ex, line
            )
        finally:
            transport.close()
            self._connected = False
