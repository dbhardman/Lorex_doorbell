"""
Support for three binary sensors
Motion sensor
Doorbell button pressed sensor
Smart human motion detection
"""

import logging
from typing import Dict, Any
from contextlib import closing

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.components.binary_sensor import BinarySensorEntity
from .__init__ import LorexDevice, CONF_STREAM_SOURCE

_LOGGER: logging.Logger = logging.getLogger(__package__)


from .const import MOTION_SENSOR_DEVICE_CLASS, DOMAIN, DOORBELL_DEVICE_CLASS

#This service handles resetting the motion counter
SERVICE_RESET_MOTION_COUNTER = "reset_motion_counter"
#This service handles reseting the doorbell button press counter
SERVICE_RESET_PRESS_COUNTER = "reset_press_counter"
#This service is for the smart human motion detection
SERVICE_RESET_HUMAN_COUNTER = "reset_human_counter"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup camera platform."""
    lorex_device: LorexDevice = hass.data[DOMAIN][entry.entry_id]

    if lorex_device:
        async_add_entities(
            [
                LorexMotion(hass, entry, lorex_device),
                LorexPressed(hass, entry, lorex_device),
                LorexHumanMotion(hass, entry, lorex_device),
            ]
        )
    # add service calls for resetting counters
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_RESET_MOTION_COUNTER,
        {},
        "async_reset_motion_counter"
    )
    platform.async_register_entity_service(
        SERVICE_RESET_PRESS_COUNTER,
        {},
        "async_reset_pressed_counter"
    )
    platform.async_register_entity_service(
        SERVICE_RESET_HUMAN_COUNTER,
        {},
        "async_reset_human_counter"
    )




class LorexMotion(BinarySensorEntity):
    """ Class for Doorbell motion sensor
        based on binary_sensor"""

    def __init__(self, hass, entry, lorex_device: LorexDevice):
        self._eventName = "VideoMotion"
        self._device = lorex_device
        self._attr_device_class = MOTION_SENSOR_DEVICE_CLASS
        self._attr_unique_id = self._device.get_serial_number() + "_motion"
        name = f"{DOMAIN}_{MOTION_SENSOR_DEVICE_CLASS}"
        #_LOGGER.info(f"Lorex Motion prefix: {name}")
        self._attr_name = name #"lorex_motion"
        #_LOGGER.info(f"Lorex Motion name: {self._attr_name}")
        self._attr_state = "off"
        self._attr_is_on = False
        self._attributes = {}
        self._attributes["counter"] = 0


    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications.
           This in addition to is_on down below allow the sensor to update
           when async_write_ha_state is called by parent it checks is_on """
        self._device.add_event_listener(self._eventName, self.async_write_ha_state)

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.  False if entity pushes its state to HA"""
        return False

    @property
    def device_class(self):
        """Return the class of this binary_sensor, Example: motion"""
        return self._attr_device_class

    @property
    def is_on(self):
        onOff = self._device.get_motion()
        if onOff:
            self._attributes["counter"] = self._attributes["counter"] + 1
        return onOff

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_reset_motion_counter(self):
        """Handles the service call for SERVICE_RESET_MOTION_COUNTER"""
        self._attributes["counter"] = 0
        self.async_write_ha_state()


            


class LorexPressed(BinarySensorEntity):
    """Class for tracking doorbell button presses
        based on binary sensor"""
    def __init__(self, hass, entry, lorex_device: LorexDevice):
        self._eventName = "AlarmLocal"
        self._attr_device_class = DOORBELL_DEVICE_CLASS
        self._device = lorex_device
        self._attr_unique_id = self._device.get_serial_number() + "_pressed"
        name = f"{DOMAIN}_{DOORBELL_DEVICE_CLASS}"
        self._attr_name = name
        self._attr_state = "off"
        self._attr_is_on = False
        self._attributes = {}
        self._attributes["counter"] = 0

    # Attach a listener to the Lorex device.
    # async_write_ha_state calls is_on to update the entitiy state
    # Lorex device sets get_pressed state based on messages from the device
    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self._device.add_event_listener(self._eventName, self.async_write_ha_state)

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.  False if entity pushes its state to HA"""
        return False

    @property
    def is_on(self):
        onOff = self._device.get_pressed()
        if onOff:
            self._attributes["counter"] = self._attributes["counter"] + 1
        return onOff

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_reset_pressed_counter(self):
        """Handles the SERVICE_RESET_PRESS_COUNTER service call"""
        self._attributes["counter"]  = 0
        self.async_write_ha_state()


class LorexHumanMotion(BinarySensorEntity):
    """Setup the doorbell smart human motion sensor"""

    def __init__(self, hass, entry, lorex_device: LorexDevice):
        self._eventName = "IntelliFrame"
        self._device = lorex_device
        self._attr_device_class = MOTION_SENSOR_DEVICE_CLASS
        self._attr_unique_id = self._device.get_serial_number() + "_human_motion"
        name = f"{DOMAIN}_human_{MOTION_SENSOR_DEVICE_CLASS}"
        #_LOGGER.info(f"Lorex Human Motion prefix: {name}")
        self._attr_name = name #"lorex_motion"
        #_LOGGER.info(f"Lorex Motion name: {self._attr_name}")
        self._attr_state = "off"
        self._attr_is_on = False
        self._attributes = {}
        self._attributes["counter"] = 0

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications.
           This in addition to is_on down below allow the sensor to update
           when async_write_ha_state is called by parent it checks is_on """
        self._device.add_event_listener(self._eventName, self.async_write_ha_state)

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.  False if entity pushes its state to HA"""
        return False

    @property
    def device_class(self):
        """Return the class of this binary_sensor, Example: motion"""
        return self._attr_device_class

    @property
    def is_on(self):
        onOff = self._device.get_human_motion()
        if onOff:
            self._attributes["counter"] = self._attributes["counter"] + 1
        return onOff

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_reset_human_counter(self):
        """Handles the service call for SERVICE_RESET_HUMAN_COUNTER"""
        self._attributes["counter"] = 0
        self.async_write_ha_state()


