""" for Coordinator integration. """
from __future__ import annotations
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

from .koolnova.device import Koolnova

_LOGGER = logging.getLogger(__name__)

class KoolnovaCoordinator(DataUpdateCoordinator):
    """ koolnova coordinator """

    def __init__(self,
                    hass: HomeAssistant, 
                    device: Koolnova,
                    update_interval_seconds:int = DEFAULT_UPDATE_INTERVAL,
                ) -> None:
        """ Class constructor """
        self._device = device
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=DOMAIN,
            update_method=self._async_update_data,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=update_interval_seconds),
        )

    async def _async_update_data(self) -> dict:
        """ Fetch data from the Koolnova device. """
        try:
            data = await self._device.async_update_all_areas()
        except Exception as err:
            raise UpdateFailed(
                f"Error communicating with Koolnova device: {err}"
            ) from err

        if data is None:
            raise UpdateFailed("Koolnova device returned no update data")

        return data
