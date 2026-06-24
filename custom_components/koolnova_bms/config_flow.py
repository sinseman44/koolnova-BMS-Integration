""" Le Config Flow """

import logging
import voluptuous as vol

from homeassistant import exceptions
import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow, FlowResult
from homeassistant.const import CONF_BASE
from .const import DOMAIN, CONF_NAME

from .koolnova.operations import Operations
from .koolnova.const import (
    DEFAULT_MODE,
    DEFAULT_TCP_ADDR,
    DEFAULT_TCP_PORT,
    DEFAULT_TCP_RETRIES,
    DEFAULT_TCP_RECO_DELAY,
    DEFAULT_TCP_RECO_DELAY_MAX,
    DEFAULT_ADDR,
    DEFAULT_BAUDRATE,
    DEFAULT_PARITY,
    DEFAULT_STOPBITS,
    DEFAULT_BYTESIZE,
    NB_ZONE_MAX,
    TABLE_VERSION_AUTO,
    TABLE_VERSION_V1,
    TABLE_VERSION_V2,
    normalize_table_version,
)

_LOGGER = logging.getLogger(__name__)

TABLE_VERSION_LABELS = {
    TABLE_VERSION_AUTO: "Auto detect",
    TABLE_VERSION_V1: "Koolnova 1.0",
    TABLE_VERSION_V2: "Koolnova 2.0",
}
TABLE_VERSION_OPTIONS = list(TABLE_VERSION_LABELS.values())

def _create_conn_from_config(config: dict) -> Operations:
    """Create a temporary Modbus client from config flow data/options."""
    table_version = normalize_table_version(
        config.get("Table_version")
    )
    if config["Mode"] == "Modbus RTU":
        return Operations(mode="Modbus RTU",
                          timeout=config["Timeout"],
                          debug=config["Debug"],
                          port=config["Device"],
                          addr=config["Address"],
                          baudrate=int(config["Baudrate"]),
                          parity=config["Parity"][0],
                          stopbits=config["Stopbits"],
                          bytesize=config["Sizebyte"],
                          table_version=table_version)
    return Operations(mode="Modbus TCP",
                      timeout=config["Timeout"],
                      debug=config["Debug"],
                      addr=config["Address"],
                      port=config["Port"],
                      modbus=config["Modbus"],
                      retries=config["Retries"],
                      reco_delay_min=config["Reconnect_delay_min"],
                      reco_delay_max=config["Reconnect_delay_max"],
                      table_version=table_version)

class KoolnovaConfigFlow(ConfigFlow, domain=DOMAIN):
    """ La classe qui implémente le config flow notre DOMAIN. 
        Elle doit dériver de FlowHandler
    """

    # La version de notre configFlow va permettre de migrer les entités
    # vers une version plus récente en cas de changement
    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow instance state."""
        # le dictionnaire qui va recevoir tous les user_input. On le vide au démarrage
        self._user_inputs: dict = {}
        self._conn: Operations | None = None

    def _disconnect_conn(self) -> None:
        """Disconnect the temporary Modbus client used during config flow."""
        if self._conn and self._conn.connected():
            self._conn.disconnect()
        self._conn = None

    def _create_conn(self) -> Operations:
        """Create a fresh temporary Modbus client from collected inputs."""
        return _create_conn_from_config(self._user_inputs)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow for this integration."""
        return KoolnovaOptionsFlow(config_entry)

    async def _set_unique_id_and_abort_if_configured(self) -> None:
        """Set a stable unique id for this controller and abort duplicates."""
        if self._user_inputs["Mode"] == "Modbus RTU":
            unique_id = (
                f"rtu:{self._user_inputs['Device']}:"
                f"{self._user_inputs['Address']}"
            )
        else:
            unique_id = (
                f"tcp:{self._user_inputs['Address']}:"
                f"{self._user_inputs['Port']}:"
                f"{self._user_inputs['Modbus']}"
            )
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

    async def async_step_user(self,
                            user_input: dict | None = None) -> FlowResult:
        """ Gestion de l'étape 'user'.
            Point d'entrée du configFlow. Cette méthode est appelée 2 fois:
            1. 1ere fois sans user_input -> Affichage du formulaire de configuration
            2. 2eme fois avec les données saisies par l'utilisateur dans user_input -> Sauvegarde des données saisies 
        """
        errors = {}
        user_form = vol.Schema( #pylint: disable=invalid-name
            {
                vol.Required("Mode", default=str(DEFAULT_MODE)): vol.In(["Modbus TCP", "Modbus RTU"])
            }
        )

        if user_input:
            self._user_inputs.update(user_input)
            if user_input["Mode"] == "Modbus RTU":
                # go to next step
                return await self.async_step_rtu()
            elif user_input["Mode"] == "Modbus TCP":
                # go to next step
                return await self.async_step_tcp()
            else:
                _LOGGER.warning("no choice :p")

        # first call or error
        return self.async_show_form(step_id="user", 
                                    data_schema=user_form,
                                    errors=errors)

    async def async_step_tcp(self, 
                            user_input: dict | None = None) -> FlowResult:
        """ Gestion de l'étape 'tcp'.
            Cette méthode est appelée 2 fois:
            1. 1ere fois sans user_input -> Affichage du formulaire de configuration
            2. 2eme fois avec les données saisies par l'utilisateur dans user_input -> Sauvegarde des données saisies 
        """
        errors = {}
        tcp_form = vol.Schema( #pylint: disable=invalid-name
            {
                vol.Required("Name", default="koolnova"): vol.Coerce(str),
                vol.Required("Modbus", default=DEFAULT_ADDR): vol.Coerce(int),
                vol.Required("Address", default=DEFAULT_TCP_ADDR): vol.Coerce(str),
                vol.Required("Port", default=DEFAULT_TCP_PORT): vol.Coerce(int),
                vol.Required("Retries", default=DEFAULT_TCP_RETRIES): vol.Coerce(int),
                vol.Required("Reconnect_delay_min", default=DEFAULT_TCP_RECO_DELAY): vol.Coerce(float),
                vol.Required("Reconnect_delay_max", default=DEFAULT_TCP_RECO_DELAY_MAX): vol.Coerce(float),
                vol.Required("Timeout", default=5): vol.Coerce(int),
                vol.Optional("Debug", default=False): cv.boolean
            }
        )
        if user_input:
            _LOGGER.debug("[config_flow|tcp] values received: {}".format(user_input))
            self._user_inputs.update(user_input)
            self._conn = self._create_conn()
            try:
                await self._conn.async_connect()
                if not self._conn.connected():
                    raise CannotConnectError(reason="Client Modbus TCP not connected")
                _LOGGER.debug("test communication with koolnova system")
                ret = await self._conn.async_test_communication()
                if not ret:
                    self._disconnect_conn()
                    raise CannotConnectError(reason="Communication error")
                self._disconnect_conn()
                await self._set_unique_id_and_abort_if_configured()

                # go to next step
                return await self.async_step_table_version()
            except CannotConnectError:
                _LOGGER.exception("Cannot connect to koolnova system")
                self._disconnect_conn()
                errors[CONF_BASE] = "cannot_connect"
            except AbortFlow:
                self._disconnect_conn()
                raise
            except Exception as e:
                self._disconnect_conn()
                _LOGGER.exception("Config Flow generic error")

        # first call or error
        return self.async_show_form(step_id="tcp", 
                                    data_schema=tcp_form,
                                    errors=errors)

    async def async_step_rtu(self, 
                            user_input: dict | None = None) -> FlowResult:
        """ Gestion de l'étape 'rtu'.
            Cette méthode est appelée 2 fois:
            1. 1ere fois sans user_input -> Affichage du formulaire de configuration
            2. 2eme fois avec les données saisies par l'utilisateur dans user_input -> Sauvegarde des données saisies 
        """
        errors = {}
        rtu_form = vol.Schema( #pylint: disable=invalid-name
            {
                vol.Required("Name", default="koolnova"): vol.Coerce(str),
                vol.Required("Device", default="/dev/ttyUSB0"): vol.Coerce(str),
                vol.Required("Address", default=DEFAULT_ADDR): vol.Coerce(int),
                vol.Required("Baudrate", default=str(DEFAULT_BAUDRATE)): vol.In(["9600", "19200"]),
                vol.Required("Sizebyte", default=DEFAULT_BYTESIZE): vol.Coerce(int),
                vol.Required("Parity", default="EVEN"): vol.In(["EVEN", "NONE"]),
                vol.Required("Stopbits", default=DEFAULT_STOPBITS): vol.Coerce(int),
                vol.Required("Timeout", default=5): vol.Coerce(int),
                vol.Optional("Debug", default=False): cv.boolean
            }
        )

        if user_input:
            _LOGGER.debug("[config_flow|rtu] values received: {}".format(user_input))
            # Second call; On memorise les données dans le dictionnaire
            self._user_inputs.update(user_input)
            self._conn = self._create_conn()
            try:
                await self._conn.async_connect()
                if not self._conn.connected():
                    raise CannotConnectError(reason="Client Modbus RTU not connected")
                #_LOGGER.debug("test communication with koolnova system")
                ret = await self._conn.async_test_communication()
                if not ret:
                    self._disconnect_conn()
                    raise CannotConnectError(reason="Communication error")
                self._disconnect_conn()
                await self._set_unique_id_and_abort_if_configured()

                # go to next step
                return await self.async_step_table_version()
            except CannotConnectError:
                _LOGGER.exception("Cannot connect to koolnova system")
                self._disconnect_conn()
                errors[CONF_BASE] = "cannot_connect"
            except AbortFlow:
                self._disconnect_conn()
                raise
            except Exception as e:
                self._disconnect_conn()
                _LOGGER.exception("Config Flow generic error")

        # first call or error
        return self.async_show_form(step_id="rtu", 
                                    data_schema=rtu_form,
                                    errors=errors)

    async def async_step_table_version(self,
                                user_input: dict | None = None) -> FlowResult:
        """ Gestion de l'étape de choix de version de table Modbus """
        errors = {}
        table_version_form = vol.Schema(
            {
                vol.Required("Table_version", default=TABLE_VERSION_LABELS[TABLE_VERSION_AUTO]): vol.In(TABLE_VERSION_OPTIONS)
            }
        )

        if user_input:
            self._user_inputs.update(user_input)
            table_version = normalize_table_version(
                self._user_inputs["Table_version"]
            )
            if table_version == TABLE_VERSION_AUTO:
                try:
                    self._conn = self._create_conn()
                    await self._conn.async_connect()
                    if not self._conn.connected():
                        raise CannotConnectError(reason="Client Modbus not connected")
                    ret, table_version = await self._conn.async_detect_table_version()
                    self._disconnect_conn()
                    if not ret:
                        raise CannotConnectError(reason="Unable to detect Modbus table version")
                except CannotConnectError:
                    _LOGGER.exception("Cannot detect Koolnova Modbus table version")
                    self._disconnect_conn()
                    errors[CONF_BASE] = "cannot_connect"
                    return self.async_show_form(step_id="table_version",
                                                data_schema=table_version_form,
                                                errors=errors)
                except Exception:
                    _LOGGER.exception("Config Flow table version detection error")
                    self._disconnect_conn()
                    errors[CONF_BASE] = "cannot_connect"
                    return self.async_show_form(step_id="table_version",
                                                data_schema=table_version_form,
                                                errors=errors)
            self._user_inputs["Table_version"] = table_version
            self._user_inputs["areas"] = []
            return await self.async_step_areas()

        return self.async_show_form(step_id="table_version",
                                    data_schema=table_version_form,
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
                try:
                    if user_input['Area_id'] < 1 or user_input['Area_id'] > NB_ZONE_MAX:
                        raise ZoneIdError(reason="Area_id must be between 1 and 16")
                    self._conn = self._create_conn()
                    await self._conn.async_connect()
                    if not self._conn.connected():
                        raise CannotConnectError(reason="Client Modbus not connected")
                    # test if area is configured into koolnova system
                    ret, _ = await self._conn.async_area_registered(user_input["Area_id"])
                    if not ret:
                        raise AreaNotRegistredError(reason="Area Id is not registred")

                    self._disconnect_conn()
                    # Update dict
                    self._user_inputs["areas"].append(user_input)
                    # Last area to configure or not ?
                    if not user_input['Other_area']:
                        # Create entities
                        return self.async_create_entry(title=CONF_NAME,
                                                       data=self._user_inputs)
                    # New area to configure
                    return await self.async_step_areas()
                except CannotConnectError:
                    _LOGGER.exception("Cannot connect to koolnova system")
                    self._disconnect_conn()
                    errors[CONF_BASE] = "cannot_connect"
                except AreaNotRegistredError:
                    _LOGGER.exception("Area (id:%s) is not registered to the koolnova system", user_input['Area_id'])
                    self._disconnect_conn()
                    errors[CONF_BASE] = "area_not_registered"
                except ZoneIdError:
                    _LOGGER.exception("Area Id must be between 1 and 16")
                    self._disconnect_conn()
                    errors[CONF_BASE] = "zone_id_error"
                except Exception:
                    self._disconnect_conn()
                    _LOGGER.exception("Config Flow generic error")
            
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

class KoolnovaOptionsFlow(OptionsFlow):
    """Options flow to update runtime connection settings."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._conn: Operations | None = None

    def _disconnect_conn(self) -> None:
        """Disconnect the temporary Modbus client used during options flow."""
        if self._conn and self._conn.connected():
            self._conn.disconnect()
        self._conn = None

    def _disconnect_runtime_device(self) -> None:
        """Disconnect the currently loaded runtime device before testing options."""
        runtime_data = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)
        if not runtime_data:
            return
        device = runtime_data.get("device")
        if device and device.connected():
            device.disconnect()

    async def _reload_runtime_device(self) -> None:
        """Reload the config entry to restore the previous runtime connection."""
        if self._config_entry.entry_id in self.hass.data.get(DOMAIN, {}):
            await self.hass.config_entries.async_reload(self._config_entry.entry_id)

    async def async_step_init(self,
                              user_input: dict | None = None) -> FlowResult:
        """Manage Koolnova options."""
        if self._config_entry.data["Mode"] != "Modbus RTU":
            return self.async_abort(reason="not_supported")

        config = {
            **self._config_entry.data,
            **self._config_entry.options,
        }
        errors = {}
        options_form = vol.Schema(
            {
                vol.Required("Device", default=config["Device"]): vol.Coerce(str),
            }
        )

        if user_input:
            updated_config = {**config, **user_input}
            self._disconnect_runtime_device()
            self._conn = _create_conn_from_config(updated_config)
            try:
                await self._conn.async_connect()
                if not self._conn.connected():
                    raise CannotConnectError(reason="Client Modbus RTU not connected")
                ret = await self._conn.async_test_communication()
                if not ret:
                    raise CannotConnectError(reason="Communication error")
                self._disconnect_conn()
                return self.async_create_entry(
                    title="",
                    data={
                        **self._config_entry.options,
                        **user_input,
                    },
                )
            except CannotConnectError:
                _LOGGER.exception("Cannot connect to koolnova system")
                self._disconnect_conn()
                await self._reload_runtime_device()
                errors[CONF_BASE] = "cannot_connect"
            except Exception:
                self._disconnect_conn()
                _LOGGER.exception("Options Flow generic error")
                await self._reload_runtime_device()
                errors[CONF_BASE] = "cannot_connect"

        return self.async_show_form(step_id="init",
                                    data_schema=options_form,
                                    errors=errors)
