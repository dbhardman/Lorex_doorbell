"""Config flow for Lorex integration."""

from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, LOREX_CLIENT, LOREX_CONNECTION, LOREX_ID
from .lorex_doorbell_client import LorexDoorbellClient

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

    # callback required for closing the connection once established
    def message_received(message: dict[str, Any]):
        """Handle callback for connection from doorbell."""
        global msg  # noqa: PLW0602
        msg = message.copy()
        _LOGGER.debug(f"Lorex connection msg {message}")
        if message[LOREX_CONNECTION] and len(message[LOREX_ID]):
            if LOREX_CLIENT in message:
                message[LOREX_CLIENT].close_connection()
            else:
                _LOGGER.info("Lorex validation message incorrect")

    # doorbell listens on port 5000 so connect
    # so test and give invalid host if not listeneing on that port

    sock = socket.socket()

    try:
        sock.connect((data["host"], 5000))
    except Exception as ex:
        _LOGGER.info(f"Lorex doorbell = Invalid host@ {data['host']}")
        raise InvalidHost
    finally:
        sock.close()

    _LOGGER.info("Lorex doorbell = Valid host")

    cd = {}
    cd["username"] = data["username"]
    cd["password"] = data["password"]
    cd["port"] = 5000
    cd["host"] = data["host"]
    cd["on_event"] = message_received

    loop = asyncio.get_running_loop()
    on_con_lost = loop.create_future()

    try:
        transport, protolcol = await loop.create_connection(
            lambda: LorexDoorbellClient(cd, on_con_lost), data["host"], 5000
        )
    except:
        raise InvalidAuth

    try:
        await on_con_lost
    finally:
        transport.close()

    # if msg["lorex_Connection"] == False:
    #    raise InvalidAuth
    return msg


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
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidHost:
                errors["base"] = "invalid_host"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                if info is not None:
                    user_input["uuid"] = info[LOREX_ID]
                    await self.async_set_unique_id(info[LOREX_ID])
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=user_input["name"], data=user_input
                    )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidHost(HomeAssistantError):
    """Error to indicate the host is not a doorbell."""
