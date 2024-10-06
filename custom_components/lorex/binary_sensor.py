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
from .const import (
    CONF_NAME,
    DOMAIN,
    INTELLIFRAME,
    LOREX_CONNECTION,
    LOREX_ID,
    VIDEOMOTION,
)

# Will enable the entity to receive device updates
SERVICE_ENABLE_UPDATES = "enable_updates"
# Will disable field device updates to the entity
SERVICE_DISABLE_UPDATES = "disable_updates"

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
                LorexMotion(entry, lorex_coord),
                LorexHumanMotion(entry, lorex_coord),
            ]
        )
    # add service calls for resetting counters
    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_ENABLE_UPDATES, {}, "async_enable_updates"
    )
    platform.async_register_entity_service(
        SERVICE_DISABLE_UPDATES, {}, "async_disable_updates"
    )


class LorexMotion(BinarySensorEntity):
    """Doorbell motion sensor.based on binary_sensor."""

    def __init__(self, entry: ConfigEntry, lorex_coordinator: LorexCoordinator) -> None:
        """Init."""
        self._attr_should_poll = False
        self._coordinator = lorex_coordinator
        self._attr_device_class = BinarySensorDeviceClass.MOTION
        self._attr_unique_id = self._coordinator.data[LOREX_ID] + "_videomotion"
        self._attr_name = entry.data[CONF_NAME] + "_motion"  # name
        self._attr_state = "off"
        # self._attr_is_on = False
        self._attributes = {}
        self._attributes["updates_enabled"] = True

    async def async_added_to_hass(self):
        """Add call back to data coordinator.

        This in addition to is_on down below allow the sensor to update
        when async_write_ha_state is called by parent it checks is_on
        """
        self._coordinator.add_callback(self.async_write_ha_state)
        self._attributes["updates_enabled"] = True

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        self._coordinator.remove_callback(self.async_write_ha_state)
        self._attributes["updates_enabled"] = False

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
        return self._coordinator.data[VIDEOMOTION]

    @property
    def extra_state_attributes(self):
        """Return attributes, in this case the counter."""
        return self._attributes

    @property
    def available(self) -> bool:
        """Return connection state of the doorbell."""
        return self._coordinator.data[LOREX_CONNECTION]

    async def async_enable_updates(self):
        """Handle  SERVICE_ENABLE_UPDATES."""
        if not self._attributes["updates_enabled"]:
            self._coordinator.add_callback(self.async_write_ha_state)
            self._attributes["updates_enabled"] = True
            self.async_write_ha_state()

    async def async_disable_updates(self):
        """Handle SERVICE_ENABLE_UPDATES."""
        if self._attributes["updates_enabled"]:
            self._coordinator.remove_callback(self.async_write_ha_state)
            self._attributes["updates_enabled"] = False
            self.async_write_ha_state()


class LorexHumanMotion(BinarySensorEntity):
    """Doorbell smart human motion sensor."""

    def __init__(self, entry: ConfigEntry, lorex_coordinator: LorexCoordinator) -> None:
        """Init."""
        self._attr_should_poll = False
        self._coordinator = lorex_coordinator
        self._attr_device_class = BinarySensorDeviceClass.MOTION
        self._attr_unique_id = self._coordinator.data[LOREX_ID] + "_human_motion"
        self._attr_name = entry.data[CONF_NAME] + "_smart_motion"  # name
        self._attr_state = "off"
        # self._attr_is_on = False
        self._attributes = {}
        self._attributes["updates_enabled"] = True

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications.

        This in addition to is_on down below allow the sensor to update
        when async_write_ha_state is called by parent it checks is_on.
        """
        self._coordinator.add_callback(self.async_write_ha_state)
        self._attributes["updates_enabled"] = True

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        self._coordinator.remove_callback(self.async_write_ha_state)
        self._attributes["updates_enabled"] = False

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
        """Property to show state of entity."""
        return self._coordinator.data[INTELLIFRAME]

    @property
    def extra_state_attributes(self):
        """Return attributes."""
        return self._attributes
    
    @property
    def available(self) -> bool:
        """Return connection state of the doorbell."""
        return self._coordinator.data[LOREX_CONNECTION]

    async def async_enable_updates(self):
        """Handle  SERVICE_ENABLE_UPDATES."""
        if not self._attributes["updates_enabled"]:
            self._coordinator.add_callback(self.async_write_ha_state)
            self._attributes["updates_enabled"] = True
            self.async_write_ha_state()

    async def async_disable_updates(self):
        """Handle SERVICE_ENABLE_UPDATES."""
        if self._attributes["updates_enabled"]:
            self._coordinator.remove_callback(self.async_write_ha_state)
            self._attributes["updates_enabled"] = False
            self.async_write_ha_state()
