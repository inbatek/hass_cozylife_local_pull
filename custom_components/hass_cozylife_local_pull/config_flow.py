"""Config flow for CozyLife Local integration."""
from __future__ import annotations

import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

import logging

_LOGGER = logging.getLogger(__name__)


class CozyLifeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CozyLife Local."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - UI configuration."""
        errors = {}

        if user_input is not None:
            # Validate IP address
            ip = user_input.get("ip", "").strip()
            alias = user_input.get("alias", "").strip()

            if not ip:
                errors["ip"] = "ip_required"
            else:
                # Check if there's already an entry for this IP
                for entry in self._async_current_entries():
                    if entry.data.get("ip") == ip:
                        errors["ip"] = "already_configured"
                        break

                if not errors:
                    # Create a unique ID based on IP for now (will be updated to device_id later)
                    await self.async_set_unique_id(f"cozylife_{ip}")
                    self._abort_if_unique_id_configured()

                    # Create config entry
                    return self.async_create_entry(
                        title=alias if alias else ip,
                        data={
                            "ip": ip,
                            "alias": alias,
                        },
                    )

        # Show form
        data_schema = vol.Schema(
            {
                vol.Required("ip"): str,
                vol.Optional("alias"): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        """Handle import from YAML configuration."""
        _LOGGER.info(f"Importing YAML config for device: {import_data}")

        # For devices list format
        if "serial_number" in import_data:
            device_id = import_data["serial_number"]
            ip = import_data["ip"]
            alias = import_data.get("alias", ip)

            # Check if there's already an entry for this IP (with any unique_id)
            for entry in self._async_current_entries():
                if entry.data.get("ip") == ip:
                    _LOGGER.info(f"Updating existing entry for {ip} with device_id {device_id}")
                    # Update existing entry with new unique_id and data
                    self.hass.config_entries.async_update_entry(
                        entry,
                        unique_id=device_id,
                        data={
                            "ip": ip,
                            "alias": alias,
                            "serial_number": device_id,
                        },
                    )
                    return self.async_abort(reason="already_configured")

            # Set unique ID to device serial number
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=alias,
                data={
                    "ip": ip,
                    "alias": alias,
                    "serial_number": device_id,
                },
            )

        # For legacy IP list format
        elif "ip" in import_data:
            ip = import_data["ip"]

            # Check if there's already an entry for this IP
            for entry in self._async_current_entries():
                if entry.data.get("ip") == ip:
                    _LOGGER.info(f"Entry for {ip} already exists, skipping import")
                    return self.async_abort(reason="already_configured")

            # Use IP as unique ID for legacy format
            await self.async_set_unique_id(f"cozylife_{ip}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=ip,
                data={
                    "ip": ip,
                    "alias": None,
                },
            )

        _LOGGER.error(f"Invalid import data: {import_data}")
        return self.async_abort(reason="invalid_import")
