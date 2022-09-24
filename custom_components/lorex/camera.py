"""
Support for doorbell Cameras  uses RTSP only

"""
import logging
from typing import Dict, Any
from contextlib import closing

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform

from homeassistant.components.generic.camera import (
    GenericCamera,
    CONF_LIMIT_REFETCH_TO_URL_CHANGE,
    CONF_FRAMERATE,
    CONF_CONTENT_TYPE,
    DEFAULT_CONTENT_TYPE,
    CONF_VERIFY_SSL,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN
from .__init__ import LorexDevice, CONF_STREAM_SOURCE

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup camera platform."""
    lorex_device: LorexDevice = hass.data[DOMAIN][entry.entry_id]

    if lorex_device:
        async_add_entities([LorexCamera(hass, entry, lorex_device)])


class LorexCamera(GenericCamera):
    """LorexCamera, a generic camera with rtsp url"""

    _device_info: Dict[str, Any]

    def __init__(self, hass, entry, lorex_device: LorexDevice):
        """Initialize a camera from Lorex_device."""
        _LOGGER.debug("Initializing the lorex camera")
        self._device = lorex_device
        self._attr_unique_id = self._device.get_serial_number() + "_camera"
        name = self._device.get_device_type() + "_camera"
        self._attr_name = f"{0} {1}".format(entry.title, name)
        self._device_info = lorex_device.camera_device_info()
        _LOGGER.debug(f"lorex camera url: {self._device_info[CONF_STREAM_SOURCE]}")
        self._device_info[CONF_LIMIT_REFETCH_TO_URL_CHANGE] = False
        self._device_info[CONF_FRAMERATE] = 2
        self._device_info[CONF_CONTENT_TYPE] = DEFAULT_CONTENT_TYPE
        self._device_info[CONF_VERIFY_SSL] = True
        super().__init__(hass, self._device_info, self._attr_unique_id, "Lorex Camera")
