""" local API to communicate with Koolnova BMS Modbus RTU client """

import re, sys, os
import logging as log

import asyncio

from pymodbus import pymodbus_apply_logging_config
from pymodbus.client import AsyncModbusSerialClient as ModbusClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse
from pymodbus.transaction import ModbusRtuFramer

from . import const

_LOGGER = log.getLogger(__name__)

class Operations:
    ''' koolnova BMS Modbus operations class '''

    def __init__(self, port:str, timeout:int) -> None:
        ''' Class constructor '''
        self._port = port
        self._timeout = timeout
        self._addr = const.DEFAULT_ADDR
        self._baudrate = const.DEFAULT_BAUDRATE
        self._parity = const.DEFAULT_PARITY
        self._bytesize = const.DEFAULT_BYTESIZE
        self._stopbits = const.DEFAULT_STOPBITS
        self._client = ModbusClient(port=self._port,
                                    baudrate=self._baudrate,
                                    parity=self._parity,
                                    stopbits=self._stopbits,
                                    bytesize=self._bytesize,
                                    timeout=self._timeout)

        pymodbus_apply_logging_config("DEBUG")

    def __init__(self, 
                    port:str="",
                    addr:int=const.DEFAULT_ADDR,
                    baudrate:int=const.DEFAULT_BAUDRATE,
                    parity:str=const.DEFAULT_PARITY,
                    stopbits:int=const.DEFAULT_STOPBITS,
                    bytesize:int=const.DEFAULT_BYTESIZE,
                    timeout:int=1) -> None:
        ''' Class constructor '''
        self._port = port
        self._addr = addr
        self._timeout = timeout
        self._baudrate = baudrate
        self._parity = parity
        self._bytesize = bytesize
        self._stopbits = stopbits
        self._client = ModbusClient(port=self._port,
                                    baudrate=self._baudrate,
                                    parity=self._parity,
                                    stopbits=self._stopbits,
                                    bytesize=self._bytesize,
                                    timeout=self._timeout)

        pymodbus_apply_logging_config("DEBUG")

    async def __read_register(self, reg:int) -> (int, bool):
        ''' Read one holding register (code 0x03) '''
        rr = None
        if not self._client.connected:
            raise ModbusConnexionError('Client Modbus not connected')
        try:
            _LOGGER.debug("reading holding register: {} - Addr: {}".format(hex(reg), self._addr))
            rr = await self._client.read_holding_registers(address=reg, count=1, slave=self._addr)
            if rr.isError():
                _LOGGER.error("reading holding register error")
                return None, False
        except Exception as e:
            _LOGGER.error("Modbus Error: {}".format(e))
            return None, False

        if isinstance(rr, ExceptionResponse):
            _LOGGER.error("Received modbus exception ({})".format(rr))
            return None, False
        elif not rr:
            _LOGGER.error("Response Null")
            return None, False
        return rr.registers[0], True

    async def __read_registers(self, start_reg:int, count:int) -> (int, bool):
        ''' Read holding registers (code 0x03) '''
        rr = None
        if not self._client.connected:
            raise ModbusConnexionError('Client Modbus not connected')
        try:
            rr = await self._client.read_holding_registers(address=start_reg, count=count, slave=self._addr)
            if rr.isError():
                _LOGGER.error("reading holding registers error")
                return None, False
        except Exception as e:
            _LOGGER.error("{}".format(e))
            return None, False

        if isinstance(rr, ExceptionResponse):
            _LOGGER.error("Received modbus exception ({})".format(rr))
            return None, False
        elif not rr:
            _LOGGER.error("Response Null")
            return None, False
        return rr.registers, True

    async def __write_register(self, reg:int, val:int) -> bool:
        ''' Write one register (code 0x06) '''
        rq = None
        ret = True
        if not self._client.connected:
            raise ModbusConnexionError('Client Modbus not connected')
        try:
            _LOGGER.debug("writing single register: {} - Addr: {} - Val: {}".format(hex(reg), self._addr, hex(val)))
            rq = await self._client.write_register(address=reg, value=val, slave=self._addr)
            if rq.isError():
                _LOGGER.error("writing register error")
                return False
        except Exception as e:
            _LOGGER.error("{}".format(e))
            return False

        if isinstance(rq, ExceptionResponse):
            _LOGGER.error("Received modbus exception ({})".format(rr))
            return False
        return ret 

    async def connect(self) -> None:
        ''' connect to the modbus serial server '''
        await self._client.connect()

    def connected(self) -> bool:
        ''' get modbus client status '''
        return self._client.connected

    def disconnect(self) -> None:
        ''' close the underlying socket connection '''
        if self._client.connected:
            self._client.close()

    async def discover_registered_zones(self) -> list:
        ''' Discover all zones registered to the system '''
        regs, ret = await self.__read_registers(start_reg=const.REG_START_ZONE, 
                                                count=const.NB_ZONE_MAX * const.NUM_REG_PER_ZONE)
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

    async def zone_registered(self,
                                zone_id:int = 0,
                                ) -> (bool, dict):
        ''' Get Zone Status from Id '''
        _LOGGER.debug("Area : {}".format(zone_id))
        if zone_id > const.NB_ZONE_MAX or zone_id == 0:
            raise ZoneIdError('Zone Id must be between 1 to {}'.format(const.NB_ZONE_MAX))
        zone_dict = {}
        regs, ret = await self.__read_registers(start_reg = const.REG_START_ZONE + (4 * (zone_id - 1)), 
                                                count = const.NUM_REG_PER_ZONE)
        if not ret:
            raise ReadRegistersError("Read holding regsiter error")
        if const.ZoneRegister(regs[0] >> 1) == const.ZoneRegister.REGISTER_OFF:
            _LOGGER.warning("Zone with id: {} is not registered".format(zone_id))
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
            _LOGGER.error('Error retreive system status')
            reg = 0
        return ret, const.SysState(reg)

    async def set_system_status(self,
                                opt:const.SysState,
                                ) -> bool:
        ''' Write system status '''
        ret = await self.__write_register(reg = const.REG_SYS_STATE, val = int(opt))
        if not ret:
            _LOGGER.error('Error writing system status')
        return ret

    async def global_mode(self) -> (bool, const.GlobalMode):
        ''' Read global mode '''
        reg, ret = await self.__read_register(const.REG_GLOBAL_MODE)
        if not ret:
            _LOGGER.error('Error retreive global mode')
            reg = 0
        return ret, const.GlobalMode(reg)

    async def set_global_mode(self,
                                opt:const.GlobalMode,
                                ) -> bool:
        ''' Write global mode '''
        ret = await self.__write_register(reg = const.REG_GLOBAL_MODE, val = int(opt))
        if not ret:
            _LOGGER.error('Error writing global mode')
        return ret

    async def efficiency(self) -> (bool, const.Efficiency):
        ''' read efficiency/speed '''
        reg, ret = await self.__read_register(const.REG_EFFICIENCY)
        if not ret:
            _LOGGER.error('Error retreive efficiency')
            reg = 0
        return ret, const.Efficiency(reg)

    async def set_efficiency(self,
                                opt:const.GlobalMode,
                            ) -> bool:
        ''' Write efficiency '''
        ret = await self.__write_register(reg = const.REG_EFFICIENCY, val = int(opt))
        if not ret:
            _LOGGER.error('Error writing efficiency')
        return ret

    async def flow_engines(self) -> (bool, list):
        ''' read flow engines AC1, AC2, AC3, AC4 '''
        engines_lst = []
        regs, ret = await self.__read_registers(const.REG_START_FLOW_ENGINE,
                                                const.NUM_OF_ENGINES)
        if ret:
            for idx, reg in enumerate(regs):
                engines_lst.append(const.FlowEngine(reg))
        else:
            _LOGGER.error('Error retreive flow engines')
        return ret, engines_lst

    async def flow_engine(self,
                            unit_id:int = 0,
                            ) -> (bool, int):
        ''' read flow unit specified by unit id '''
        if unit_id < 1 or unit_id > 4:
            raise UnitIdError("Unit Id must be between 1 and 4")
        reg, ret = await self.__read_register(const.REG_START_FLOW_ENGINE + (unit_id - 1))
        if not ret:
            _LOGGER.error('Error retreive flow engine for id:{}'.format(unit_id))
            reg = 0
        return ret, reg

    async def flow_state_engine(self,
                                unit_id:int = 0,
                                ) -> (bool, const.FlowEngine):
        if unit_id < 1 or unit_id > 4:
            raise UnitIdError("Unit Id must be between 1 and 4")
        reg, ret = await self.__read_register(const.REG_START_FLOW_STATE_ENGINE + (unit_id - 1))
        if not ret:
            _LOGGER.error('Error retreive flow state for id:{}'.format(unit_id))
            reg = 0
        return ret, const.FlowEngine(reg)

    async def order_temp_engine(self,
                                unit_id:int = 0,
                                ) -> (bool, float):
        if unit_id < 1 or unit_id > 4:
            raise UnitIdError("Unit Id must be between 1 and 4")
        reg, ret = await self.__read_register(const.REG_START_ORDER_TEMP + (unit_id - 1))
        if not ret:
            _LOGGER.error('Error retreive order temp for id:{}'.format(unit_id))
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
            _LOGGER.error('error reading flow engines registers')
        return ret, engines_lst

    async def set_area_target_temp(self,
                                    zone_id:int = 0,
                                    val:float = 0.0,
                                    ) -> bool:
        ''' Set area target temperature '''
        if zone_id > const.NB_ZONE_MAX or zone_id == 0:
            raise ZoneIdError('Zone Id must be between 1 to 16')
        if val > const.MAX_TEMP_ORDER or val < const.MIN_TEMP_ORDER:
            _LOGGER.error('Order Temperature must be between {} and {}'.format(const.MIN_TEMP_ORDER, const.MAX_TEMP_ORDER))
            return False
        ret = await self.__write_register(reg = const.REG_START_ZONE + (4 * (zone_id - 1)) + const.REG_TEMP_ORDER, val = int(val * 2))
        if not ret:
            _LOGGER.error('Error writing zone order temperature')

        return ret

    async def area_temp(self,
                        id_zone:int = 0,
                        ) -> (bool, float):
        """ get temperature of specific area id """
        reg, ret = await self.__read_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_TEMP_REAL)
        if not ret:
            _LOGGER.error('Error retreive area real temp')
            reg = 0
        return ret, reg / 2

    async def area_target_temp(self,
                                id_zone:int = 0,
                                ) -> (bool, float):
        """ get target temperature of specific area id """
        reg, ret = await self.__read_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_TEMP_ORDER)
        if not ret:
            _LOGGER.error('Error retreive area target temp')
            reg = 0
        return ret, reg / 2

    async def area_clim_and_fan_mode(self, 
                                        id_zone:int = 0,
                                    ) -> (bool, const.ZoneFanMode, const.ZoneClimMode):
        """ get climate and fan mode of specific area id """
        reg, ret = await self.__read_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_STATE_AND_FLOW)
        if not ret:
            _LOGGER.error('Error retreive area fan and climate values')
            reg = 0
        return ret, const.ZoneFanMode((reg & 0xF0) >> 4), const.ZoneClimMode(reg & 0x0F)

    async def area_state_and_register(self,
                                        id_zone:int = 0,
                                    ) -> (bool, const.ZoneRegister, const.ZoneState):
        """ get area state and register """
        reg, ret = await self.__read_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_LOCK_ZONE)
        if not ret:
            _LOGGER.error('Error retreive area register value')
            reg = 0
        return ret, const.ZoneRegister(reg >> 1), const.ZoneState(reg & 0b01)

    async def set_area_state(self,
                                id_zone:int = 0,
                                val:const.ZoneState = const.ZoneState.STATE_OFF,
                            ) -> bool:
        """ set area state """
        register:const.ZoneRegister = const.ZoneRegister.REGISTER_OFF
        if id_zone > const.NB_ZONE_MAX or id_zone == 0:
            raise ZoneIdError('Zone Id must be between 1 to 16')
        # retreive values to combine the new state with register read
        ret, register, _ = await self.area_state_and_register(id_zone = id_zone)
        if not ret:
            _LOGGER.error("Error reading state and register mode")
            return ret
        _LOGGER.debug("register & state: {}".format(hex((int(register) << 1) | (int(val) & 0b01))))
        ret = await self.__write_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_LOCK_ZONE,
                                            val = int(int(register) << 1) | (int(val) & 0b01))
        if not ret:
            _LOGGER.error('Error writing area state value')

        return True

    async def set_area_clim_mode(self,
                                    id_zone:int = 0,
                                    val:const.ZoneClimMode = const.ZoneClimMode.OFF,
                                ) -> bool:
        """ set area clim mode """
        fan:const.ZoneFanMode = const.ZoneFanMode.FAN_OFF
        if id_zone > const.NB_ZONE_MAX or id_zone == 0:
            raise ZoneIdError('Zone Id must be between 1 to 16')
        # retreive values to combine the new climate mode with fan mode read
        ret, fan, _ = await self.area_clim_and_fan_mode(id_zone = id_zone)
        if not ret:
            _LOGGER.error("Error reading fan and clim mode")
            return ret
        _LOGGER.debug("Fan & Clim: {}".format(hex((int(fan) << 4) | (int(val) & 0x0F))))
        ret = await self.__write_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_STATE_AND_FLOW,
                                            val = int(int(fan) << 4) | (int(val) & 0x0F))
        if not ret:
            _LOGGER.error('Error writing area climate mode')

        return ret

    async def set_area_fan_mode(self,
                                    id_zone:int = 0,
                                    val:const.ZoneFanMode = const.ZoneFanMode.FAN_OFF,
                                ) -> bool:
        """ set area fan mode """
        clim:const.ZoneClimMode = const.ZoneClimMode.OFF
        if id_zone > const.NB_ZONE_MAX or id_zone == 0:
            raise ZoneIdError('Zone Id must be between 1 to 16')
        # retreive values to combine the new fan mode with climate mode read
        ret, _, clim = await self.area_clim_and_fan_mode(id_zone = id_zone)
        if not ret:
            _LOGGER.error("Error reading fan and clim mode")
            return ret
        _LOGGER.debug("Fan & Clim: {}".format(hex((int(val) << 4) | (int(clim) & 0x0F))))
        ret = await self.__write_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_STATE_AND_FLOW,
                                            val = int(int(val) << 4) | (int(clim) & 0x0F))
        if not ret:
            _LOGGER.error('Error writing area fan mode')
        return ret

    @property
    def port(self) -> str:
        ''' Get Port '''
        return self._port

    @property
    def address(self) -> str:
        ''' Get address '''
        return self._addr

    @property
    def baudrate(self) -> str:
        ''' Get baudrate '''
        return self._baudrate

    @property
    def parity(self) -> str:
        ''' Get parity '''
        return self._parity

    @property
    def bytesize(self) -> str:
        ''' Get bytesize '''
        return self._bytesize

    @property
    def stopbits(self) -> str:
        ''' Get stopbits '''
        return self._stopbits

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
