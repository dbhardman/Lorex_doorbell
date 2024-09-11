"""Lorex event.

respond to doorbell button evvents
"""

import logging

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .__init__ import LorexCoordinator
from .const import ALARMLOCAL, DOMAIN, LOREX_ID, LOREX_MODEL

# This service handles reseting the doorbell button press counter
SERVICE_RESET_EVENT_COUNTER = "reset_event_counter"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Doorbell button event entity."""
    lorex_device: LorexCoordinator = hass.data[DOMAIN][entry.entry_id]

    if lorex_device:
        async_add_entities(
            [
                LorexPressed(lorex_device),
            ]
        )
    # add service calls for resetting counters
    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_RESET_EVENT_COUNTER, {}, "async_reset_event_counter"
    )


_LOGGER: logging.Logger = logging.getLogger(__package__)


class LorexPressed(EventEntity):
    """Doorbell button events."""

    def __init__(self, lorex: LorexCoordinator) -> None:
        """LorexPressed."""
        self._attr_name = lorex.data[LOREX_MODEL] + "_event"
        self._attr_unique_id = lorex.data[LOREX_ID] + "_event"
        self.counter = 0
        self._coordinator = lorex
        self._attr_device_class = EventDeviceClass.DOORBELL
        self._attr_event_types = ["press", "idle"]

    @callback
    def _async_handle_event(self) -> None:
        """Handle the demo button event."""
        _LOGGER.debug("Button event: %s", self._coordinator.data[ALARMLOCAL])
        if self._coordinator.data[ALARMLOCAL]:
            self.counter += 1
            self._trigger_event(
                self._attr_event_types[0],
                {"extra_data": self._coordinator.data[LOREX_ID]},
            )
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register callbacks with data coordinator."""
        self._coordinator.add_callback(
            self._coordinator.data[LOREX_ID], self._async_handle_event
        )

    async def async_reset_event_counter(self):
        """Handle the SERVICE_RESET_PRESS_COUNTER service call."""
        self.counter = 0
        self.schedule_update_ha_state()
