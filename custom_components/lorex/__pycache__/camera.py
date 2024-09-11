"""Support for doorbell Cameras  uses RTSP only."""

import logging
from typing import Any

from homeassistant.components.generic.camera import (
    CONF_CONTENT_TYPE,
    CONF_FRAMERATE,
    CONF_LIMIT_REFETCH_TO_URL_CHANGE,
    CONF_NAME,
    CONF_VERIFY_SSL,
    GenericCamera,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .__init__ import CONF_STREAM_SOURCE, LorexCoordinator
from .const import DOMAIN, LOREX_ID, LOREX_MODEL

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Camera platform setup."""
    lorex_coord: LorexCoordinator = hass.data[DOMAIN][entry.entry_id]

    if lorex_coord:
        async_add_entities([LorexCamera(hass, lorex_coord)])


class LorexCamera(GenericCamera):
    """LorexCamera, a generic camera with rtsp url."""

    _device_info: dict[str, Any]

    def __init__(self, hass, lorex_coord: LorexCoordinator) -> None:
        """Initialize a camera from Lorex_device."""
        _LOGGER.debug("Initializing the lorex camera")
        self._device_info = lorex_coord.camera_device_info()
        self._device_info[CONF_LIMIT_REFETCH_TO_URL_CHANGE] = False
        self._device_info[CONF_FRAMERATE] = 2
        self._device_info[CONF_CONTENT_TYPE] = CONF_CONTENT_TYPE
        self._device_info[CONF_VERIFY_SSL] = True
        self._device_info[CONF_NAME] = lorex_coord.data[LOREX_MODEL]
        super().__init__(
            hass, self._device_info, lorex_coord.data[LOREX_ID], "doorbell"
        )

        self._coordinator = lorex_coord
        self._attr_unique_id = self._coordinator.data[LOREX_ID] + "_camera"
        self._attr_brand = "Lorex"
        self._attr_model = self._coordinator.data[LOREX_MODEL]

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._coordinator.data[LOREX_ID])},
            manufacturer="Lorex",
        )
        _LOGGER.info(
            "Lorex doorbell RTSP url: %s", self._device_info[CONF_STREAM_SOURCE]
        )
