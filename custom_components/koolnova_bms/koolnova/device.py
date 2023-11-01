#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# @author: sinseman44 <vincent.benoit@benserv.fr>
# @date: 10/2023
# @brief: System, Unit and Zone classes 

###########################################################################
#         import external modules

import re, sys, os
import logging as log
import asyncio

###########################################################################
#         import internal modules

from . import const
from .operations import Operations, ModbusConnexionError

###########################################################################
#         class & methods

logger = log.getLogger('koolnova_bms')

class Koolnova:
    ''' koolnova Device class '''

    def __init__(self,
                 port:str = "", 
                 timeout:int = 0,
                ) -> None:
        ''' Class constructor '''
        self._client = Operations(port=port, timeout=timeout)
        self._global_mode = const.GlobalMode.COLD
        self._efficiency = const.Efficiency.LOWER_EFF
        self._sys_state = const.SysState.SYS_STATE_OFF 
        self._units = []
        self._zones = [] 

    async def connect(self) -> bool:
        ''' connect to the modbus serial server '''
        await self._client.connect()
        if not self.connected():
            raise ClientNotConnectedError("Client Modbus connexion error")

        logger.info("Retreive system status ...")
        ret, self._sys_state = await self._client.system_status()
        if not ret:
            logger.error("Error retreiving system status")
            self._sys_state = const.SysState.SYS_STATE_OFF

        logger.info("Retreive global mode ...")
        ret, self._global_mode = await self._client.global_mode()
        if not ret:
            logger.error("Error retreiving global mode")
            self._global_mode = const.GlobalMode.COLD

        logger.info("Retreive efficiency ...")
        ret, self._efficiency = await self._client.efficiency()
        if not ret:
            logger.error("Error retreiving efficiency")
            self._efficiency = const.Efficiency.LOWER_EFF
        
        await asyncio.sleep(0.5)

        logger.info("Retreive units ...")
        for idx in range(1, const.NUM_OF_ENGINES + 1):
            logger.debug("Unit id: {}".format(idx))
            unit = Unit(unit_id = idx)
            ret, unit.flow_engine = await self._client.flow_engine(unit_id = idx)
            ret, unit.flow_state = await self._client.flow_state_engine(unit_id = idx)
            ret, unit.order_temp = await self._client.order_temp_engine(unit_id = idx)
            self._units.append(unit)
            await asyncio.sleep(0.5)
            
        return True

    def connected(self) -> bool:
        ''' get modbus client status '''
        return self._client.connected

    def disconnect(self) -> None:
        ''' close the underlying socket connection '''
        self._client.disconnect()

    async def discover_zones(self) -> None:
        ''' Set all registered zones for system '''
        if not self._client.connected:
            raise ModbusConnexionError('Client Modbus not connected')
        zones_lst = await self._client.discover_registered_zones()
        for zone in zones_lst:
            self._zones.append(Zone(id_zone = zone['id'],
                                    state = zone['state'],
                                    register = zone['register'],
                                    fan_mode = zone['fan'],
                                    clim_mode = zone['clim'],
                                    real_temp = zone['real_temp'],
                                    order_temp = zone['order_temp']
                                   ))
        return

    async def add_manual_registered_zone(self,
                                         id_zone:int = 0) -> bool:
        ''' Add zone to koolnova System '''
        if not self._client.connected:
            raise ModbusConnexionError('Client Modbus not connected')

        ret, zone_dict = await self._client.zone_registered(zone_id = id_zone)
        if not ret:
            logger.error("Zone with ID: {} is not registered".format(id_zone))
            return False
        for zone in self._zones:
            if id_zone == zone.id_zone:
                logger.error('Zone registered with ID: {} is already saved')
                return False
        
        self._zones.append(Zone(id_zone = id_zone,
                                state = zone_dict['state'],
                                register = zone_dict['register'],
                                fan_mode = zone_dict['fan'],
                                clim_mode = zone_dict['clim'],
                                real_temp = zone_dict['real_temp'],
                                order_temp = zone_dict['order_temp']
                               ))
        logger.debug("Zones registered: {}".format(self._zones))
        return True

    def get_zones(self) -> list:
        ''' get zones '''
        return self._zones

    def get_zone(self, zone_id:int = 0) -> str:
        ''' get specific zone '''
        return self._zones[zone_id - 1]

    def get_units(self) -> list:
        ''' get units '''
        return self._units

    @property
    def global_mode(self) -> const.GlobalMode:
        ''' Get Global Mode '''
        return self._global_mode

    @global_mode.setter
    def global_mode(self, val:const.GlobalMode) -> None:
        ''' Set Global Mode '''
        if not isinstance(val, const.GlobalMode):
            raise AssertionError('Input variable must be Enum GlobalMode')
        self._global_mode = val

    @property
    def efficiency(self) -> const.Efficiency:
        ''' Get Efficiency '''
        return self._efficiency

    @efficiency.setter
    def efficiency(self, val:const.Efficiency) -> None:
        ''' Set Efficiency '''
        if not isinstance(val, const.Efficiency):
            raise AssertionError('Input variable must be Enum Efficiency')
        self._efficiency = val

    @property
    def sys_state(self) -> const.SysState:
        ''' Get System State '''
        return self.sys_state

    @sys_state.setter
    def sys_state(self, val:const.SysState) -> None:
        ''' Set System State '''
        if not isinstance(val, const.SysState):
            raise AssertionError('Input variable must be Enum SysState')
        self._sys_state = val

    def __repr__(self) -> str:
        ''' repr method '''
        return repr('System(Global Mode:{}, Efficiency:{}, State:{})'.format(           self._global_mode,self._efficiency,self._sys_state))

class Unit:
    ''' koolnova Unit class '''

    def __init__(self,
                 unit_id:int = 0,
                 flow_engine:int = 0,
                 flow_state:const.FlowEngine = const.FlowEngine.AUTO,
                 order_temp:float = 0
                ) -> None:
        ''' Constructor class '''
        self._unit_id = unit_id
        self._flow_engine = flow_engine
        self._flow_state = flow_state
        self._order_temp = order_temp

    @property
    def unit_id(self) -> int:
        ''' Get Unit ID '''
        return self._unit_id

    @unit_id.setter
    def unit_id(self, val:int) -> None:
        ''' Set Unit ID '''
        if not isinstance(val, int):
            raise AssertionError('Input variable must be Int')
        if val > const.NUM_OF_ENGINES:
            raise NumUnitError('Unit ID must be lower than {}'.format(const.NUM_OF_ENGINES))
        self._unit_id = val

    @property
    def flow_engine(self) -> int:
        ''' Get Flow Engine '''
        return self._flow_engine

    @flow_engine.setter
    def flow_engine(self, val:int) -> None:
        ''' Set Flow Engine '''
        if not isinstance(val, int):
            raise AssertionError('Input variable must be Int')
        if val > const.FLOW_ENGINE_VAL_MAX or val < const.FLOW_ENGINE_VAL_MIN:
            raise FlowEngineError('Flow Engine value ({}) must be between {} and {}'.format(val, const.FLOW_ENGINE_VAL_MIN, const.FLOW_ENGINE_VAL_MAX))
        self._flow_engine = val

    @property
    def flow_state(self) -> const.FlowEngine:
        ''' Get Flow State '''
        return self._flow_state

    @flow_state.setter
    def flow_state(self, val:const.FlowEngine) -> None:
        ''' Set Flow State '''
        if not isinstance(val, const.FlowEngine):
            raise AssertionError('Input variable must be Enum FlowEngine')
        self._flow_state = val

    @property
    def order_temp(self) -> float:
        ''' Get Order Temp '''
        return self._order_temp

    @order_temp.setter
    def order_temp(self, val:float = 0.0) -> None:
        ''' Set Flow Engine '''
        if not isinstance(val, float):
            raise AssertionError('Input variable must be Int')
        if val > 0 and (val > 30.0 or val < 15.0):
            raise OrderTempError('Flow Engine value ({}) must be between 15 and 30'.format(val))
        self._flow_engine = val

    def __repr__(self) -> str:
        ''' repr method '''
        return repr('Unit(Id:{}, Flow Engine:{}, Flow State:{}, Order Temp:{})'.format(self._unit_id,
          self._flow_engine,
          self._flow_state,
          self._order_temp))

class Zone:
    ''' koolnova Zone class '''

    def __init__(self,
                 id_zone:int = 0,
                 state:const.ZoneState = const.ZoneState.STATE_OFF,
                 register:const.ZoneRegister = const.ZoneRegister.REGISTER_OFF,
                 fan_mode:const.ZoneFanMode = const.ZoneFanMode.FAN_OFF,
                 clim_mode:const.ZoneClimMode = const.ZoneClimMode.COLD,
                 real_temp:float = 0,
                 order_temp:float = 0
                ) -> None:
        ''' Class constructor '''
        self._id = id_zone
        self._state = state
        self._register = register
        self._fan_mode = fan_mode
        self._clim_mode = clim_mode
        self._real_temp = real_temp
        self._order_temp = order_temp

    @property
    def id_zone(self) -> int:
        ''' Get Zone Id '''
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
        return repr('Zone(Id:{}, State:{}, Register:{}, Fan:{}, Clim:{}, Real Temp:{}, Order Temp:{})'.format(self._id, 
                        self._state,
                        self._register,
                        self._fan_mode,
                        self._clim_mode,
                        self._real_temp,
                        self._order_temp))

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

