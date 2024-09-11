"""The Lorex integration."""

import asyncio
from collections import defaultdict
from datetime import timedelta
import logging
import sys
from typing import Any

from homeassistant.components.generic.const import CONF_STREAM_SOURCE

# from homeassistant.components.lorex.camera import LorexCamera
from homeassistant.components.stream.const import CONF_RTSP_TRANSPORT
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CALLBACK_TYPE, Config, HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE,
)
from .const import (
    ALARMLOCAL,
    INTELLIFRAME,
    LOREX_CLIENT,
    LOREX_CONNECTION,
    LOREX_GETTING_EVENTS,
    LOREX_ID,
    LOREX_MODEL,
    LOREX_TIME_STAMP,
    VIDEOMOTION,
    LorexType,
)
from .lorex_doorbell_client import LorexDoorbellClient

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

    # username = entry.data.get(CONF_USERNAME)
    # password = entry.data.get(CONF_PASSWORD)
    # host = entry.data.get(CONF_HOST)
    # name = entry.data.get(CONF_NAME)

    lorex_coor = LorexCoordinator(
        hass,
        entry,
    )

    # other platforms are called later by the lorex_device
    # due to slow communication responses
    await lorex_coor.is_connected()
    # await lorex_coor.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = lorex_coor

    for platform in PLATFORMS:
        # if entry.options.get(platform, True):
        lorex_coor.platforms.append(platform)
        _LOGGER.info(f"lorex setup platform: {platform}")
        await hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    # ensure we stop threads when home assistant stops
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, lorex_coor.async_stop)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class LorexCoordinator(DataUpdateCoordinator):
    """class to manage overall communication with device"""

    data: dict[str, Any]

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise coordinator."""

        self.platforms = []
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
        # self._dahua_event_listeners: dict[str, CALLBACK_TYPE] = dict()
        self.entity_callbacks = defaultdict(list)
        self.data = {}
        self.data[LOREX_CONNECTION] = False
        self.data[INTELLIFRAME] = False
        self.data[ALARMLOCAL] = False
        self.data[VIDEOMOTION] = False
        self.data[LOREX_MODEL] = ""
        self.data[LOREX_ID] = ""
        self.data[LOREX_TIME_STAMP] = ""

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({entry.unique_id})",
            # update_method=self._async_update_data,
            # update_interval=None,
        )
        # last thing is to start the doorbell and start recieving events from the device
        asyncio.run_coroutine_threadsafe(self.run_doorbell(), self.hass.loop)

    def on_event(self, event: dict[str, Any]):
        """Recieve callback from doorbell device."""
        if event[LOREX_CONNECTION] and not event[LOREX_GETTING_EVENTS]:
            event[LOREX_CLIENT].attach_event_manager()
        self._connected = event[LOREX_CONNECTION]
        if self.data is not None:
            if self.data == event:
                return True
        self.data = event.copy()
        _LOGGER.debug("Event received from API: %s", self.data)
        # self.async_set_updated_data(event)
        for cb in self.entity_callbacks[event[LOREX_ID]]:
            cb()
        return True

    async def async_stop(self, event: Any):
        """Stop seperate thread."""
        self._failed_connection = True
        self.data[LOREX_CLIENT].close_connection()

    def add_callback(self, entity_id: str, to_call: CALLBACK_TYPE):
        """Add call back from entity."""
        if to_call is not None:
            self.entity_callbacks[entity_id].append(to_call)

    def camera_device_info(self):
        """Return camera information."""
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

    async def is_connected(self):
        while not self._connected and not self._failed_connection:
            await asyncio.sleep(0.2)
        _LOGGER.info("Doorbell connected.")
        return self._connected

    async def _async_update_data(self):
        try:
            if not self.data[LOREX_CONNECTION]:
                await self.is_connected()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        return self.data

    async def run_doorbell(self):
        """Run the doorbell client recive messages from client at on_event."""
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

        except Exception as ex:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            if not self.started:
                _LOGGER.debug("Exiting Lorex doorbell Client.")
                return
            line = exc_tb.tb_lineno
            _LOGGER.error(
                f"Connection to Lorex doorbell failed. error: {ex}, Line: {line}",
            )
        finally:
            transport.close()
