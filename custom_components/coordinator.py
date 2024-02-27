""" for Coordinator integration. """
from __future__ import annotations
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.util import Throttle
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
)

from .koolnova.device import Koolnova

_LOGGER = logging.getLogger(__name__)

class KoolnovaCoordinator(DataUpdateCoordinator):
    """ koolnova coordinator """

    def __init__(self,
                    hass: HomeAssistant, 
                    device: Koolnova,
                ) -> None:
        """ Class constructor """
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=DOMAIN,
            update_method=device.async_update_all_areas,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=30),
        )