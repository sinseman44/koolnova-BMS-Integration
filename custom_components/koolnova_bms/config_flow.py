"""Config flow Koolnova"""
from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4
from functools import partial

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components import zeroconf
from homeassistant import config_entries, exceptions
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_NAME,
    CONF_BASE,
    CONF_DEVICE_ID,
    CONF_FORCE_UPDATE,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

#from .const import CONF_OPERATOR_ID, CONF_AIRCO_ID, DOMAIN
#from .wfrac.repository import Repository

_LOGGER = logging.getLogger(__name__)

class KoolnovaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL
    DOMAIN = DOMAIN

    async def async_step_user(self, user_input=None):
        """Handle adding device manually."""

        field = partial(self._field, user_input)
        data_schema = vol.Schema({
            field(CONF_NAME, vol.Required, "Airco unknown") : cv.string,
            field(CONF_HOST, vol.Required) : cv.string,
            field(CONF_PORT, vol.Optional, 51443): cv.port,
            field(CONF_FORCE_UPDATE, vol.Optional, False): cv.boolean,
        })

        return await self._async_create_common(
            step_id="user",
            data_schema=data_schema,
            user_input=user_input
        )

    @property
    def _name(self) -> str | None:
        return self.context.get(CONF_NAME)

# pylint: disable=too-few-public-methods

class KnownError(exceptions.HomeAssistantError):
    """Base class for errors known to this config flow.

    [error_name] is the value passed to [errors] in async_show_form, which should match a key
    under "errors" in strings.json

    [applies_to_field] is the name of the field name that contains the error (for
    async_show_form); if the field doesn't exist in the form CONF_BASE will be used instead.
    """
    error_name = "unknown_error"
    applies_to_field = CONF_BASE

    def __init__(self, *args: object, **kwargs: dict[str, str]) -> None:
        super().__init__(*args)
        self._extra_info = kwargs

    def get_errors_and_placeholders(self, schema):
        """Return dicts of errors and description_placeholders, for adding to async_show_form"""
        key = self.applies_to_field
        # Errors will only be displayed to the user if the key is actually in the form (or
        # CONF_BASE for a general error), so we'll check the schema (seems weird there
        # isn't a more efficient way to do this...)
        if key not in {k.schema for k in schema}:
            key = CONF_BASE
        return ({key : self.error_name}, self._extra_info or {})

class CannotConnect(KnownError):
    """Error to indicate we cannot connect."""
    error_name = "cannot_connect"

class InvalidHost(KnownError):
    """Error to indicate there is an invalid hostname."""
    error_name = "cannot_connect"
    applies_to_field = CONF_HOST

class HostAlreadyConfigured(KnownError):
    """Error to indicate there is an duplicate hostname."""
    error_name = "host_already_configured"
    applies_to_field = CONF_HOST

class InvalidName(KnownError):
    """Error to indicate there is an invalid hostname."""
    error_name = "name_invalid"
    applies_to_field = CONF_NAME

class TooManyDevicesRegistered(KnownError):
    """Error to indicate that there are too many devices registered"""
    error_name = "too_many_devices_registered"
    applies_to_field = CONF_BASE
