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
from .const import (
    ALARMLOCAL,
    CONF_NAME,
    DOMAIN,
    LOREX_CONNECTION,
    LOREX_ID,
    LOREX_IDLE,
    LOREX_PRESSED,
)


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
                LorexPressed(entry, lorex_device),
            ]
        )


_LOGGER: logging.Logger = logging.getLogger(__package__)


class LorexPressed(EventEntity):
    """Doorbell button events."""

    def __init__(self, entry: ConfigEntry, lorex: LorexCoordinator) -> None:
        """LorexPressed."""
        super().__init__()
        self._attr_name = entry.data[CONF_NAME]
        self._attr_unique_id = lorex.data[LOREX_ID] + "_event"
        self._coordinator = lorex
        self._attr_device_class = EventDeviceClass.DOORBELL
        self._attr_event_types = [LOREX_IDLE, LOREX_PRESSED]
        self.last_event = LOREX_IDLE
        self.updates_enabled = True
        self._trigger_event(
            LOREX_IDLE,
            {"extra_data": f"updates_enabled = {self.updates_enabled}"},
        )

    @callback
    def _async_handle_event(self) -> None:
        """Handle the demo button event."""
        _LOGGER.debug("Button event: %s", self._coordinator.data[ALARMLOCAL])

        if self._coordinator.data[ALARMLOCAL]:
            if self.last_event == LOREX_IDLE:
                self._trigger_event(
                    LOREX_PRESSED,
                    {"extra_data": f"updates_enabled = {self.updates_enabled}"},
                )
                self.last_event = LOREX_PRESSED
        elif self.last_event == LOREX_PRESSED:
            self._trigger_event(
                LOREX_IDLE,
                {"extra_data": f"updates_enabled = {self.updates_enabled}"},
            )
            self.last_event = LOREX_IDLE
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register callbacks with data coordinator."""
        self._coordinator.add_callback(self._async_handle_event)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        self._coordinator.remove_callback(self._async_handle_event)

    @property
    def available(self) -> bool:
        """Return connection state of the doorbell."""
        return self._coordinator.data[LOREX_CONNECTION]
