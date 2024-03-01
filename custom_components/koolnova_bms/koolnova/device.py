""" local API to manage system, engines and areas """ 

import re, sys, os
import logging as log
import asyncio

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
        if val > 0 and (val > 30.0 or val < 15.0):
            raise OrderTempError('Flow Engine value ({}) must be between 15 and 30'.format(val))
        self._order_temp = val

    def __repr__(self) -> str:
        ''' repr method '''
        return repr('Unit(Id:{}, Throughput:{}, State:{}, Order Temp:{})'.format(self._engine_id,
                        self._throughput,
                        self._state,
                        self._order_temp))

class Koolnova:
    ''' koolnova Device class '''

    def __init__(self,
                    name:str = "",
                    port:str = "",
                    addr:int = const.DEFAULT_ADDR,
                    baudrate:int = const.DEFAULT_BAUDRATE,
                    parity:str = const.DEFAULT_PARITY,
                    bytesize:int = const.DEFAULT_BYTESIZE,
                    stopbits:int = const.DEFAULT_STOPBITS,
                    timeout:int = 1) -> None:
        ''' Class constructor '''
        self._client = Operations(port=port,
                                    addr=addr,
                                    baudrate=baudrate,
                                    parity=parity,
                                    bytesize=bytesize,
                                    stopbits=stopbits,
                                    timeout=timeout)
        self._name = name
        self._global_mode = const.GlobalMode.COLD
        self._efficiency = const.Efficiency.LOWER_EFF
        self._sys_state = const.SysState.SYS_STATE_OFF 
        self._engines = []
        self._areas = [] 

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
        _LOGGER.debug("Retreive system status ...")
        ret, self._sys_state = await self._client.async_system_status()
        if not ret:
            _LOGGER.error("Error retreiving system status")
            self._sys_state = const.SysState.SYS_STATE_OFF

        _LOGGER.debug("Retreive global mode ...")
        ret, self._global_mode = await self._client.async_global_mode()
        if not ret:
            _LOGGER.error("Error retreiving global mode")
            self._global_mode = const.GlobalMode.COLD

        _LOGGER.debug("Retreive efficiency ...")
        ret, self._efficiency = await self._client.async_efficiency()
        if not ret:
            _LOGGER.error("Error retreiving efficiency")
            self._efficiency = const.Efficiency.LOWER_EFF
        
        await asyncio.sleep(0.1)

        _LOGGER.debug("Retreive engines ...")
        for idx in range(1, const.NUM_OF_ENGINES + 1):
            engine = Engine(engine_id = idx)
            ret, engine.throughput = await self._client.async_engine_throughput(engine_id = idx)
            ret, engine.state = await self._client.async_engine_state(engine_id = idx)
            ret, engine.order_temp = await self._client.async_engine_order_temp(engine_id = idx)
            self._engines.append(engine)
            await asyncio.sleep(0.1)
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

    def get_area(self, zone_id:int = 0) -> Area:
        ''' get specific area '''
        return self._areas[zone_id - 1]

    async def async_update_area(self, zone_id:int = 0) -> bool:
        """ update specific area from zone_id """
        ret, infos = await self._client.async_area_registered(zone_id = zone_id)
        if not ret:
            _LOGGER.error("Error retreiving area ({}) values".format(zone_id))
            return ret, None
        for idx, area in enumerate(self._areas):
                if area.id_zone == zone_id:
                    # update areas list values from modbus response
                    self._areas[idx].state = infos['state']
                    self._areas[idx].register = infos['register']
                    self._areas[idx].fan_mode = infos['fan']
                    self._areas[idx].clim_mode = infos['clim']
                    self._areas[idx].real_temp = infos['real_temp']
                    self._areas[idx].order_temp = infos['order_temp']
                    break
        return ret, self._areas[zone_id - 1]

    async def async_update_all_areas(self) -> list:
        """ update all areas registered and all engines values """
        ##### Areas
        _ret, _vals = await self._client.async_areas_registered()
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

        ##### Engines
        for _idx in range(1, const.NUM_OF_ENGINES + 1):
            ret, self._engines[_idx - 1].throughput = await self._client.async_engine_throughput(engine_id = _idx)
            ret, self._engines[_idx - 1].state = await self._client.async_engine_state(engine_id = _idx)
            ret, self._engines[_idx - 1].order_temp = await self._client.async_engine_order_temp(engine_id = _idx)

        ##### Global mode
        ret, self._global_mode = await self._client.async_global_mode()
        if not ret:
            _LOGGER.error("Error retreiving global mode")
            self._global_mode = const.GlobalMode.COLD

        ##### Efficiency
        ret, self._efficiency = await self._client.async_efficiency()
        if not ret:
            _LOGGER.error("Error retreiving efficiency")
            self._efficiency = const.Efficiency.LOWER_EFF

        ##### Sys state
        ret, self._sys_state = await self._client.async_system_status()
        if not ret:
            _LOGGER.error("Error retreiving system status")
            self._sys_state = const.SysState.SYS_STATE_OFF

        return {"areas": self._areas, 
                "engines": self._engines,
                "glob": self._global_mode,
                "eff": self._efficiency,
                "sys": self._sys_state}

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
            "identifiers": {(DOMAIN, "deadbeef")},
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