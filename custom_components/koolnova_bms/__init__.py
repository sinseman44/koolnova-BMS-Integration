""" Initialisation du package de l'intégration Koolnova """

import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

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
            _LOGGER.error("Something went wrong when connecting to modbus ...")
            return False
        # update attributes
        ret = await device.async_update()
        if not ret:
            _LOGGER.error("Something went wrong when updating datas ...")
            return False
        # record each area in device
        _LOGGER.debug("Koolnova areas: {}".format(entry.data['areas']))
        for area in entry.data['areas']:
            await device.async_add_manual_registered_area(name=area['Name'], 
                                                    id_zone=area['Area_id'])
        hass.data[DOMAIN]['device'] = device
        coordinator = KoolnovaCoordinator(hass, device)
        hass.data[DOMAIN]['coordinator'] = coordinator
    except Exception as e:
        _LOGGER.exception("Something went wrong ... {}".format(e))

    # Propagation du configEntry à toutes les plateformes déclarées dans notre intégration
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant,
                            entry: ConfigEntry) -> bool:
    """ Unload a config entry. """
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    _LOGGER.debug("Unload entries: {}".format(unload_ok))
    return unload_ok

async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """ Handle removal of an entry """
    _LOGGER.debug("Remove entry")
    if hass.data[DOMAIN]:
        device = hass.data[DOMAIN]['device']
        if device.connected():
            device.disconnect()
