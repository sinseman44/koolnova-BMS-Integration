""" Initialisation du package de l'intégration TestVBE_4 """

import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .koolnova.device import Koolnova

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, 
                            entry: ConfigEntry) -> bool: # pylint: disable=unused-argument
    """ Creation des entités à partir d'une configEntry """

    hass.data.setdefault(DOMAIN, [])
    
    name: str = entry.data['Name']
    port: str = entry.data['Device']
    addr: int = entry.data['Address']
    baudrate: int = entry.data['Baudrate']
    parity: str = entry.data['Parity'][0]
    bytesize: int = entry.data['Sizebyte']
    stopbits: int = entry.data['Stopbits']
    timeout: int = entry.data['Timeout']
    
    _LOGGER.debug("Appel de async_setup_entry - entry: entry_id={}, data={}".format(entry.entry_id, entry.data))
    try:
        device = Koolnova(name, port, addr, baudrate, parity, bytesize, stopbits, timeout)
        # connect to modbus client
        await device.connect()
        # update attributes
        await device.update()
        # record each area in device
        _LOGGER.debug("Koolnova areas: {}".format(entry.data['areas']))
        for area in entry.data['areas']:
            await device.add_manual_registered_zone(name=area['Name'], 
                                                    id_zone=area['Zone_id'])
        _LOGGER.debug("Koolnova device: {}".format(device))
        hass.data[DOMAIN].append(device)
    except Exception as e:
        _LOGGER.exception("Something went wrong ... {}".format(e))

    # Propagation du configEntry à toutes les plateformes déclarées dans notre intégration
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """ Handle removal of an entry """
    _LOGGER.debug("Appel de async_remove_entry - entry: {}".format(entry))