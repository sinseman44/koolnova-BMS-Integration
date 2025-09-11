""" local API to communicate with Koolnova BMS Modbus RTU client """

import re, sys, os
import logging as log

import asyncio

from pymodbus import pymodbus_apply_logging_config
from pymodbus.client import AsyncModbusSerialClient as ModbusClient
from pymodbus.client import AsyncModbusTcpClient as ModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse
from pymodbus.framer.rtu import FramerRTU

from . import const

_LOGGER = log.getLogger(__name__)

class Operations:
    ''' koolnova BMS Modbus operations class '''

    _rtu_port:str = ""
    _rtu_addr:int = const.DEFAULT_ADDR
    _rtu_baudrate = const.DEFAULT_BAUDRATE
    _rtu_parity = const.DEFAULT_PARITY
    _rtu_bytesize = const.DEFAULT_BYTESIZE
    _rtu_stopbits = const.DEFAULT_STOPBITS
    _tcp_port:int = const.DEFAULT_TCP_PORT
    _tcp_addr:str = const.DEFAULT_TCP_ADDR
    _tcp_modbus:int=const.DEFAULT_ADDR
    _tcp_retries:int=const.DEFAULT_TCP_RETRIES
    _tcp_reco_delay_min:float=const.DEFAULT_TCP_RECO_DELAY
    _tcp_reco_delay_max:float=const.DEFAULT_TCP_RECO_DELAY_MAX
    _lock = asyncio.Lock()

    def __init__(self, mode:str, timeout:int, debug:bool=False, **kwargs) -> None:
        ''' Class constructor '''
        self._mode = mode
        self._timeout = timeout
        self._debug = debug
        self.__dict__.update(kwargs)
        _LOGGER.debug("[OPERATION] dict: {}".format(self.__dict__))
        if self._mode == 'Modbus RTU':
            self._addr = kwargs.get('addr', const.DEFAULT_ADDR)
            self._rtu_port = kwargs.get('port', "")
            self._rtu_baudrate = kwargs.get('baudrate', const.DEFAULT_BAUDRATE)
            self._rtu_parity = kwargs.get('parity', const.DEFAULT_PARITY)
            self._rtu_bytesize = kwargs.get('bytesize', const.DEFAULT_BYTESIZE)
            self._rtu_stopbits = kwargs.get('stopbits', const.DEFAULT_STOPBITS)
            self._client = ModbusClient(port=self._rtu_port,
                                        baudrate=self._rtu_baudrate,
                                        parity=self._rtu_parity,
                                        stopbits=self._rtu_stopbits,
                                        bytesize=self._rtu_bytesize,
                                        timeout=self._timeout)
        elif self._mode == 'Modbus TCP':
            self._tcp_port = kwargs.get('port',const.DEFAULT_TCP_PORT)
            self._tcp_addr = kwargs.get('addr',const.DEFAULT_TCP_ADDR)
            self._addr = kwargs.get('modbus',const.DEFAULT_ADDR) # Modbus slave ID for the operations
            self._tcp_retries = kwargs.get('retries',const.DEFAULT_TCP_RETRIES)
            self._tcp_reco_delay_min = kwargs.get('reco_delay_min',const.DEFAULT_TCP_RECO_DELAY)
            self._tcp_reco_delay_max = kwargs.get('reco_delay_max',const.DEFAULT_TCP_RECO_DELAY_MAX)
            self._client = ModbusTcpClient(host=self._tcp_addr,
                                            port=self._tcp_port,
                                            name="koolnovaTCP",
                                            retries=self._tcp_retries,
                                            reconnect_delay=self._tcp_reco_delay_min,
                                            reconnect_delay_max=self._tcp_reco_delay_max,
                                            timeout=self._timeout)
        else:
            raise InitialisationError('Mode ({}) not defined'.format(self._mode))
        if self._debug:
            pymodbus_apply_logging_config("DEBUG")

    async def __async_read_register(self, reg:int) -> (int, bool):
        ''' Read one holding register (code 0x03) '''
        async with Operations._lock:
            rr = None
            if not self._client.connected:
                raise ModbusConnexionError('Client Modbus not connected')
            try:
                await asyncio.sleep(0.3)
                _LOGGER.debug("reading holding register: {} - Slave: {}".format(hex(reg), self._addr))
                rr = await self._client.read_holding_registers(address=reg, count=1, device_id=self._addr)
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

    async def __async_read_registers(self, start_reg:int, count:int) -> (int, bool):
        ''' Read holding registers (code 0x03) '''
        async with Operations._lock:
            rr = None
            if not self._client.connected:
                raise ModbusConnexionError('Client Modbus not connected')
            try:
                await asyncio.sleep(0.3)
                _LOGGER.debug("reading holding registers: {} - count: {} - Slave: {}".format(hex(start_reg), count, self._addr))
                rr = await self._client.read_holding_registers(address=start_reg, count=count, device_id=self._addr)
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

    async def __async_write_register(self, reg:int, val:int) -> bool:
        ''' Write one register (code 0x06) '''
        async with Operations._lock:
            rq = None
            ret = True
            if not self._client.connected:
                raise ModbusConnexionError('Client Modbus not connected')
            try:
                await asyncio.sleep(0.3)
                _LOGGER.debug("writing single register: {} - Slave: {} - Val: {}".format(hex(reg), self._addr, hex(val)))
                rq = await self._client.write_register(address=reg, value=val, device_id=self._addr)
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

    async def async_connect(self) -> None:
        ''' connect to the modbus serial server '''
        async with Operations._lock:
            await self._client.connect()

    def connected(self) -> bool:
        ''' get modbus client status '''
        return self._client.connected

    def disconnect(self) -> None:
        ''' close the underlying socket connection '''
        if self._client.connected:
            self._client.close()

    async def async_discover_registered_areas(self) -> list:
        ''' Discover all areas registered to the system '''
        regs, ret = await self.__async_read_registers(start_reg=const.REG_START_ZONE, 
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

    async def async_area_registered(self,
                                    zone_id:int = 0,
                                    ) -> (bool, dict):
        ''' Get Area status from id '''
        #_LOGGER.debug("Area : {}".format(zone_id))
        if zone_id > const.NB_ZONE_MAX or zone_id == 0:
            raise ZoneIdError('Zone Id must be between 1 to {}'.format(const.NB_ZONE_MAX))
        zone_dict = {}
        regs, ret = await self.__async_read_registers(start_reg = const.REG_START_ZONE + (4 * (zone_id - 1)), 
                                                count = const.NUM_REG_PER_ZONE)
        if not ret:
            raise ReadRegistersError("Error reading holding register")
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

    async def async_areas_registered(self) -> (bool, dict):
        """ Get all areas values """
        _areas_dict:dict = {}
        # retreive all areas (registered and unregistered)
        regs, ret = await self.__async_read_registers(start_reg = const.REG_START_ZONE, 
                                                count = const.NUM_REG_PER_ZONE * const.NB_ZONE_MAX)
        if not ret:
            raise ReadRegistersError("Error reading holding register")
        for area_idx in range(const.NB_ZONE_MAX):
            _idx:int = 4 * area_idx
            _area_dict:dict = {}
            # test if area is registered or not
            if const.ZoneRegister(regs[_idx + const.REG_LOCK_ZONE] >> 1) == const.ZoneRegister.REGISTER_OFF:
                continue

            _area_dict['state'] = const.ZoneState(regs[_idx + const.REG_LOCK_ZONE] & 0b01)
            _area_dict['register'] = const.ZoneRegister(regs[_idx + const.REG_LOCK_ZONE] >> 1)
            _area_dict['fan'] = const.ZoneFanMode((regs[_idx + const.REG_STATE_AND_FLOW] & 0xF0) >> 4)
            _area_dict['clim'] = const.ZoneClimMode(regs[_idx + const.REG_STATE_AND_FLOW] & 0x0F)
            _area_dict['order_temp'] = regs[_idx + const.REG_TEMP_ORDER]/2
            _area_dict['real_temp'] = regs[_idx + const.REG_TEMP_REAL]/2
            _areas_dict[area_idx + 1] = _area_dict
        return True, _areas_dict

    async def async_set_debug(self, val:bool) -> bool:
        ''' Set/Reset Debug Mode '''
        if val:
            pymodbus_apply_logging_config("DEBUG")
        else:
            pymodbus_apply_logging_config("INFO")
        return True

    async def async_system_status(self) -> (bool, const.SysState):
        ''' Read system status register '''
        reg, ret = await self.__async_read_register(const.REG_SYS_STATE)
        if not ret:
            _LOGGER.error('Error retreive system status')
            reg = 0
        return ret, const.SysState(reg)

    async def async_set_system_status(self,
                                        opt:const.SysState,
                                        ) -> bool:
        ''' Write system status '''
        ret = await self.__async_write_register(reg = const.REG_SYS_STATE, val = int(opt))
        if not ret:
            _LOGGER.error('Error writing system status')
        return ret

    async def async_global_mode(self) -> (bool, const.GlobalMode):
        ''' Read global mode '''
        reg, ret = await self.__async_read_register(const.REG_GLOBAL_MODE)
        if not ret:
            _LOGGER.error('Error retreive global mode')
            reg = 1
        return ret, const.GlobalMode(reg)

    async def async_set_global_mode(self,
                                    opt:const.GlobalMode,
                                    ) -> bool:
        ''' Write global mode '''
        ret = await self.__async_write_register(reg = const.REG_GLOBAL_MODE, val = int(opt))
        if not ret:
            _LOGGER.error('Error writing global mode')
        return ret

    async def async_efficiency(self) -> (bool, const.Efficiency):
        ''' read efficiency/speed '''
        reg, ret = await self.__async_read_register(const.REG_EFFICIENCY)
        if not ret:
            _LOGGER.error('Error retreive efficiency')
            reg = 1
        return ret, const.Efficiency(reg)

    async def async_set_efficiency(self,
                                    opt:const.GlobalMode,
                                    ) -> bool:
        ''' Write efficiency '''
        ret = await self.__async_write_register(reg = const.REG_EFFICIENCY, val = int(opt))
        if not ret:
            _LOGGER.error('Error writing efficiency')
        return ret

    async def async_engines_throughput(self) -> (bool, list):
        ''' read engines throughput AC1, AC2, AC3, AC4 '''
        engines_lst = []
        regs, ret = await self.__async_read_registers(const.REG_START_FLOW_ENGINE,
                                                        const.NUM_OF_ENGINES)
        if ret:
            for idx, reg in enumerate(regs):
                engines_lst.append(const.FlowEngine(reg))
        else:
            _LOGGER.error('Error retreive engines throughput')
        return ret, engines_lst

    async def async_engine_throughput(self,
                                        engine_id:int = 0,
                                        ) -> (bool, int):
        ''' read engine throughput specified by id '''
        if engine_id < 1 or engine_id > 4:
            raise UnitIdError("engine Id must be between 1 and 4")
        reg, ret = await self.__async_read_register(const.REG_START_FLOW_ENGINE + (engine_id - 1))
        if not ret:
            _LOGGER.error('Error retreive engine throughput for id:{}'.format(engine_id))
            reg = 0
        return ret, reg

    async def async_engine_state(self,
                                    engine_id:int = 0,
                                    ) -> (bool, const.FlowEngine):
        ''' read engine state specified by id '''
        if engine_id < 1 or engine_id > 4:
            raise UnitIdError("Engine id must be between 1 and 4")
        reg, ret = await self.__async_read_register(const.REG_START_FLOW_STATE_ENGINE + (engine_id - 1))
        if not ret:
            _LOGGER.error('Error retreive engine state for id:{}'.format(engine_id))
            reg = 4
        return ret, const.FlowEngine(reg)

    async def async_set_engine_state(self,
                                        engine_id:int = 0,
                                        opt:const.FlowEngine = const.FlowEngine.AUTO,
                                        ) -> bool:
        ''' write engine state specified by id '''
        if engine_id < 1 or engine_id > 4:
            raise UnitIdError("Engine id must be between 1 and 4")
        ret = await self.__async_write_register(reg = const.REG_START_FLOW_STATE_ENGINE + (engine_id - 1), val = int(opt))
        if not ret:
            _LOGGER.error('Error writing engine state for id:{}'.format(engine_id))
        return ret

    async def async_engine_order_temp(self,
                                        engine_id:int = 0,
                                        ) -> (bool, float):
        ''' read engine order temperature specified by id '''
        if engine_id < 1 or engine_id > 4:
            raise UnitIdError("Engine id must be between 1 and 4")
        reg, ret = await self.__async_read_register(const.REG_START_ORDER_TEMP + (engine_id - 1))
        if not ret:
            _LOGGER.error('Error retreive engine order temp for id:{}'.format(engine_id))
            reg = 0
        return ret, reg / 2

    async def async_engine_orders_temp(self) -> (bool, list):
        ''' read orders temperature for engines : AC1, AC2, AC3, AC4 '''
        engines_lst = []
        regs, ret = await self.__async_read_registers(const.REG_START_ORDER_TEMP, const.NUM_OF_ENGINES)
        if ret:
            for idx, reg in enumerate(regs):
                engines_lst.append(reg/2)
        else:
            _LOGGER.error('error reading engines order temp registers')
        return ret, engines_lst

    async def async_set_area_target_temp(self,
                                        zone_id:int = 0,
                                        val:float = 0.0,
                                        ) -> bool:
        ''' Set area target temperature '''
        if zone_id > const.NB_ZONE_MAX or zone_id == 0:
            raise ZoneIdError('Zone Id must be between 1 to 16')
        if val > const.MAX_TEMP_ORDER or val < const.MIN_TEMP_ORDER:
            _LOGGER.error('Order Temperature must be between {} and {}'.format(const.MIN_TEMP_ORDER, const.MAX_TEMP_ORDER))
            return False
        ret = await self.__async_write_register(reg = const.REG_START_ZONE + (4 * (zone_id - 1)) + const.REG_TEMP_ORDER, val = int(val * 2))
        if not ret:
            _LOGGER.error('Error writing area order temperature')

        return ret

    async def async_area_temp(self,
                                id_zone:int = 0,
                                ) -> (bool, float):
        """ get temperature of specific area id """
        reg, ret = await self.__async_read_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_TEMP_REAL)
        if not ret:
            _LOGGER.error('Error retreive area real temp')
            reg = 0
        return ret, reg / 2

    async def async_area_target_temp(self,
                                    id_zone:int = 0,
                                    ) -> (bool, float):
        """ get target temperature of specific area id """
        reg, ret = await self.__async_read_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_TEMP_ORDER)
        if not ret:
            _LOGGER.error('Error retreive area target temp')
            reg = 0
        return ret, reg / 2

    async def async_area_clim_and_fan_mode(self, 
                                            id_zone:int = 0,
                                            ) -> (bool, const.ZoneFanMode, const.ZoneClimMode):
        """ get climate and fan mode of specific area id """
        reg, ret = await self.__async_read_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_STATE_AND_FLOW)
        if not ret:
            _LOGGER.error('Error retreive area fan and climate values')
            reg = 0
        return ret, const.ZoneFanMode((reg & 0xF0) >> 4), const.ZoneClimMode(reg & 0x0F)

    async def async_area_state_and_register(self,
                                            id_zone:int = 0,
                                            ) -> (bool, const.ZoneRegister, const.ZoneState):
        """ get area state and register """
        reg, ret = await self.__async_read_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_LOCK_ZONE)
        if not ret:
            _LOGGER.error('Error retreive area register value')
            reg = 0
        return ret, const.ZoneRegister(reg >> 1), const.ZoneState(reg & 0b01)

    async def async_set_area_state(self,
                                    id_zone:int = 0,
                                    val:const.ZoneState = const.ZoneState.STATE_OFF,
                                    ) -> bool:
        """ set area state """
        register:const.ZoneRegister = const.ZoneRegister.REGISTER_OFF
        if id_zone > const.NB_ZONE_MAX or id_zone == 0:
            raise ZoneIdError('Area Id must be between 1 to 16')
        # retreive values to combine the new state with register read
        ret, register, _ = await self.async_area_state_and_register(id_zone = id_zone)
        if not ret:
            _LOGGER.error("Error reading state and register mode")
            return ret
        #_LOGGER.debug("register & state: {}".format(hex((int(register) << 1) | (int(val) & 0b01))))
        ret = await self.__async_write_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_LOCK_ZONE,
                                            val = int(int(register) << 1) | (int(val) & 0b01))
        if not ret:
            _LOGGER.error('Error writing area state value')

        return True

    async def async_set_area_clim_mode(self,
                                        id_zone:int = 0,
                                        val:const.ZoneClimMode = const.ZoneClimMode.OFF,
                                ) -> bool:
        """ set area clim mode """
        fan:const.ZoneFanMode = const.ZoneFanMode.FAN_OFF
        if id_zone > const.NB_ZONE_MAX or id_zone == 0:
            raise ZoneIdError('Zone Id must be between 1 to 16')
        # retreive values to combine the new climate mode with fan mode read
        ret, fan, _ = await self.async_area_clim_and_fan_mode(id_zone = id_zone)
        if not ret:
            _LOGGER.error("Error reading fan and clim mode")
            return ret
        #_LOGGER.debug("Fan & Clim: {}".format(hex((int(fan) << 4) | (int(val) & 0x0F))))
        ret = await self.__async_write_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_STATE_AND_FLOW,
                                            val = int(int(fan) << 4) | (int(val) & 0x0F))
        if not ret:
            _LOGGER.error('Error writing area climate mode')

        return ret

    async def async_set_area_fan_mode(self,
                                        id_zone:int = 0,
                                        val:const.ZoneFanMode = const.ZoneFanMode.FAN_OFF,
                                    ) -> bool:
        """ set area fan mode """
        clim:const.ZoneClimMode = const.ZoneClimMode.OFF
        if id_zone > const.NB_ZONE_MAX or id_zone == 0:
            raise ZoneIdError('Zone Id must be between 1 to 16')
        # retreive values to combine the new fan mode with climate mode read
        ret, _, clim = await self.async_area_clim_and_fan_mode(id_zone = id_zone)
        if not ret:
            _LOGGER.error("Error reading fan and clim mode")
            return ret
        #_LOGGER.debug("Fan & Clim: {}".format(hex((int(val) << 4) | (int(clim) & 0x0F))))
        ret = await self.__async_write_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_STATE_AND_FLOW,
                                            val = int(int(val) << 4) | (int(clim) & 0x0F))
        if not ret:
            _LOGGER.error('Error writing area fan mode')
        return ret

class InitialisationError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg    

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
