""" Le Config Flow """

import logging
import voluptuous as vol

from homeassistant import exceptions
import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.const import CONF_BASE
from .const import DOMAIN, CONF_NAME

from .koolnova.operations import Operations
from .koolnova.const import (
    DEFAULT_ADDR,
    DEFAULT_BAUDRATE,
    DEFAULT_PARITY,
    DEFAULT_STOPBITS,
    DEFAULT_BYTESIZE,
    NB_ZONE_MAX
)

_LOGGER = logging.getLogger(__name__)

class TestVBE4ConfigFlow(ConfigFlow, domain=DOMAIN):
    """ La classe qui implémente le config flow notre DOMAIN. 
        Elle doit dériver de FlowHandler
    """

    # La version de notre configFlow va permettre de migrer les entités
    # vers une version plus récente en cas de changement
    VERSION = 1
    # le dictionnaire qui va recevoir tous les user_input. On le vide au démarrage
    _user_inputs: dict = {}
    _conn = None

    async def async_step_user(self, 
                                user_input: dict | None = None) -> FlowResult:
        """ Gestion de l'étape 'user'.
            Point d'entrée de mon configFlow. Cette méthode est appelée 2 fois:
            1. 1ere fois sans user_input -> Affichage du formulaire de configuration
            2. 2eme fois avec les données saisies par l'utilisateur dans user_input -> Sauvegarde des données saisies 
        """
        errors = {}
        user_form = vol.Schema( #pylint: disable=invalid-name
            {
                vol.Required("Name", default="koolnova"): vol.Coerce(str),
                vol.Required("Device", default="/dev/ttyUSB0"): vol.Coerce(str),
                vol.Required("Address", default=DEFAULT_ADDR): vol.Coerce(int),
                vol.Required("Baudrate", default=str(DEFAULT_BAUDRATE)): vol.In(["9600", "19200"]),
                vol.Required("Sizebyte", default=DEFAULT_BYTESIZE): vol.Coerce(int),
                vol.Required("Parity", default="EVEN"): vol.In(["EVEN", "NONE"]),
                vol.Required("Stopbits", default=DEFAULT_STOPBITS): vol.Coerce(int),
                vol.Required("Timeout", default=1): vol.Coerce(int),
                vol.Optional("Debug", default=False): cv.boolean
            }
        )

        if user_input:
            _LOGGER.debug("config_flow [user] - Step 1b -> On a reçu les valeurs: {}".format(user_input))
            # Second call; On memorise les données dans le dictionnaire
            self._user_inputs.update(user_input)

            self._conn = Operations(port=self._user_inputs["Device"],
                                    addr=self._user_inputs["Address"],
                                    baudrate=int(self._user_inputs["Baudrate"]),
                                    parity=self._user_inputs["Parity"][0],
                                    bytesize=self._user_inputs["Sizebyte"],
                                    stopbits=self._user_inputs["Stopbits"],
                                    timeout=self._user_inputs["Timeout"],
                                    debug=self._user_inputs["Debug"])
            try:
                await self._conn.connect()
                if not self._conn.connected():
                    raise CannotConnectError(reason="Client Modbus not connected")
                #_LOGGER.debug("test communication with koolnova system")
                ret, _ = await self._conn.system_status()
                if not ret:
                    self._conn.disconnect()
                    raise CannotConnectError(reason="Communication error")
                self._conn.disconnect()

                self._user_inputs["areas"] = []
                # go to next step
                return await self.async_step_areas()
            except CannotConnectError:
                _LOGGER.exception("Cannot connect to koolnova system")
                errors[CONF_BASE] = "cannot_connect"
            except Exception as e:
                _LOGGER.exception("Config Flow generic error")

        # first call or error
        return self.async_show_form(step_id="user", 
                                    data_schema=user_form,
                                    errors=errors)

    async def async_step_areas(self,
                                user_input: dict | None = None) -> FlowResult:
        """ Gestion de l'étape de découverte manuelle des zones """
        errors = {}
        default_id = 1
        default_area_name = "Area 1"
        # set default_id to the last id configured
        # set default_area_name with the last id configured
        for area in self._user_inputs["areas"]:
            default_id = area['Area_id'] + 1
            default_area_name = "Area " + str(default_id)
        zone_form = vol.Schema(
            {
                vol.Required("Name", default=default_area_name): vol.Coerce(str),
                vol.Required("Area_id", default=default_id): vol.Coerce(int),
                vol.Optional("Other_area", default=False): cv.boolean
            }
        )

        if user_input:
            # second call
            try:
                # test if area_id is already configured
                for area in self._user_inputs["areas"]:
                    if user_input['Area_id'] == area['Area_id']:
                        raise AreaAlreadySetError(reason="Area is already configured")
                # Last area to configure or not ?
                if not user_input['Other_area']:
                    try:
                        if not self._conn.connected():
                            await self._conn.connect()
                        if user_input['Area_id'] > NB_ZONE_MAX:
                            raise ZoneIdError(reason="Area_id must be between 1 and 16")
                        #_LOGGER.debug("test area registered with id: {}".format(user_input['Area_id']))
                        # test if area is configured into koolnova system 
                        ret, _ = await self._conn.zone_registered(user_input["Area_id"])
                        if not ret:
                            self._conn.disconnect()
                            raise AreaNotRegistredError(reason="Area Id is not registred")
                    
                        self._conn.disconnect()
                        # Update dict
                        self._user_inputs["areas"].append(user_input)
                        # Create entities
                        return self.async_create_entry(title=CONF_NAME, 
                                                        data=self._user_inputs)
                    except CannotConnectError:
                        _LOGGER.exception("Cannot connect to koolnova system")
                        errors[CONF_BASE] = "cannot_connect"
                    except AreaNotRegistredError:
                        _LOGGER.exception("Area (id:{}) is not registered to the koolnova system".format(user_input['Area_id']))
                        errors[CONF_BASE] = "area_not_registered"
                    except ZoneIdError:
                        _LOGGER.exception("Area Id must be between 1 and 16")
                        errors[CONF_BASE] = "zone_id_error"
                    except Exception as e:
                        _LOGGER.exception("Config Flow generic error")
                else:
                    #_LOGGER.debug("Config_flow [zone] - Une autre zone à configurer")
                    # Update dict
                    self._user_inputs["areas"].append(user_input)
                    # New area to configure
                    return await self.async_step_areas()
            
            except AreaAlreadySetError:
                _LOGGER.exception("Area (id:{}) is already configured".format(user_input['Area_id']))
                errors[CONF_BASE] = "area_already_configured"

        # first call or error
        return self.async_show_form(step_id="areas", 
                                    data_schema=zone_form,
                                    errors=errors)

class KnownError(exceptions.HomeAssistantError):
    """ Base class for errors known to this config flow
        [error_name] is the value passed to [errors] in async_show_form, which should match
        a key under "errors" in string.json

        [applies_to_field] is the name of the field name that contains the error (for async_show_form)
        if the field doesn't exist in the form, CONF_BASE will be used instead.
    """
    error_name = "unknown_error"
    applies_to_field = CONF_BASE

    def __init__(self, *args: object, **kwargs: dict[str, str]) -> None:
        super().__init__(*args)
        self._extra_info = kwargs

    def get_errors_and_placeholders(self, schema):
        """ Return dicts of errors and description_placeholders for adding to async_show_form """
        key = self.applies_to_field
        if key not in {k.schema for k in schema}:
            key = CONF_BASE
        return ({key: self.error_name}, self._extra_info or {})

class CannotConnectError(KnownError):
    """ Error to indicate we cannot connect """
    error_name = "cannot_connect"

class AreaNotRegistredError(KnownError):
    """ Error to indicate that area is not registered """
    error_name = "area_not_registered"

class AreaAlreadySetError(KnownError):
    """ Error to indicate that the area is already configured """
    error_name = "area_already_configured"

class ZoneIdError(KnownError):
    """ Error with the Zone_Id """
    error_name = "zone_id_error"