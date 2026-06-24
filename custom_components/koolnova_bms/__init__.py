""" Initialisation du package de l'intégration Koolnova """

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .koolnova.device import Koolnova

from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_FIELD_ANGLE,
    SERVICE_FIELD_ENTRY_ID,
    SERVICE_FIELD_ZONE_ID,
    SERVICE_GET_V2_LAST_OPENING_ANGLE,
    SERVICE_SET_V2_OPENING_ANGLE,
)

from .coordinator import KoolnovaCoordinator

_LOGGER = logging.getLogger(__name__)

SET_V2_OPENING_ANGLE_SCHEMA = vol.Schema({
    vol.Optional(SERVICE_FIELD_ENTRY_ID): cv.string,
    vol.Required(SERVICE_FIELD_ZONE_ID): vol.All(
        vol.Coerce(int),
        vol.Range(min=1, max=16),
    ),
    vol.Required(SERVICE_FIELD_ANGLE): vol.All(
        vol.Coerce(int),
        vol.In([45, 60, 75, 90]),
    ),
})

GET_V2_LAST_OPENING_ANGLE_SCHEMA = vol.Schema({
    vol.Optional(SERVICE_FIELD_ENTRY_ID): cv.string,
    vol.Optional(SERVICE_FIELD_ZONE_ID): vol.All(
        vol.Coerce(int),
        vol.Range(min=1, max=16),
    ),
})

ANGLE_BY_CODE = {
    0x00: 45,
    0x01: 60,
    0x02: 75,
    0x03: 90,
}

def _build_device_from_entry(entry: ConfigEntry) -> Koolnova:
    """Build a Koolnova runtime device from a config entry."""
    config = {**entry.data, **entry.options}
    debug: bool = config['Debug']
    timeout: int = config['Timeout']
    name: str = config['Name']
    table_version: str | None = config.get("Table_version")
    mode: str = config['Mode']

    if mode == 'Modbus RTU':
        return Koolnova(mode=mode,
                        name=name,
                        timeout=timeout,
                        debug=debug,
                        port=config['Device'],
                        addr=config['Address'],
                        baudrate=config['Baudrate'],
                        parity=config['Parity'][0],
                        bytesize=config['Sizebyte'],
                        stopbits=config['Stopbits'],
                        table_version=table_version)
    if mode == 'Modbus TCP':
        return Koolnova(mode=mode,
                        name=name,
                        timeout=timeout,
                        debug=debug,
                        port=config['Port'],
                        addr=config['Address'],
                        modbus=config['Modbus'],
                        retries=config['Retries'],
                        reco_delay_min=config['Reconnect_delay_min'],
                        reco_delay_max=config['Reconnect_delay_max'],
                        table_version=table_version)

    raise ConfigEntryNotReady(f"Unsupported Koolnova Modbus mode: {mode}")

def _disconnect_device(device: Koolnova | None) -> None:
    """Disconnect a Koolnova device if it has an active Modbus client."""
    if device and device.connected():
        device.disconnect()

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)

def _runtime_data_for_v2_service(hass: HomeAssistant,
                                 entry_id: str | None,
                                 ) -> dict:
    """Return runtime data for a v2 service call."""
    runtime_entries = hass.data.get(DOMAIN, {})
    if entry_id:
        runtime_data = runtime_entries.get(entry_id)
        if runtime_data is None:
            raise HomeAssistantError(
                f"Koolnova config entry {entry_id} is not loaded"
            )
    else:
        v2_entries = [
            runtime_data
            for runtime_data in runtime_entries.values()
            if runtime_data["device"].table_version == "v2"
        ]
        if len(v2_entries) != 1:
            raise HomeAssistantError(
                "Provide entry_id when zero or multiple Koolnova v2 entries are loaded"
            )
        runtime_data = v2_entries[0]

    if runtime_data["device"].table_version != "v2":
        raise HomeAssistantError("Koolnova v2 opening-angle services require a Koolnova v2 entry")
    return runtime_data

def _v2_last_opening_angle_payload(register_name: str,
                                   register_address: int,
                                   value: dict,
                                   ) -> dict:
    """Return a service response payload for one opening-angle register."""
    angle_code = value.get("angle_code")
    return {
        "register": register_address,
        "register_name": register_name,
        "raw": value.get("raw"),
        "target_zone_id": value.get("zone_id"),
        "target_zone_index": value.get("zone_index"),
        "angle": ANGLE_BY_CODE.get(angle_code),
        "angle_code": angle_code,
    }

def _async_setup_services(hass: HomeAssistant) -> None:
    """Register integration-level services once."""

    async def async_set_v2_opening_angle(call) -> None:
        """Set one Koolnova v2 opening-angle command register."""
        runtime_data = _runtime_data_for_v2_service(
            hass,
            call.data.get(SERVICE_FIELD_ENTRY_ID),
        )
        device = runtime_data["device"]
        coordinator = runtime_data["coordinator"]
        zone_id = call.data[SERVICE_FIELD_ZONE_ID]
        zone_index = zone_id - 1
        angle_code = {
            45: 0x00,
            60: 0x01,
            75: 0x02,
            90: 0x03,
        }[call.data[SERVICE_FIELD_ANGLE]]

        if zone_index < 8:
            await device.async_set_v2_opening_angle_z1_z8(angle_code, zone_index)
        else:
            await device.async_set_v2_opening_angle_z9_z16(angle_code, zone_index)
        await coordinator.async_request_refresh()

    async def async_get_v2_last_opening_angle(call) -> dict:
        """Return the last targeted v2 opening-angle command register values."""
        runtime_data = _runtime_data_for_v2_service(
            hass,
            call.data.get(SERVICE_FIELD_ENTRY_ID),
        )
        coordinator = runtime_data["coordinator"]
        await coordinator.async_request_refresh()
        data = coordinator.data or {}
        v2_registers = data.get(
            "v2_registers",
            runtime_data["device"].v2_registers,
        )

        z1_z8 = _v2_last_opening_angle_payload(
            "z1_z8",
            40080,
            v2_registers.get("40080_opening_angle_z1_z8", {}),
        )
        z9_z16 = _v2_last_opening_angle_payload(
            "z9_z16",
            40081,
            v2_registers.get("40081_opening_angle_z9_z16", {}),
        )
        response = {
            "z1_z8": z1_z8,
            "z9_z16": z9_z16,
        }

        zone_id = call.data.get(SERVICE_FIELD_ZONE_ID)
        if zone_id is not None:
            selected = z1_z8 if zone_id <= 8 else z9_z16
            response["requested_zone_id"] = zone_id
            response["requested_zone_last_command"] = selected
            response["requested_zone_is_current_target"] = (
                selected.get("target_zone_id") == zone_id
            )
        return response

    if not hass.services.has_service(DOMAIN, SERVICE_SET_V2_OPENING_ANGLE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_V2_OPENING_ANGLE,
            async_set_v2_opening_angle,
            schema=SET_V2_OPENING_ANGLE_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_GET_V2_LAST_OPENING_ANGLE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_V2_LAST_OPENING_ANGLE,
            async_get_v2_last_opening_angle,
            schema=GET_V2_LAST_OPENING_ANGLE_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

async def async_setup_entry(hass: HomeAssistant, 
                            entry: ConfigEntry) -> bool: # pylint: disable=unused-argument
    """ Creation des entités à partir d'une configEntry """

    hass.data.setdefault(DOMAIN, {})
    device: Koolnova | None = None
    try:
        device = _build_device_from_entry(entry)
        # connect to modbus client
        ret = await device.async_connect()
        if not ret:
            raise ConfigEntryNotReady("Unable to connect to Koolnova Modbus client")
        # update attributes
        ret = await device.async_update()
        if not ret:
            raise ConfigEntryNotReady("Unable to retrieve initial Koolnova data")
        # record each area in device
        _LOGGER.debug("Koolnova areas: %s", entry.data['areas'])
        for area in entry.data['areas']:
            ret = await device.async_add_manual_registered_area(name=area['Name'],
                                                    id_zone=area['Area_id'])
            if not ret:
                raise ConfigEntryNotReady(
                    f"Unable to register Koolnova area {area['Area_id']}"
                )
        coordinator = KoolnovaCoordinator(hass, device)
        # Ensure coordinator.data is populated before platform entities are created.
        await coordinator.async_config_entry_first_refresh()
        hass.data[DOMAIN][entry.entry_id] = {
            "device": device,
            "coordinator": coordinator,
        }
    except ConfigEntryNotReady:
        _disconnect_device(device)
        raise
    except Exception as e:
        _disconnect_device(device)
        raise ConfigEntryNotReady(
            f"Unexpected error while setting up Koolnova integration: {e}"
        ) from e

    # Propagation du configEntry à toutes les plateformes déclarées dans notre intégration
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _disconnect_device(device)
        raise

    _async_setup_services(hass)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant,
                            entry: ConfigEntry) -> bool:
    """ Unload a config entry. """
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        runtime_data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if runtime_data:
            _disconnect_device(runtime_data["device"])
        if not hass.data.get(DOMAIN):
            hass.services.async_remove(DOMAIN, SERVICE_SET_V2_OPENING_ANGLE)
            hass.services.async_remove(DOMAIN, SERVICE_GET_V2_LAST_OPENING_ANGLE)
    _LOGGER.debug("Unload entries: {}".format(unload_ok))
    return unload_ok

async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """ Handle removal of an entry """
    _LOGGER.debug("Remove entry")
    if DOMAIN in hass.data:
        runtime_data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if not runtime_data:
            return
        _disconnect_device(runtime_data["device"])
