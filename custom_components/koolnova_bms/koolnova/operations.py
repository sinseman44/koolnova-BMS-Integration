#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# @author: sinseman44 <vincent.benoit@benserv.fr>
# @date: 10/2023
# @brief: Communicate with Koolnova BMS Modbus RTU

###########################################################################
#         import external modules

import re, sys, os
import logging as log

import asyncio

from pymodbus import pymodbus_apply_logging_config
from pymodbus.client import AsyncModbusSerialClient as ModbusClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse
from pymodbus.transaction import ModbusRtuFramer

###########################################################################
#         import internal modules

from . import const

###########################################################################
#         class & methods

logger = log.getLogger('koolnova_bms')

class Operations:
    ''' koolnova BMS Modbus operations class '''

    def __init__(self, port:str, timeout:int) -> None:
        ''' Class constructor '''
        self._port = port
        self._timeout = timeout
        self._client = ModbusClient(port=self._port, 
                                    baudrate=const.DEFAULT_BAUDRATE, 
                                    parity=const.DEFAULT_PARITY, 
                                    stopbits=const.DEFAULT_STOPBITS, 
                                    bytesize=const.DEFAULT_BYTESIZE, 
                                    timeout=self._timeout)
        pymodbus_apply_logging_config("DEBUG")

    async def __read_register(self, reg:int) -> (int, bool):
        ''' Read one holding register (code 0x03) '''
        ret = True
        rr = None
        if not self._client.connected:
            raise ModbusConnexionError('Client Modbus not connected')
        try:
            rr = await self._client.read_holding_registers(address=reg, count=1, slave=const.DEFAULT_ADDR)
            if rr.isError():
                ret = False
        except ModbusException as e:
            logger.error("{}".format(e))
            ret = False

        if isinstance(rr, ExceptionResponse):
            logger.error("Received modbus exception ({})".format(rr))
            ret = False
        return rr.registers[0], ret

    async def __read_registers(self, start_reg:int, count:int) -> (int, bool):
        ''' Read holding registers (code 0x03) '''
        ret = True
        rr = None
        if not self._client.connected:
            raise ModbusConnexionError('Client Modbus not connected')
        try:
            rr = await self._client.read_holding_registers(address=start_reg, count=count, slave=const.DEFAULT_ADDR)
            if rr.isError():
                ret = False
        except ModbusException as e:
            logger.error("{}".format(e))
            ret = False

        if isinstance(rr, ExceptionResponse):
            logger.error("Received modbus exception ({})".format(rr))
            ret = False
        return rr.registers, ret

    async def __write_register(self, reg:int, val:int) -> bool:
        ''' Write one register (code 0x06) '''
        rq = None
        ret = True
        if not self._client.connected:
            raise ModbusConnexionError('Client Modbus not connected')
        try:
            rq = await self._client.write_register(address=reg, value=val, slave=const.DEFAULT_ADDR)
            if rq.isError():
                logger.error("Write error: {}".format(rq))
                ret = False
        except ModbusException as e:
            logger.error("{}".format(e))
            ret = False

        if isinstance(rq, ExceptionResponse):
            logger.error("Received modbus exception ({})".format(rr))
            ret = False
        return ret 

    async def connect(self) -> None:
        ''' connect to the modbus serial server '''
        await self._client.connect()

    def connected(self) -> bool:
        ''' get modbus client status '''
        return self._client.connected

    def disconnect(self) -> None:
        ''' close the underlying socket connection '''
        self._client.close()

    async def discover_registered_zones(self) -> list:
        ''' Discover all zones registered to the system '''
        regs, ret = await self.__read_registers(start_reg=const.REG_START_ZONE, count=const.NB_ZONE_MAX * const.NUM_REG_PER_ZONE)
        if not ret:
            raise ReadRegistersError("Read holding regsiter error")
        zones_lst = []
        zone_dict = {}
        jdx = 1
        flag = False
        for idx, reg in enumerate(regs):
            if idx % const.NUM_REG_PER_ZONE == 0:
                zone_dict = {}
                if const.ZoneRegister(reg >> 1) == const.ZoneRegister.REGISTER_ON:
                    zone_dict['id'] = jdx
                    zone_dict['state'] = const.ZoneState(reg & 0b01)
                    zone_dict['register'] = const.ZoneRegister(reg >> 1)
                    flag = True
            elif idx % const.NUM_REG_PER_ZONE == 1 and flag:
                zone_dict['fan'] = const.ZoneFanMode((reg & 0xF0) >> 4)
                zone_dict['clim'] = const.ZoneClimMode(reg & 0x0F)
            elif idx % const.NUM_REG_PER_ZONE == 2 and flag:
                zone_dict['order_temp'] = reg/2
            elif idx % const.NUM_REG_PER_ZONE == 3 and flag:
                zone_dict['real_temp'] = reg/2
                jdx += 1
                flag = False
                zones_lst.append(zone_dict)
        return zones_lst

    async def zone_registered(self, zone_id:int = 0) -> (bool, dict):
        ''' Get Zone Status from Id '''
        if zone_id > const.NB_ZONE_MAX or zone_id == 0:
            raise ZoneIdError('Zone Id must be between 1 to 16')
        zone_dict = {}
        regs, ret = await self.__read_registers(start_reg = const.REG_START_ZONE + (4 * (zone_id - 1)), count = const.NUM_REG_PER_ZONE)
        if not ret:
            raise ReadRegistersError("Read holding regsiter error")
        if const.ZoneRegister(regs[0] >> 1) == const.ZoneRegister.REGISTER_OFF:
            return False, {}

        zone_dict['state'] = const.ZoneState(regs[0] & 0b01)
        zone_dict['register'] = const.ZoneRegister(regs[0] >> 1)
        zone_dict['fan'] = const.ZoneFanMode((regs[1] & 0xF0) >> 4)
        zone_dict['clim'] = const.ZoneClimMode(regs[1] & 0x0F)
        zone_dict['order_temp'] = regs[2]/2
        zone_dict['real_temp'] = regs[3]/2
        return True, zone_dict

    async def system_status(self) -> (bool, const.SysState):
        ''' Read system status register '''
        reg, ret = await self.__read_register(const.REG_SYS_STATE)
        if not ret:
            logger.error('Error retreive system status')
            reg = 0
        return ret, const.SysState(reg)

    async def global_mode(self) -> (bool, const.GlobalMode):
        ''' Read global mode '''
        reg, ret = await self.__read_register(const.REG_GLOBAL_MODE)
        if not ret:
            logger.error('Error retreive global mode')
            reg = 0
        return ret, const.GlobalMode(reg)
    
    async def efficiency(self) -> (bool, const.Efficiency):
        ''' read efficiency/speed '''
        reg, ret = await self.__read_register(const.REG_EFFICIENCY)
        if not ret:
            logger.error('Error retreive efficiency')
            reg = 0
        return ret, const.Efficiency(reg)

    async def flow_engines(self) -> (bool, list):
        ''' read flow engines AC1, AC2, AC3, AC4 '''
        engines_lst = []
        regs, ret = await self.__read_registers(const.REG_START_FLOW_ENGINE, const.NUM_OF_ENGINES)
        if ret:
            for idx, reg in enumerate(regs):
                engines_lst.append(const.FlowEngine(reg))
        else:
            logger.error('Error retreive flow engines')
        return ret, engines_lst

    async def flow_engine(self, unit_id:int = 0) -> (bool, int):
        ''' read flow unit specified by unit id '''
        if unit_id < 1 or unit_id > 4:
            raise UnitIdError("Unit Id must be between 1 and 4")
        reg, ret = await self.__read_register(const.REG_START_FLOW_ENGINE + (unit_id - 1))
        if not ret:
            logger.error('Error retreive flow engine for id:{}'.format(unit_id))
            reg = 0
        return ret, reg

    async def flow_state_engine(self, unit_id:int = 0) -> (bool, const.FlowEngine):
        if unit_id < 1 or unit_id > 4:
            raise UnitIdError("Unit Id must be between 1 and 4")
        reg, ret = await self.__read_register(const.REG_START_FLOW_STATE_ENGINE + (unit_id - 1))
        if not ret:
            logger.error('Error retreive flow state for id:{}'.format(unit_id))
            reg = 0
        return ret, const.FlowEngine(reg)

    async def order_temp_engine(self, unit_id:int = 0) -> (bool, float):
        if unit_id < 1 or unit_id > 4:
            raise UnitIdError("Unit Id must be between 1 and 4")
        reg, ret = await self.__read_register(const.REG_START_ORDER_TEMP + (unit_id - 1))
        if not ret:
            logger.error('Error retreive order temp for id:{}'.format(unit_id))
            reg = 0
        return ret, reg / 2

    async def orders_temp(self) -> (bool, list):
        ''' read orders temperature AC1, AC2, AC3, AC4 '''
        engines_lst = []
        regs, ret = await self.__read_registers(const.REG_START_ORDER_TEMP, const.NUM_OF_ENGINES)
        if ret:
            for idx, reg in enumerate(regs):
                engines_lst.append(reg/2)
        else:
            logger.error('error reading flow engines registers')
        return ret, engines_lst

    async def set_zone_order_temp(self, zone_id:int = 0, val:float = 0.0) -> bool:
        ''' Set zone order temp '''
        if zone_id > const.NB_ZONE_MAX or zone_id == 0:
            raise ZoneIdError('Zone Id must be between 1 to 16')
        if val > const.MAX_TEMP_ORDER or val < const.MIN_TEMP_ORDER:
            logger.error('Order Temperature must be between {} and {}'.format(const.MIN_TEMP_ORDER, const.MAX_TEMP_ORDER))
            return False
        ret = await self.__write_register(reg = const.REG_START_ZONE + (4 * (zone_id - 1)) + const.REG_TEMP_ORDER, val = int(val * 2))
        if not ret:
            logger.error('Error writing zone order temperature')

        return ret

    @property
    def port(self) -> str:
        ''' Get Port '''
        return self._port

    @property
    def timeout(self) -> int:
        ''' Get Timeout '''
        return self._timeout

class ModbusConnexionError(Exception):
    ''' user defined exception '''

    def __init__(self,
                 msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg

class ReadRegistersError(Exception):
    ''' user defined exception '''

    def __init__(self,
                 msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg

class ZoneIdError(Exception):
    ''' user defined exception '''

    def __init__(self,
                 msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg

class UnitIdError(Exception):
    ''' user defined exception '''

    def __init__(self,
                 msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg
