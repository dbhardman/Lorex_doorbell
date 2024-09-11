"""Binary sensors.

Motion sensor
Doorbell button pressed sensor
Smart human motion detection
"""

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .__init__ import LorexCoordinator
from .const import DOMAIN, INTELLIFRAME, LOREX_ID, LOREX_MODEL, VIDEOMOTION

# This service handles resetting the motion counter
SERVICE_RESET_MOTION_COUNTER = "reset_motion_counter"
# This service is for the smart human motion detection
SERVICE_RESET_HUMAN_COUNTER = "reset_human_counter"

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Motion sensor setup."""
    lorex_coord: LorexCoordinator = hass.data[DOMAIN][entry.entry_id]

    if lorex_coord:
        async_add_entities(
            [
                LorexMotion(lorex_coord),
                LorexHumanMotion(lorex_coord),
            ]
        )
    # add service calls for resetting counters
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_RESET_MOTION_COUNTER, {}, "async_reset_motion_counter"
    )
    platform.async_register_entity_service(
        SERVICE_RESET_HUMAN_COUNTER, {}, "async_reset_human_counter"
    )


class LorexMotion(BinarySensorEntity):
    """Doorbell motion sensor.based on binary_sensor."""

    def __init__(self, lorex_coordinator: LorexCoordinator) -> None:
        """Init."""
        self._attr_should_poll = False
        self._coordinator = lorex_coordinator
        self._attr_device_class = BinarySensorDeviceClass.MOTION
        self._attr_unique_id = self._coordinator.data[LOREX_ID] + "_videomotion"
        tp = self._coordinator.data[LOREX_MODEL]
        if len(tp):
            name = f"{tp}_{self._attr_device_class}"
        else:
            name = f"{DOMAIN}_{self._attr_device_class}"
        self._attr_name = name  # "lorex_motion"
        self._attr_state = "off"
        self._attr_is_on = False
        self._attributes = {}
        self._attributes["counter"] = 0

    async def async_added_to_hass(self):
        """Add call back to data coordinator.

        This in addition to is_on down below allow the sensor to update
        when async_write_ha_state is called by parent it checks is_on
        """
        self._coordinator.add_callback(
            self._coordinator.data[LOREX_ID], self.async_write_ha_state
        )

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.  False if entity pushes its state to HA."""
        return False

    @property
    def device_class(self):
        """Return the class of this binary_sensor, Example: motion."""
        return self._attr_device_class

    @property
    def is_on(self):
        """Proerty to show state of entity."""
        onOff = self._coordinator.data[VIDEOMOTION]
        if onOff:
            self._attributes["counter"] = self._attributes["counter"] + 1
        return onOff

    @property
    def extra_state_attributes(self):
        """Return attributes in this case counter."""
        return self._attributes

    async def async_reset_motion_counter(self):
        """Handle the service call for SERVICE_RESET_MOTION_COUNTER."""
        self._attributes["counter"] = 0
        self.schedule_update_ha_state()

    """
    def async_update(self):
        self.schedule_update_ha_state()
    """


class LorexHumanMotion(BinarySensorEntity):
    """Doorbell smart human motion sensor."""

    def __init__(self, lorex_coordinator: LorexCoordinator) -> None:
        """Init."""
        self._attr_should_poll = False
        self._coordinator = lorex_coordinator
        self._attr_device_class = BinarySensorDeviceClass.MOTION
        self._attr_unique_id = self._coordinator.data[LOREX_ID] + "_human_motion"
        # name = f"{DOMAIN}_human_{MOTION_SENSOR_coordinator_CLASS}"
        tp = self._coordinator.data[LOREX_MODEL]
        if len(tp):
            name = f"{tp}_smart_{self._attr_device_class}"
        else:
            name = f"{DOMAIN}_smart_{self._attr_device_class}"
        self._attr_name = name  # "lorex_motion"
        self._attr_state = "off"
        self._attr_is_on = False
        self._attributes = {}
        self._attributes["counter"] = 0

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications.

        This in addition to is_on down below allow the sensor to update
        when async_write_ha_state is called by parent it checks is_on.
        """
        self._coordinator.add_callback(
            self._coordinator.data[LOREX_ID], self.async_write_ha_state
        )

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.  False if entity pushes its state to HA."""
        return False

    @property
    def device_class(self):
        """Return the class of this binary_sensor, Example: motion."""
        return self._attr_device_class

    @property
    def is_on(self):
        """Proerty to show state of entity."""
        onOff = self._coordinator.data[INTELLIFRAME]
        if onOff:
            self._attributes["counter"] = self._attributes["counter"] + 1
        return onOff

    @property
    def extra_state_attributes(self):
        """Return attributes in this case counter."""
        return self._attributes

    async def async_reset_human_counter(self):
        """Handle the service call for SERVICE_RESET_HUMAN_COUNTER."""
        self._attributes["counter"] = 0
        self.schedule_update_ha_state()

    """
    def async_update(self):
        self.schedule_update_ha_state()
    """
