"""Config flow for Lorex integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, LOREX_CLIENT, LOREX_CONNECTION, LOREX_ID, LorexType
from .lorex_doorbell_client import LorexDoorbellClient
from .lorex_utils import determine_type

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional("name", default="Lorex Doorbell"): str,
        vol.Required("host"): str,
        vol.Required("username", default="admin"): str,
        vol.Required("password"): str,
    }
)


msg = {}


def message_received(message: dict[str, Any]):
    """Handle callback for connection from doorbell."""
    global msg  # noqa: PLW0602
    msg = message.copy()
    if message[LOREX_CONNECTION] and len(message[LOREX_ID]):
        if LOREX_CLIENT in message:
            message[LOREX_CLIENT].close_connection()


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )
    global msg  # noqa: PLW0602

    tp: LorexType = determine_type(data["host"])

    if tp == LorexType.DOORBELL:
        cd = {}
        cd["username"] = data["username"]
        cd["password"] = data["password"]
        cd["port"] = 5000
        cd["host"] = data["host"]
        cd["on_event"] = message_received

        loop = asyncio.get_running_loop()
        on_con_lost = loop.create_future()
        transport, protolcol = await loop.create_connection(
            lambda: LorexDoorbellClient(cd, on_con_lost), data["host"], 5000
        )

        try:
            await on_con_lost
        finally:
            transport.close()

        if len(msg[LOREX_ID]) and msg[LOREX_CONNECTION]:
            return {"title": vol.name, "uuid": msg[LOREX_ID]}

        return {"title": "", "uuid": ""}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lorex."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            user_input["uuid"] = info["uuid"]
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
