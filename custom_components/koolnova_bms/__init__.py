""" Initialisation du package de l'intégration Koolnova """

import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady

from .koolnova.device import Koolnova

from .const import DOMAIN, PLATFORMS

from .coordinator import KoolnovaCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, 
                            entry: ConfigEntry) -> bool: # pylint: disable=unused-argument
    """ Creation des entités à partir d'une configEntry """

    hass.data.setdefault(DOMAIN, {})
    device:Koolnova = None
    debug:bool = entry.data['Debug']
    timeout:int = entry.data['Timeout']
    name: str = entry.data['Name']
    if entry.data['Mode'] == 'Modbus RTU':
        port: str = entry.data['Device']
        addr: int = entry.data['Address']
        baudrate: int = entry.data['Baudrate']
        parity: str = entry.data['Parity'][0]
        bytesize: int = entry.data['Sizebyte']
        stopbits: int = entry.data['Stopbits']
        device = Koolnova(mode=entry.data['Mode'],
                            name=name,
                            timeout=timeout,
                            debug=debug,
                            port=port,
                            addr=addr,
                            baudrate=baudrate,
                            parity=parity,
                            bytesize=bytesize,
                            stopbits=stopbits)
    elif entry.data['Mode'] == 'Modbus TCP':
        port:int = entry.data['Port']
        addr:str = entry.data['Address']
        modbus:int = entry.data['Modbus']
        retries:int = entry.data['Retries']
        reco_delay_min:float = entry.data['Reconnect_delay_min']
        reco_delay_max:float = entry.data['Reconnect_delay_max']
        device = Koolnova(mode=entry.data['Mode'],
                            name=name,
                            timeout=timeout,
                            debug=debug,
                            port=port,
                            addr=addr,
                            modbus=modbus,
                            retries=retries,
                            reco_delay_min=reco_delay_min,
                            reco_delay_max=reco_delay_max)
    else:
        _LOGGER.error("Integration initialisation failed (Mode unknown)")
        return False
    try:
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
        hass.data[DOMAIN][entry.entry_id] = {
            "device": device,
            "coordinator": coordinator,
        }
    except ConfigEntryNotReady:
        if device and device.connected():
            device.disconnect()
        raise
    except Exception as e:
        if device and device.connected():
            device.disconnect()
        raise ConfigEntryNotReady(
            f"Unexpected error while setting up Koolnova integration: {e}"
        ) from e

    # Propagation du configEntry à toutes les plateformes déclarées dans notre intégration
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

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
            device = runtime_data["device"]
            if device.connected():
                device.disconnect()
    _LOGGER.debug("Unload entries: {}".format(unload_ok))
    return unload_ok

async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """ Handle removal of an entry """
    _LOGGER.debug("Remove entry")
    if DOMAIN in hass.data:
        runtime_data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if not runtime_data:
            return
        device = runtime_data["device"]
        if device.connected():
            device.disconnect()
