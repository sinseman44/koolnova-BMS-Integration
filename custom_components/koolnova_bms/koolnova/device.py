""" local API to manage system, engines and areas """ 

import logging as log
import warnings

from homeassistant.helpers.entity import DeviceInfo
from ..const import DOMAIN

from . import const
from .operations import Operations, ModbusConnexionError

_LOGGER = log.getLogger(__name__)

class Area:
    ''' koolnova Area class '''

    def __init__(self,
                    name:str = "",
                    id_zone:int = 0,
                    state:const.ZoneState = const.ZoneState.STATE_OFF,
                    register:const.ZoneRegister = const.ZoneRegister.REGISTER_OFF,
                    fan_mode:const.ZoneFanMode = const.ZoneFanMode.FAN_OFF,
                    clim_mode:const.ZoneClimMode = const.ZoneClimMode.OFF,
                    real_temp:float = 0,
                    order_temp:float = 0
                ) -> None:
        ''' Class constructor '''
        self._name = name
        self._id = id_zone
        self._state = state
        self._register = register
        self._fan_mode = fan_mode
        self._clim_mode = clim_mode
        self._real_temp = real_temp
        self._order_temp = order_temp

    @property
    def name(self) -> str:
        ''' Get area name '''
        return self._name

    @name.setter
    def name(self, name:str) -> None:
        ''' Set area name '''
        if not isinstance(name, str):
            raise AssertionError('Input variable must be a string')
        self._name = name

    @property
    def id_zone(self) -> int:
        ''' Get area id '''
        return self._id

    @property
    def state(self) -> const.ZoneState:
        ''' Get state '''
        return self._state

    @state.setter
    def state(self, val:const.ZoneState) -> None:
        ''' Set state '''
        if not isinstance(val, const.ZoneState):
            raise AssertionError('Input variable must be Enum ZoneState')
        self._state = val

    @property
    def register(self) -> const.ZoneRegister:
        ''' Get register state '''
        return self._register

    @register.setter
    def register(self, val:const.ZoneRegister) -> None:
        ''' Set register state '''
        if not isinstance(val, const.ZoneRegister):
            raise AssertionError('Input variable must be Enum ZoneRegister')
        self._register = val

    @property
    def fan_mode(self) -> const.ZoneFanMode:
        ''' Get Fan Mode '''
        return self._fan_mode

    @fan_mode.setter
    def fan_mode(self, val:const.ZoneFanMode) -> None:
        ''' Set Fan Mode '''
        if not isinstance(val, const.ZoneFanMode):
            raise AssertionError('Input variable must be Enum ZoneFanMode')
        self._fan_mode = val

    @property
    def clim_mode(self) -> const.ZoneClimMode:
        ''' Get Clim Mode '''
        return self._clim_mode

    @clim_mode.setter
    def clim_mode(self, val:const.ZoneClimMode) -> None:
        ''' Set Clim Mode '''
        if not isinstance(val, const.ZoneClimMode):
            raise AssertionError('Input variable must be Enum ZoneClimMode')
        self._clim_mode = val

    @property
    def real_temp(self) -> float:
        ''' Get real temp '''
        return self._real_temp

    @real_temp.setter
    def real_temp(self, val:float) -> None:
        ''' Set Real Temp '''
        if not isinstance(val, float):
            raise AssertionError('Input variable must be Float')
        self._real_temp = val

    @property
    def order_temp(self) -> float:
        ''' Get order temp '''
        return self._order_temp

    @order_temp.setter
    def order_temp(self, val:float) -> None:
        ''' Set Order Temp '''
        if not isinstance(val, float):
            raise AssertionError('Input variable must be float')
        if val > const.MAX_TEMP_ORDER or val < const.MIN_TEMP_ORDER:
            raise OrderTempError('Order temp value must be between {} and {}'.format(const.MIN_TEMP_ORDER, const.MAX_TEMP_ORDER))
        self._order_temp = val

    def __repr__(self) -> str:
        ''' repr method '''
        return repr('Area(Name: {}, Id:{}, State:{}, Register:{}, Fan:{}, Clim:{}, Real Temp:{}, Order Temp:{})'.format(
                        self._name,
                        self._id, 
                        self._state,
                        self._register,
                        self._fan_mode,
                        self._clim_mode,
                        self._real_temp,
                        self._order_temp))

class Engine:
    ''' koolnova Engine class '''

    def __init__(self,
                    engine_id:int = 0,
                    throughput:int = 0,
                    state:const.FlowEngine = const.FlowEngine.AUTO,
                    order_temp:float = 0
                ) -> None:
        ''' Constructor class '''
        self._engine_id = engine_id
        self._throughput = throughput
        self._state = state
        self._order_temp = order_temp

    @property
    def engine_id(self) -> int:
        ''' Get Engine ID '''
        return self._engine_id

    @engine_id.setter
    def engine_id(self, val:int) -> None:
        ''' Set Engine ID '''
        if not isinstance(val, int):
            raise AssertionError('Input variable must be Int')
        if val > const.NUM_OF_ENGINES:
            raise NumUnitError('Engine ID must be lower than {}'.format(const.NUM_OF_ENGINES))
        self._engine_id = val

    @property
    def throughput(self) -> int:
        ''' Get throughput Engine '''
        return self._throughput

    @throughput.setter
    def throughput(self, val:int) -> None:
        ''' Set throughput Engine '''
        if not isinstance(val, int):
            raise AssertionError('Input variable must be Int')
        if val > const.FLOW_ENGINE_VAL_MAX or val < const.FLOW_ENGINE_VAL_MIN:
            raise FlowEngineError('throughput engine value ({}) must be between {} and {}'.format(val,
                                    const.FLOW_ENGINE_VAL_MIN,
                                    const.FLOW_ENGINE_VAL_MAX))
        self._throughput = val

    @property
    def state(self) -> const.FlowEngine:
        ''' Get Engine state '''
        return self._state

    @state.setter
    def state(self, val:const.FlowEngine) -> None:
        ''' Set Engine state '''
        if not isinstance(val, const.FlowEngine):
            raise AssertionError('Input variable must be Enum FlowEngine')
        self._state = val

    @property
    def order_temp(self) -> float:
        ''' Get Order Temp '''
        return self._order_temp

    @order_temp.setter
    def order_temp(self, val:float = 0.0) -> None:
        ''' Set order temp engine '''
        if not isinstance(val, float):
            raise AssertionError('Input variable must be Int')
        if val > 0 and (val > 35.0 or val < 15.0):
            raise OrderTempError('Flow Engine value ({}) must be between 15 and 35'.format(val))
        self._order_temp = val

    def __repr__(self) -> str:
        ''' repr method '''
        return repr('Unit(Id:{}, Throughput:{}, State:{}, Order Temp:{})'.format(self._engine_id,
                        self._throughput,
                        self._state,
                        self._order_temp))

class Koolnova:
    ''' koolnova Device class '''

    _rtu_port:str = ""
    _rtu_addr:int = const.DEFAULT_ADDR
    _rtu_baudrate:int = const.DEFAULT_BAUDRATE
    _rtu_parity:str = const.DEFAULT_PARITY
    _rtu_bytesize:int = const.DEFAULT_BYTESIZE
    _rtu_stopbits:int = const.DEFAULT_STOPBITS

    _tcp_port:int = const.DEFAULT_TCP_PORT
    _tcp_addr:str = const.DEFAULT_TCP_ADDR
    _tcp_modbus:int = const.DEFAULT_ADDR
    _tcp_retries:int = const.DEFAULT_TCP_RETRIES
    _tcp_reco_delay_min:float = const.DEFAULT_TCP_RECO_DELAY
    _tcp_reco_delay_max:float = const.DEFAULT_TCP_RECO_DELAY_MAX

    def __init__(self, mode:str = "", name:str = "", timeout:int = 1, debug:bool = False, **kwargs) -> None:
        ''' Class constructor '''
        self._mode = mode
        self._name = name
        self._debug = debug
        self._timeout = timeout
        self._table_version = const.normalize_table_version(
            kwargs.get('table_version')
        )
        self.__dict__.update(kwargs)
        if self._mode == "Modbus RTU":
            self._rtu_port = kwargs.get('port', '')
            self._rtu_addr = kwargs.get('addr', const.DEFAULT_ADDR)
            self._rtu_baudrate = kwargs.get('baudrate', const.DEFAULT_BAUDRATE)
            self._rtu_parity = kwargs.get('parity', const.DEFAULT_PARITY)
            self._rtu_bytesize = kwargs.get('bytesize', const.DEFAULT_BYTESIZE)
            self._rtu_stopbits = kwargs.get('stopbits', const.DEFAULT_STOPBITS)
            self._client = Operations(mode=self._mode,
                                        timeout=self._timeout,
                                        debug=self._debug,
                                        port=self._rtu_port,
                                        addr=self._rtu_addr,
                                        baudrate=self._rtu_baudrate,
                                        parity=self._rtu_parity,
                                        bytesize=self._rtu_bytesize,
                                        stopbits=self._rtu_stopbits,
                                        table_version=self._table_version)
        elif self._mode == "Modbus TCP":
            self._tcp_port = kwargs.get('port', const.DEFAULT_TCP_PORT)
            self._tcp_addr = kwargs.get('addr', const.DEFAULT_TCP_ADDR)
            self._tcp_modbus = kwargs.get('modbus', const.DEFAULT_ADDR)
            self._tcp_retries = kwargs.get('retries', const.DEFAULT_TCP_RETRIES)
            self._tcp_reco_delay_min = kwargs.get('reco_delay_min', const.DEFAULT_TCP_RECO_DELAY)
            self._tcp_reco_delay_max = kwargs.get('reco_delay_max', const.DEFAULT_TCP_RECO_DELAY_MAX)
            self._client = Operations(mode=self._mode,
                                        timeout=self._timeout,
                                        debug=self._debug,
                                        addr=self._tcp_addr,
                                        port=self._tcp_port,
                                        modbus=self._tcp_modbus,
                                        retries=self._tcp_retries,
                                        reco_delay_min=self._tcp_reco_delay_min,
                                        reco_delay_max=self._tcp_reco_delay_max,
                                        table_version=self._table_version)
        else:
            raise InitialisationError('unknown mode ({})'.format(self._mode))
        self._global_mode = const.GlobalMode.COLD
        self._efficiency = const.Efficiency.LOWER_EFF
        self._sys_state = const.SysState.SYS_STATE_OFF
        self._engines = []
        self._areas = []
        self._system_registers = {}
        self._v2_registers = {}

    @property
    def table_version(self) -> str:
        """Return the normalized Modbus table version."""
        return self._table_version

    @property
    def supports_efficiency(self) -> bool:
        """Return whether this table version supports scalar efficiency."""
        return self._client.supports_efficiency

    @property
    def v2_registers(self) -> dict:
        """Return raw Koolnova 2.0 advanced register values."""
        return self._v2_registers

    @property
    def system_registers(self) -> dict:
        """Return raw common system register values."""
        return self._system_registers

    async def _async_update_system_registers(self) -> bool:
        """Update common system values from one Operations snapshot.

        The snapshot is used for both V1 and V2 so global mode, system state and
        system diagnostic registers stay on the same refresh path for both
        table versions.

        Returns:
            True when common system values were refreshed, False otherwise.
        """
        ret, values = await self._client.async_system_snapshot()
        if not ret:
            _LOGGER.error("Error retreiving Koolnova system snapshot")
            return False

        self._global_mode = values["global_mode"]
        self._efficiency = values["efficiency"]
        self._sys_state = values["system_status"]
        self._system_registers = {
            "communication_config": values["communication_config"],
            "modbus_address": values["modbus_address"],
            "infrared_receiver_id": values["infrared_receiver_id"],
        }
        return True

    async def _async_update_v2_registers(self) -> bool:
        """Update raw Koolnova 2.0 advanced register values.

        These values back the V2-only sensors, numbers, switches and selects.
        Operations handles the Modbus block boundaries, including the 40124 gap.

        Returns:
            True when the v2 snapshot was refreshed or not needed, False on
            read failure.
        """
        if self._table_version != const.TABLE_VERSION_V2:
            self._v2_registers = {}
            return True

        ret, values = await self._client.async_v2_registers_snapshot()
        if not ret:
            _LOGGER.error("Error retreiving Koolnova v2 register snapshot")
            return False
        self._v2_registers = values
        return True

    async def _async_update_engines(self) -> bool:
        """Update AC1-AC4 engine values from one Operations snapshot.

        This replaces twelve per-engine reads while preserving the existing
        Engine objects consumed by Home Assistant entities.

        Returns:
            True when all engine values were refreshed, False otherwise.
        """
        ret, engine_values = await self._client.async_engines_snapshot()
        if not ret:
            _LOGGER.error("Error retreiving Koolnova engines snapshot")
            return False

        if len(self._engines) != const.NUM_OF_ENGINES:
            self._engines = [
                Engine(engine_id=idx)
                for idx in range(1, const.NUM_OF_ENGINES + 1)
            ]

        for idx, values in enumerate(engine_values):
            self._engines[idx].throughput = values["throughput"]
            self._engines[idx].state = values["state"]
            self._engines[idx].order_temp = values["order_temp"]
        return True

    async def _async_write_v2_register(self,
                                        label:str,
                                        write_register,
                                        read_register,
                                        *args,
                                        ):
        """Write a Koolnova 2.0 register and refresh only its snapshot value."""
        if self._table_version != const.TABLE_VERSION_V2:
            raise UpdateValueError("Koolnova v2 register {} is not supported by this Modbus table".format(label))

        try:
            ret = await write_register(*args)
        except ValueError as err:
            _LOGGER.error("[V2] Invalid value for register %s: %s", label, err)
            raise UpdateValueError(str(err)) from err
        if not ret:
            _LOGGER.error("[V2] Error writing register %s", label)
            raise UpdateValueError("Error writing Koolnova v2 register {}".format(label))

        ret, value = await read_register()
        if not ret:
            _LOGGER.error("[V2] Error refreshing register %s after write", label)
            raise UpdateValueError("Error refreshing Koolnova v2 register {} after write".format(label))
        self._v2_registers[label] = value
        return value

    async def _async_v2_register_raw(self,
                                        label:str,
                                        read_register,
                                        ) -> int:
        """Return the current raw value for a Koolnova 2.0 register snapshot."""
        if self._table_version != const.TABLE_VERSION_V2:
            raise UpdateValueError("Koolnova v2 register {} is not supported by this Modbus table".format(label))

        value = self._v2_registers.get(label)
        if value is None:
            ret, value = await read_register()
            if not ret:
                _LOGGER.error("[V2] Error reading register %s before write", label)
                raise UpdateValueError("Error reading Koolnova v2 register {} before write".format(label))
            self._v2_registers[label] = value

        if isinstance(value, dict):
            return int(value["raw"])
        return int(value)

    @staticmethod
    def _replace_bit(raw:int,
                        bit:int,
                        value:bool,
                        ) -> int:
        """Return raw with one bit replaced by the requested boolean value."""
        if value:
            return raw | (1 << bit)
        return raw & ~(1 << bit)

    def _area_defined(self, 
                        id_search:int = 0,
                    ) -> (bool, int):
        """ test if area id is defined """
        _areas_found = [idx for idx, x in enumerate(self._areas) if x.id_zone == id_search]
        _idx = 0
        if not _areas_found:
            _LOGGER.error("Area id ({}) not defined".format(id_search))
            return False, _idx
        elif len(_areas_found) > 1:
            _LOGGER.error("Multiple Area with same id ({})".format(id_search))
            return False, _idx
        else:
            _idx  = _areas_found[0]
            _LOGGER.debug("idx found: {}".format(_idx))
        return True, _idx

    async def async_update(self) -> bool:
        ''' update values from modbus '''
        _LOGGER.debug("Retreive engines ...")
        ret = await self._async_update_engines()
        if not ret:
            return False

        _LOGGER.debug("Retreive common system registers ...")
        ret = await self._async_update_system_registers()
        if not ret:
            return False

        if self._table_version == const.TABLE_VERSION_V2:
            _LOGGER.debug("Retreive Koolnova v2 advanced registers ...")
            ret = await self._async_update_v2_registers()
            if not ret:
                return False
        else:
            self._v2_registers = {}
        return True

    async def async_connect(self) -> bool:
        ''' connect to the modbus serial server '''
        ret = True
        await self._client.async_connect()
        if not self.connected():
            ret = False
            raise ClientNotConnectedError("Client Modbus connexion error")

        #_LOGGER.info("Update system values")
        #ret = await self.update()

        return ret

    def connected(self) -> bool:
        ''' get modbus client status '''
        return self._client.connected

    def disconnect(self) -> None:
        ''' close the underlying socket connection '''
        self._client.disconnect()

    async def async_discover_areas(self) -> None:
        ''' Set all registered areas for system '''
        if not self._client.connected:
            raise ModbusConnexionError('Client Modbus not connected')
        zones_lst = await self._client.async_discover_registered_areas()
        for zone in zones_lst:
            self._areas.append(Area(name = zone['name'],
                                    id_zone = zone['id'],
                                    state = zone['state'],
                                    register = zone['register'],
                                    fan_mode = zone['fan'],
                                    clim_mode = zone['clim'],
                                    real_temp = zone['real_temp'],
                                    order_temp = zone['order_temp']
                                    ))
        return

    async def async_add_manual_registered_area(self,
                                                name:str = "",
                                                id_zone:int = 0) -> bool:
        ''' Add manual area to koolnova system '''
        if not self._client.connected:
            raise ModbusConnexionError('Client Modbus not connected')

        ret, zone_dict = await self._client.async_area_registered(zone_id = id_zone)
        if not ret:
            _LOGGER.error("Zone with ID: {} is not registered".format(id_zone))
            return False
        for zone in self._areas:
            if id_zone == zone.id_zone:
                _LOGGER.error('Zone registered with ID: {} is already saved')
                return False
        
        self._areas.append(Area(name = name,
                                id_zone = id_zone,
                                state = zone_dict['state'],
                                register = zone_dict['register'],
                                fan_mode = zone_dict['fan'],
                                clim_mode = zone_dict['clim'],
                                real_temp = zone_dict['real_temp'],
                                order_temp = zone_dict['order_temp']
                                ))
        _LOGGER.debug("Areas registered: {}".format(self._areas))
        return True

    @property
    def areas(self) -> list:
        ''' get areas '''
        return self._areas

    def get_area(self, zone_id:int = 0) -> Area | None:
        ''' get specific area '''
        warnings.warn(
            "Koolnova.get_area() is deprecated and will be removed in a future release.",
            DeprecationWarning,
            stacklevel=2,
        )
        _LOGGER.warning("Koolnova.get_area() is deprecated")
        ret, idx = self._area_defined(id_search = zone_id)
        if not ret:
            return None
        return self._areas[idx]

    async def async_update_area(self, zone_id:int = 0) -> tuple[bool, Area | None]:
        """ update specific area from zone_id """
        warnings.warn(
            "Koolnova.async_update_area() is deprecated and will be removed in a future release.",
            DeprecationWarning,
            stacklevel=2,
        )
        _LOGGER.warning("Koolnova.async_update_area() is deprecated")
        ret, idx = self._area_defined(id_search = zone_id)
        if not ret:
            _LOGGER.error("Area not defined ...")
            return False, None

        ret, infos = await self._client.async_area_registered(zone_id = zone_id)
        if not ret:
            _LOGGER.error("Error retreiving area ({}) values".format(zone_id))
            return False, None

        # update areas list values from modbus response
        self._areas[idx].state = infos['state']
        self._areas[idx].register = infos['register']
        self._areas[idx].fan_mode = infos['fan']
        self._areas[idx].clim_mode = infos['clim']
        self._areas[idx].real_temp = infos['real_temp']
        self._areas[idx].order_temp = infos['order_temp']
        return True, self._areas[idx]

    async def async_update_all_areas(self) -> list:
        """Refresh the full device snapshot used by the Home Assistant coordinator.

        This is the central polling entry point used by `KoolnovaCoordinator`.
        It updates the in-memory Area and Engine objects in place, refreshes the
        common global/system values for both V1 and V2 tables, and adds the V2
        advanced register snapshot when the configured table version supports it.

        The returned dictionary is passed directly to coordinator entities, so
        its keys are part of the integration's internal data contract:
        - `areas`: registered zone objects consumed by climate entities.
        - `engines`: AC1-AC4 engine objects consumed by diagnostic entities.
        - `glob`, `eff`, `sys`: current global mode, efficiency and HVAC state.
        - `system_registers`: common Modbus diagnostic registers.
        - `v2_registers`: V2-only decoded register snapshot, or an empty dict for V1.

        Returns:
            Coordinator data dictionary when every required Modbus read succeeds;
            None when any required block cannot be refreshed.
        """
        # Refresh only Home Assistant configured zones; they cannot appear by themselves.
        configured_zone_ids = [_area.id_zone for _area in self._areas]
        _ret, _vals = await self._client.async_areas_registered(
            zone_ids=configured_zone_ids
        )
        if not _ret:
            _LOGGER.error("Error retreiving areas values")
            return None
        else:
            for k,v in _vals.items():
                for _idx, _area in enumerate(self._areas):
                    if k == _area.id_zone:
                        # update areas list values from modbus response
                        self._areas[_idx].state = v['state']
                        self._areas[_idx].register = v['register']
                        self._areas[_idx].fan_mode = v['fan']
                        self._areas[_idx].clim_mode = v['clim']
                        self._areas[_idx].real_temp = v['real_temp']
                        self._areas[_idx].order_temp = v['order_temp']

        # Refresh AC1-AC4 engine values used by diagnostic entities.
        ret = await self._async_update_engines()
        if not ret:
            return None

        # Refresh common global/system registers shared by V1 and V2 tables.
        ret = await self._async_update_system_registers()
        if not ret:
            return None

        if self._table_version == const.TABLE_VERSION_V2:
            # Refresh V2-only advanced registers used by V2 entities.
            ret = await self._async_update_v2_registers()
            if not ret:
                return None
        else:
            self._v2_registers = {}

        return {"areas": self._areas, 
                "engines": self._engines,
                "glob": self._global_mode,
                "eff": self._efficiency,
                "sys": self._sys_state,
                "system_registers": self._system_registers,
                "v2_registers": self._v2_registers}

    @property
    def engines(self) -> list:
        ''' get engines '''
        return self._engines

    @property
    def device_info(self) -> DeviceInfo:
        """ Return a device description for device registry """
        return {
            "name": self._name,
            "manufacturer": "Koolnova",
            "identifiers": {(DOMAIN, "{}-{}".format("Koolnova", self._name))},
        }

    @property
    def name(self) -> str:
        ''' Get name '''
        return self._name

    async def async_set_engine_state(self,
                                    val:const.FlowEngine,
                                    engine_id: int,
                                    ) -> None:
        ''' set engine flow from id '''
        _LOGGER.debug("set engine (id:{}) flow : {}".format(engine_id, val))
        if not isinstance(val, const.FlowEngine):
            raise AssertionError('Input variable must be Enum FlowEngine')
        ret = await self._client.async_set_engine_state(engine_id, val)
        if not ret:
            _LOGGER.error("[GLOBAL] Error writing {} to modbus".format(val))
            raise UpdateValueError('Error writing to modbus updated value')
        self._engines[engine_id - 1].state = val

    @property
    def global_mode(self) -> const.GlobalMode:
        ''' Get Global Mode '''
        return self._global_mode

    async def async_set_global_mode(self,
                                    val:const.GlobalMode,
                                    ) -> None:
        ''' Set Global Mode '''
        _LOGGER.debug("set global mode : {}".format(val))
        if not isinstance(val, const.GlobalMode):
            raise AssertionError('Input variable must be Enum GlobalMode')
        ret = await self._client.async_set_global_mode(val)
        if not ret:
            _LOGGER.error("[GLOBAL] Error writing {} to modbus".format(val))
            raise UpdateValueError('Error writing to modbus updated value')
        self._global_mode = val

    @property
    def efficiency(self) -> const.Efficiency:
        ''' Get Efficiency '''
        return self._efficiency

    async def async_set_efficiency(self,
                                    val:const.Efficiency,
                                    ) -> None:
        ''' Set Efficiency '''
        _LOGGER.debug("set efficiency : {}".format(val))
        if not isinstance(val, const.Efficiency):
            raise AssertionError('Input variable must be Enum Efficiency')
        ret = await self._client.async_set_efficiency(val)
        if not ret:
            _LOGGER.error("[EFF] Error writing {} to modbus".format(val))
            raise UpdateValueError('Error writing to modbus updated value')    
        self._efficiency = val

    async def async_set_v2_parameters(self,
                                        hum:bool | None = None,
                                        af:bool | None = None,
                                        stop:bool | None = None,
                                        eco:bool | None = None,
                                        efi:int | None = None,
                                        din2:bool | None = None,
                                        din1:bool | None = None,
                                        aux1:bool | None = None,
                                        heating:bool | None = None,
                                        pump:bool | None = None,
                                        k5:bool | None = None,
                                        k6:bool | None = None,
                                        ) -> dict:
        ''' Set Koolnova v2 system parameters '''
        raw = await self._async_v2_register_raw(
            "40074_parameters",
            self._client.async_v2_parameters,
        )
        for bit, value in (
            (15, hum),
            (14, af),
            (12, stop),
            (11, eco),
            (6, din2),
            (5, din1),
            (4, aux1),
            (3, heating),
            (2, pump),
            (1, k5),
            (0, k6),
        ):
            if value is not None:
                raw = Koolnova._replace_bit(raw, bit, bool(value))
        if efi is not None:
            efi = int(efi)
            if efi < 0 or efi > 7:
                raise UpdateValueError("efi must be between 0 and 7")
            raw = (raw & ~0x0700) | (efi << 8)
        return await self._async_write_v2_register(
            "40074_parameters",
            self._client.async_set_v2_parameters,
            self._client.async_v2_parameters,
            raw,
        )

    async def async_set_v2_active_modes(self,
                                        radiant_floor_heating:bool | None = None,
                                        radiant_floor_cooling:bool | None = None,
                                        radiant_floor:bool | None = None,
                                        dehumidification:bool | None = None,
                                        heating:bool | None = None,
                                        cooling:bool | None = None,
                                        ventilation:bool | None = None,
                                        ) -> dict:
        ''' Set Koolnova v2 active modes '''
        raw = await self._async_v2_register_raw(
            "40075_active_modes",
            self._client.async_v2_active_modes,
        )
        raw &= ~0x0080
        for bit, value in (
            (6, radiant_floor_heating),
            (5, radiant_floor_cooling),
            (4, radiant_floor),
            (3, dehumidification),
            (2, heating),
            (1, cooling),
            (0, ventilation),
        ):
            if value is not None:
                raw = Koolnova._replace_bit(raw, bit, bool(value))
        return await self._async_write_v2_register(
            "40075_active_modes",
            self._client.async_set_v2_active_modes,
            self._client.async_v2_active_modes,
            raw,
        )

    async def async_set_v2_temperature_limits(self,
                                                max_heating_limit:float,
                                                min_cooling_limit:float,
                                                ) -> dict:
        ''' Set Koolnova v2 temperature limits '''
        return await self._async_write_v2_register(
            "40076_temperature_limits",
            self._client.async_set_v2_temperature_limits,
            self._client.async_v2_temperature_limits,
            max_heating_limit,
            min_cooling_limit,
        )

    async def async_set_v2_auto_changeover_humidity(self,
                                                    mode_when_water_above_threshold:int,
                                                    mode_when_water_below_threshold:int,
                                                    humidity_relay_threshold:int,
                                                    ) -> dict:
        ''' Set Koolnova v2 automatic changeover modes and humidity control '''
        return await self._async_write_v2_register(
            "40077_auto_changeover_humidity",
            self._client.async_set_v2_auto_changeover_humidity,
            self._client.async_v2_auto_changeover_humidity,
            mode_when_water_above_threshold,
            mode_when_water_below_threshold,
            humidity_relay_threshold,
        )

    async def async_set_v2_system_time(self,
                                        day:int,
                                        hour:int,
                                        minute:int,
                                        ) -> dict:
        ''' Set Koolnova v2 system time '''
        return await self._async_write_v2_register(
            "40078_system_time",
            self._client.async_set_v2_system_time,
            self._client.async_v2_system_time,
            day,
            hour,
            minute,
        )

    async def async_set_v2_external_inputs(self,
                                            din2_function:int,
                                            din1_function:int,
                                            ) -> dict:
        ''' Set Koolnova v2 external input functions '''
        return await self._async_write_v2_register(
            "40079_external_inputs",
            self._client.async_set_v2_external_inputs,
            self._client.async_v2_external_inputs,
            din2_function,
            din1_function,
        )

    async def async_set_v2_opening_angle_z1_z8(self,
                                                angle_code:int,
                                                zone_index:int,
                                                ) -> dict:
        ''' Set Koolnova v2 opening angle for zones Z1 to Z8 '''
        return await self._async_write_v2_register(
            "40080_opening_angle_z1_z8",
            self._client.async_set_v2_opening_angle_z1_z8,
            self._client.async_v2_opening_angle_z1_z8,
            angle_code,
            zone_index,
        )

    async def async_set_v2_opening_angle_z9_z16(self,
                                                angle_code:int,
                                                zone_index:int,
                                                ) -> dict:
        ''' Set Koolnova v2 opening angle for zones Z9 to Z16 '''
        return await self._async_write_v2_register(
            "40081_opening_angle_z9_z16",
            self._client.async_set_v2_opening_angle_z9_z16,
            self._client.async_v2_opening_angle_z9_z16,
            angle_code,
            zone_index,
        )

    async def async_set_v2_valve_mask(self,
                                        enabled_zone_indexes:list[int],
                                        ) -> dict:
        ''' Set Koolnova v2 valve mask '''
        raw = 0
        for zone_index in enabled_zone_indexes:
            if zone_index < 0 or zone_index > 15:
                raise UpdateValueError("zone_index must be between 0 and 15")
            raw |= 1 << zone_index
        return await self._async_write_v2_register(
            "40085_valve_mask",
            self._client.async_set_v2_valve_mask,
            self._client.async_v2_valve_mask,
            raw,
        )

    async def async_set_v2_zone_pump_enabled(self,
                                                zone_index:int,
                                                enabled:bool,
                                                ) -> dict:
        ''' Set one Koolnova v2 valve mask zone flag '''
        if zone_index < 0 or zone_index > 15:
            raise UpdateValueError("zone_index must be between 0 and 15")
        raw = await self._async_v2_register_raw(
            "40085_valve_mask",
            self._client.async_v2_valve_mask,
        )
        raw = Koolnova._replace_bit(raw, zone_index, enabled)
        return await self._async_write_v2_register(
            "40085_valve_mask",
            self._client.async_set_v2_valve_mask,
            self._client.async_v2_valve_mask,
            raw,
        )

    async def async_set_v2_pump_delay_valve_offset(self,
                                                    valve_origin_offset:int,
                                                    pump_delay_seconds:int,
                                                    ) -> dict:
        ''' Set Koolnova v2 pump delay and valve offset '''
        return await self._async_write_v2_register(
            "40086_pump_delay_valve_offset",
            self._client.async_set_v2_pump_delay_valve_offset,
            self._client.async_v2_pump_delay_valve_offset,
            valve_origin_offset,
            pump_delay_seconds,
        )

    async def async_set_v2_immersion_heater(self,
                                            activation_delay_minutes:int,
                                            activation_temperature_celsius:int,
                                            ) -> dict:
        ''' Set Koolnova v2 immersion heater settings '''
        return await self._async_write_v2_register(
            "40087_immersion_heater",
            self._client.async_set_v2_immersion_heater,
            self._client.async_v2_immersion_heater,
            activation_delay_minutes,
            activation_temperature_celsius,
        )

    async def async_set_v2_thermostat_block(self,
                                            block_level:int,
                                            ) -> dict:
        ''' Set Koolnova v2 thermostat block level '''
        return await self._async_write_v2_register(
            "40088_thermostat_block",
            self._client.async_set_v2_thermostat_block,
            self._client.async_v2_thermostat_block,
            block_level,
        )

    async def async_set_v2_auto_mode(self,
                                    cooling_water_threshold_celsius:int,
                                    heating_water_threshold_celsius:int,
                                    ) -> dict:
        ''' Set Koolnova v2 automatic mode water thresholds '''
        return await self._async_write_v2_register(
            "40089_auto_mode",
            self._client.async_set_v2_auto_mode,
            self._client.async_v2_auto_mode,
            cooling_water_threshold_celsius,
            heating_water_threshold_celsius,
        )

    async def async_set_v2_mixing_valve_ambient_temperatures(self,
                                                            upper_ambient_temperature_celsius:int,
                                                            lower_ambient_temperature_celsius:int,
                                                            ) -> dict:
        ''' Set Koolnova v2 mixing valve ambient temperatures '''
        return await self._async_write_v2_register(
            "40090_mixing_valve_ambient_temperatures",
            self._client.async_set_v2_mixing_valve_ambient_temperatures,
            self._client.async_v2_mixing_valve_ambient_temperatures,
            upper_ambient_temperature_celsius,
            lower_ambient_temperature_celsius,
        )

    async def async_set_v2_mixing_valve_water_temperatures(self,
                                                            upper_water_temperature_celsius:int,
                                                            lower_water_temperature_celsius:int,
                                                            ) -> dict:
        ''' Set Koolnova v2 mixing valve water temperatures '''
        return await self._async_write_v2_register(
            "40091_mixing_valve_water_temperatures",
            self._client.async_set_v2_mixing_valve_water_temperatures,
            self._client.async_v2_mixing_valve_water_temperatures,
            upper_water_temperature_celsius,
            lower_water_temperature_celsius,
        )

    async def async_set_v2_mixing_valve_mode_info(self,
                                                    safety_factor_code:int,
                                                    mode:int,
                                                    cooling_supply_temperature_celsius:int,
                                                    heating_supply_temperature_celsius:int,
                                                    ) -> dict:
        ''' Set Koolnova v2 mixing valve mode information '''
        return await self._async_write_v2_register(
            "40092_mixing_valve_mode_info",
            self._client.async_set_v2_mixing_valve_mode_info,
            self._client.async_v2_mixing_valve_mode_info,
            safety_factor_code,
            mode,
            cooling_supply_temperature_celsius,
            heating_supply_temperature_celsius,
        )

    @property
    def debug(self) -> bool:
        ''' Get Debug mode '''
        return self._debug

    async def async_set_debug(self,
                                val:bool,
                                ) -> None:
        ''' Set Debug mode '''
        if not isinstance(val, bool):
            raise AssertionError('Input variable must be Enum SysState')
        _LOGGER.debug("set debug mode : {}".format(val))
        ret = await self._client.async_set_debug(val)
        if not ret:
            _LOGGER.error("[DEBUG] Error setting/reseting {}".format(val))
            raise UpdateValueError('Error setting/reseting debug mode') 
        self._debug = val

    @property
    def sys_state(self) -> const.SysState:
        ''' Get System State '''
        return self._sys_state

    async def async_set_sys_state(self,
                                    val:const.SysState,
                                    ) -> None:
        ''' Set System State '''
        if not isinstance(val, const.SysState):
            raise AssertionError('Input variable must be Enum SysState')
        _LOGGER.debug("set system state : {}".format(val))
        ret = await self._client.async_set_system_status(val)
        if not ret:
            _LOGGER.error("[SYS_STATE] Error writing {} to modbus".format(val))
            raise UpdateValueError('Error writing to modbus updated value') 
        self._sys_state = val

    async def async_get_area_temp(self,
                                    zone_id:int,
                                ) -> float:
        """ get current temp of specific Area """
        _ret, _idx = self._area_defined(id_search = zone_id)
        if not _ret:
            _LOGGER.error("Area not defined ...")
            return False

        ret, temp = await self._client.async_area_temp(id_zone = zone_id)
        if not ret:
            _LOGGER.error("Error reading temp for area with ID: {}".format(zone_id))
            return False
        self._areas[_idx].real_temp = temp
        return temp

    async def async_set_area_target_temp(self,
                                        zone_id:int,
                                        temp:float,
                                        ) -> bool:
        """ set target temp of specific area """
        _ret, _idx = self._area_defined(id_search = zone_id)
        if not _ret:
            _LOGGER.error("Area not defined ...")
            return False

        ret = await self._client.async_set_area_target_temp(zone_id = zone_id, val = temp)
        if not ret:
            _LOGGER.error("Error writing target temp for area with ID: {}".format(zone_id))
            return False
        self._areas[_idx].order_temp = temp
        return True

    async def async_get_area_target_temp(self,
                                        zone_id:int,
                                        ) -> float:
        """ get target temp of specific area """
        _ret, _idx = self._area_defined(id_search = zone_id)
        if not _ret:
            _LOGGER.error("Area not defined ...")
            return False

        ret, temp = await self._client.async_area_target_temp(id_zone = zone_id)
        if not ret:
            _LOGGER.error("Error reading target temp for area with ID: {}".format(zone_id))
            return 0.0
        self._areas[_idx].order_temp = temp
        return temp

    async def async_set_area_off(self,
                                zone_id:int,
                                ) -> bool:
        """ set area off """
        _ret, _idx = self._area_defined(id_search = zone_id)
        if not _ret:
            _LOGGER.error("Area not defined ...")
            return False

        ret = await self._client.async_set_area_state(id_zone = zone_id, val = const.ZoneState.STATE_OFF)
        if not ret:
            _LOGGER.error("Error writing area state (STATE_OFF) for area with ID: {}".format(zone_id))
            return False
        self._areas[_idx].state = const.ZoneState.STATE_OFF
        return True
    
    async def async_set_area_on(self,
                                zone_id:int,
                                ) -> bool:
        """ set area on """
        _ret, _idx = self._area_defined(id_search = zone_id)
        if not _ret:
            _LOGGER.error("Area not defined ...")
            return False

        ret = await self._client.async_set_area_state(id_zone = zone_id, val = const.ZoneState.STATE_ON)
        if not ret:
            _LOGGER.error("Error writing area state (STATE_ON) for area with ID: {}".format(zone_id))
            return False
        self._areas[_idx].state = const.ZoneState.STATE_ON
        return True

    async def async_set_area_clim_mode(self,
                                        zone_id:int, 
                                        mode:const.ZoneClimMode,
                                        ) -> bool:
        """ set climate mode for specific area """
        _ret, _idx = self._area_defined(id_search = zone_id)
        if not _ret:
            _LOGGER.error("Area not defined ...")
            return False

        if mode == const.ZoneClimMode.OFF:
            _LOGGER.debug("Set area state to OFF")
            ret = await self._client.async_set_area_state(id_zone = zone_id, val = const.ZoneState.STATE_OFF)
            if not ret:
                _LOGGER.error("Error writing area state for area with ID: {}".format(zone_id))
                return False
            self._areas[_idx].state = const.ZoneState.STATE_OFF
        else:
            if self._areas[_idx].state == const.ZoneState.STATE_OFF:
                _LOGGER.debug("Set area state to ON")
                # update area state
                ret = await self._client.async_set_area_state(id_zone = zone_id, val = const.ZoneState.STATE_ON)
                if not ret:
                    _LOGGER.error("Error writing area state for area with ID: {}".format(zone_id))
                    return False
            _LOGGER.debug("clim mode ? {}".format(mode))
            # update clim mode
            ret = await self._client.async_set_area_clim_mode(id_zone = zone_id, val = mode)
            if not ret:
                _LOGGER.error("Error writing climate mode for area with ID: {}".format(zone_id))
                return False
            self._areas[_idx].clim_mode = mode
        return True

    async def async_set_area_fan_mode(self,
                                        zone_id:int, 
                                        mode:const.ZoneFanMode,
                                        ) -> bool:
        """ set fan mode for specific area """
        # test if area id is defined
        _ret, _idx = self._area_defined(id_search = zone_id)
        if not _ret:
            _LOGGER.error("Area not defined ...")
            return False

        if self._areas[_idx].state == const.ZoneState.STATE_OFF:
            _LOGGER.warning("Area state is off, cannot change fan speed ...")
            return False
        else:
            _LOGGER.debug("fan mode ? {}".format(mode))
            # writing new value to modbus
            ret = await self._client.async_set_area_fan_mode(id_zone = zone_id, val = mode)
            if not ret:
                _LOGGER.error("Error writing fan mode for area with ID: {}".format(zone_id))
                return False
            # update fan mode in list for specific area
            self._areas[_idx].fan_mode = mode
        return True

    def __repr__(self) -> str:
        ''' repr method '''
        return repr('System(Global Mode:{}, Efficiency:{}, State:{})'.format(
                        self._global_mode,
                        self._efficiency,
                        self._sys_state))

class NumUnitError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg

class FlowEngineError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg

class OrderTempError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg

class ClientNotConnectedError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg

class UpdateValueError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg

class InitialisationError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg
