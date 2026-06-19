""" Initialisation du package de l'intégration Koolnova """

import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady

from .koolnova.device import Koolnova

from .const import DOMAIN, PLATFORMS

from .coordinator import KoolnovaCoordinator

_LOGGER = logging.getLogger(__name__)

def _build_device_from_entry(entry: ConfigEntry) -> Koolnova:
    """Build a Koolnova runtime device from a config entry."""
    debug: bool = entry.data['Debug']
    timeout: int = entry.data['Timeout']
    name: str = entry.data['Name']
    table_version: str | None = entry.data.get("Table_version")
    mode: str = entry.data['Mode']

    if mode == 'Modbus RTU':
        return Koolnova(mode=mode,
                        name=name,
                        timeout=timeout,
                        debug=debug,
                        port=entry.data['Device'],
                        addr=entry.data['Address'],
                        baudrate=entry.data['Baudrate'],
                        parity=entry.data['Parity'][0],
                        bytesize=entry.data['Sizebyte'],
                        stopbits=entry.data['Stopbits'],
                        table_version=table_version)
    if mode == 'Modbus TCP':
        return Koolnova(mode=mode,
                        name=name,
                        timeout=timeout,
                        debug=debug,
                        port=entry.data['Port'],
                        addr=entry.data['Address'],
                        modbus=entry.data['Modbus'],
                        retries=entry.data['Retries'],
                        reco_delay_min=entry.data['Reconnect_delay_min'],
                        reco_delay_max=entry.data['Reconnect_delay_max'],
                        table_version=table_version)

    raise ConfigEntryNotReady(f"Unsupported Koolnova Modbus mode: {mode}")

def _disconnect_device(device: Koolnova | None) -> None:
    """Disconnect a Koolnova device if it has an active Modbus client."""
    if device and device.connected():
        device.disconnect()

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
