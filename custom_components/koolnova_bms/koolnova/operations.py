""" local API to communicate with Koolnova BMS Modbus RTU client """

import logging as log

import asyncio

from pymodbus.client import AsyncModbusSerialClient as ModbusClient
from pymodbus.client import AsyncModbusTcpClient as ModbusTcpClient
from pymodbus.pdu import ExceptionResponse

from . import const

_LOGGER = log.getLogger(__name__)

_DEBUG_LOGGERS = (
    "custom_components.koolnova_bms",
    "pymodbus",
    "pymodbus.logging",
)

def _set_debug_logging(enabled:bool) -> None:
    """Set debug logger levels without changing Home Assistant handlers."""
    level = log.DEBUG if enabled else log.INFO
    for logger_name in _DEBUG_LOGGERS:
        log.getLogger(logger_name).setLevel(level)

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
        self._table_version = const.normalize_table_version(
            kwargs.get('table_version')
        )
        self._registers = const.register_map_for_table_version(
            self._table_version
        )
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
        _set_debug_logging(self._debug)

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

    @staticmethod
    def __validated_int(name:str, value:int, minimum:int, maximum:int) -> int:
        ''' Validate an integer value against documented Modbus bounds '''
        value = int(value)
        if value < minimum or value > maximum:
            raise ValueError("{} must be between {} and {}".format(name, minimum, maximum))
        return value

    @staticmethod
    def __validated_half_degree_raw(name:str, value:float) -> int:
        ''' Validate a Celsius value encoded as half-degree Modbus steps. '''
        raw = float(value) * 2
        rounded_raw = round(raw)
        if abs(raw - rounded_raw) > 0.000001:
            raise ValueError("{} must use 0.5°C steps".format(name))
        return Operations.__validated_int(name, rounded_raw, 0x00, 0xFF)

    @property
    def supports_efficiency(self) -> bool:
        """Return whether the selected register map supports efficiency."""
        return self._registers[const.REG_KEY_EFFICIENCY] is not None

    def disconnect(self) -> None:
        ''' close the underlying socket connection '''
        if self._client.connected:
            self._client.close()

    async def async_test_communication(self) -> bool:
        """Test communication using a common zone register."""
        _, ret = await self.__async_read_register(const.REG_START_ZONE)
        return ret

    async def async_detect_table_version(self) -> (bool, str):
        """Detect the Koolnova Modbus table version.

        Register 40073 is used as the discriminator:
        - v1.0 uses it as AC1 airflow programming, with legal values 1..4.
        - v2.0 uses it as control unit model/software version.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_MODEL_VERSION)
        if not ret:
            _LOGGER.error("Unable to read Koolnova table version candidate register")
            return False, const.TABLE_VERSION_DEFAULT

        if reg in const.V1_FLOW_STATE_VALUES:
            table_version = const.TABLE_VERSION_V1
        elif reg != 0:
            table_version = const.TABLE_VERSION_V2
        else:
            _LOGGER.warning(
                "Unknown Koolnova table version pattern from register 40073 value %s; using %s",
                hex(reg),
                const.TABLE_VERSION_DEFAULT,
            )
            table_version = const.TABLE_VERSION_DEFAULT

        _LOGGER.debug(
            "Detected Koolnova Modbus table version %s from register 40073 value %s",
            table_version,
            hex(reg),
        )
        return True, table_version

    async def async_v2_model_version(self) -> (bool, int):
        ''' read 40073: control unit model and software version '''
        reg, ret = await self.__async_read_register(const.REG_V2_MODEL_VERSION)
        if not ret:
            _LOGGER.error('Error retreive v2 model version')
            reg = 0
        return ret, reg

    async def async_v2_parameters(self) -> (bool, dict):
        ''' read 40074: system parameters '''
        reg, ret = await self.__async_read_register(const.REG_V2_PARAMETERS)
        if not ret:
            _LOGGER.error('Error retreive v2 parameters')
            return ret, {}

        msb = (reg >> 8) & 0xFF
        lsb = reg & 0xFF
        return ret, {
            "raw": reg,
            "msb": msb,
            "lsb": lsb,
            "hum": bool(msb & 0x80),
            "af": bool(msb & 0x40),
            "reserved_msb_bit5": bool(msb & 0x20),
            "stop": bool(msb & 0x10),
            "eco": bool(msb & 0x08),
            "efi": msb & 0x07,
            "reserved_lsb_bit7": bool(lsb & 0x80),
            "din2": bool(lsb & 0x40),
            "din1": bool(lsb & 0x20),
            "aux1": bool(lsb & 0x10),
            "heating": bool(lsb & 0x08),
            "pump": bool(lsb & 0x04),
            "k5": bool(lsb & 0x02),
            "k6": bool(lsb & 0x01),
        }

    async def async_set_v2_parameters(self,
                                        raw:int,
                                        ) -> bool:
        ''' write 40074: system parameters '''
        raw = Operations.__validated_int("raw", raw, 0x0000, 0xFFFF)
        ret = await self.__async_write_register(reg = const.REG_V2_PARAMETERS, val = int(raw))
        if not ret:
            _LOGGER.error('Error writing v2 parameters')
        return ret

    async def async_v2_active_modes(self) -> (bool, dict):
        ''' read 40075: active modes '''
        reg, ret = await self.__async_read_register(const.REG_V2_ACTIVE_MODES)
        if not ret:
            _LOGGER.error('Error retreive v2 active modes')
            return ret, {}

        msb = (reg >> 8) & 0xFF
        lsb = reg & 0xFF
        return ret, {
            "raw": reg,
            "msb": msb,
            "lsb": lsb,
            "bit7_expected_zero": bool(lsb & 0x80),
            "radiant_floor_heating": bool(lsb & 0x40),
            "radiant_floor_cooling": bool(lsb & 0x20),
            "radiant_floor": bool(lsb & 0x10),
            "dehumidification": bool(lsb & 0x08),
            "heating": bool(lsb & 0x04),
            "cooling": bool(lsb & 0x02),
            "ventilation": bool(lsb & 0x01),
        }

    async def async_set_v2_active_modes(self,
                                        raw:int,
                                        ) -> bool:
        ''' write 40075: active modes '''
        raw = Operations.__validated_int("raw", raw, 0x0000, 0xFFFF)
        if raw & 0x0080:
            raise ValueError("raw bit 7 of LSB must be 0")
        ret = await self.__async_write_register(reg = const.REG_V2_ACTIVE_MODES, val = int(raw))
        if not ret:
            _LOGGER.error('Error writing v2 active modes')
        return ret

    async def async_v2_temperature_limits(self) -> (bool, dict):
        ''' read 40076: temperature limits '''
        reg, ret = await self.__async_read_register(const.REG_V2_TEMPERATURE_LIMITS)
        if not ret:
            _LOGGER.error('Error retreive v2 temperature limits')
            return ret, {}

        msb = (reg >> 8) & 0xFF
        lsb = reg & 0xFF
        return ret, {
            "raw": reg,
            "msb": msb,
            "lsb": lsb,
            "max_heating_limit": msb / 2,
            "min_cooling_limit": lsb / 2,
        }

    async def async_set_v2_temperature_limits(self,
                                                max_heating_limit:float,
                                                min_cooling_limit:float,
                                                ) -> bool:
        ''' write 40076: temperature limits '''
        max_heating_limit_raw = Operations.__validated_half_degree_raw(
            "max_heating_limit",
            max_heating_limit,
        )
        min_cooling_limit_raw = Operations.__validated_half_degree_raw(
            "min_cooling_limit",
            min_cooling_limit,
        )
        val = (max_heating_limit_raw << 8) | min_cooling_limit_raw
        ret = await self.__async_write_register(reg = const.REG_V2_TEMPERATURE_LIMITS, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 temperature limits')
        return ret

    async def async_v2_auto_changeover_humidity(self) -> (bool, dict):
        ''' read 40077: automatic changeover modes and humidity control '''
        reg, ret = await self.__async_read_register(const.REG_V2_AUTO_CHANGEOVER_HUMIDITY)
        if not ret:
            _LOGGER.error('Error retreive v2 auto changeover humidity')
            return ret, {}

        msb = (reg >> 8) & 0xFF
        lsb = reg & 0xFF
        mode_when_above = (msb >> 4) & 0x0F
        mode_when_below = msb & 0x0F
        return ret, {
            "raw": reg,
            "msb": msb,
            "lsb": lsb,
            "mode_when_water_above_threshold": mode_when_above,
            "mode_when_water_above_threshold_name": {
                0x04: "radiant_floor_heating",
                0x06: "radiant_floor_heating_and_heating",
                0x02: "heating",
            }.get(mode_when_above),
            "mode_when_water_below_threshold": mode_when_below,
            "mode_when_water_below_threshold_name": {
                0x01: "cooling",
                0x05: "radiant_floor_cooling_and_cooling",
            }.get(mode_when_below),
            "humidity_relay_threshold": lsb,
        }

    async def async_set_v2_auto_changeover_humidity(self,
                                                    mode_when_water_above_threshold:int,
                                                    mode_when_water_below_threshold:int,
                                                    humidity_relay_threshold:int,
                                                    ) -> bool:
        ''' write 40077: automatic changeover modes and humidity control '''
        mode_when_water_above_threshold = Operations.__validated_int(
            "mode_when_water_above_threshold",
            mode_when_water_above_threshold,
            0x00,
            0x0F,
        )
        mode_when_water_below_threshold = Operations.__validated_int(
            "mode_when_water_below_threshold",
            mode_when_water_below_threshold,
            0x00,
            0x0F,
        )
        humidity_relay_threshold = Operations.__validated_int(
            "humidity_relay_threshold",
            humidity_relay_threshold,
            0x00,
            0xFF,
        )
        msb = ((mode_when_water_above_threshold << 4) | mode_when_water_below_threshold)
        val = (msb << 8) | humidity_relay_threshold
        ret = await self.__async_write_register(reg = const.REG_V2_AUTO_CHANGEOVER_HUMIDITY, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 auto changeover humidity')
        return ret

    async def async_v2_system_time(self) -> (bool, dict):
        ''' read 40078: system time '''
        reg, ret = await self.__async_read_register(const.REG_V2_SYSTEM_TIME)
        if not ret:
            _LOGGER.error('Error retreive v2 system time')
            return ret, {}

        reserved_prefix = (reg >> 14) & 0x03
        day = (reg >> 11) & 0x07
        hour = (reg >> 6) & 0x1F
        minute = reg & 0x3F
        return ret, {
            "raw": reg,
            "reserved_prefix": reserved_prefix,
            "day": day,
            "day_name": {
                1: "monday",
                2: "tuesday",
                3: "wednesday",
                4: "thursday",
                5: "friday",
                6: "saturday",
                7: "sunday",
            }.get(day),
            "hour": hour,
            "minute": minute,
        }

    async def async_set_v2_system_time(self,
                                        day:int,
                                        hour:int,
                                        minute:int,
                                        ) -> bool:
        ''' write 40078: system time '''
        day = Operations.__validated_int("day", day, 1, 7)
        hour = Operations.__validated_int("hour", hour, 0, 23)
        minute = Operations.__validated_int("minute", minute, 0, 59)
        val = (day << 11) | (hour << 6) | minute
        ret = await self.__async_write_register(reg = const.REG_V2_SYSTEM_TIME, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 system time')
        return ret

    async def async_v2_external_inputs(self) -> (bool, dict):
        ''' read 40079: external inputs '''
        reg, ret = await self.__async_read_register(const.REG_V2_EXTERNAL_INPUTS)
        if not ret:
            _LOGGER.error('Error retreive v2 external inputs')
            return ret, {}

        msb = (reg >> 8) & 0xFF
        lsb = reg & 0xFF
        return ret, {
            "raw": reg,
            "msb": msb,
            "lsb": lsb,
            "din2_function": (lsb >> 4) & 0x0F,
            "din1_function": lsb & 0x0F,
        }

    async def async_set_v2_external_inputs(self,
                                            din2_function:int,
                                            din1_function:int,
                                            ) -> bool:
        ''' write 40079: external inputs '''
        din2_function = Operations.__validated_int("din2_function", din2_function, 0x00, 0x0F)
        din1_function = Operations.__validated_int("din1_function", din1_function, 0x00, 0x0F)
        val = ((din2_function << 4) | din1_function)
        ret = await self.__async_write_register(reg = const.REG_V2_EXTERNAL_INPUTS, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 external inputs')
        return ret

    async def async_v2_opening_angle_z1_z8(self) -> (bool, dict):
        ''' read 40080: opening angle for zones Z1 to Z8 '''
        reg, ret = await self.__async_read_register(const.REG_V2_OPENING_ANGLE_Z1_Z8)
        if not ret:
            _LOGGER.error('Error retreive v2 opening angle Z1 to Z8')
            return ret, {}

        msb = (reg >> 8) & 0xFF
        lsb = reg & 0xFF
        angle_code = (lsb >> 4) & 0x0F
        zone_index = lsb & 0x0F
        return ret, {
            "raw": reg,
            "msb": msb,
            "lsb": lsb,
            "angle_code": angle_code,
            "angle_degrees": {
                0x00: 45,
                0x01: 60,
                0x02: 75,
                0x03: 90,
            }.get(angle_code),
            "zone_index": zone_index,
            "zone_id": zone_index + 1,
        }

    async def async_set_v2_opening_angle_z1_z8(self,
                                                angle_code:int,
                                                zone_index:int,
                                                ) -> bool:
        ''' write 40080: opening angle for zones Z1 to Z8 '''
        angle_code = Operations.__validated_int("angle_code", angle_code, 0x00, 0x03)
        zone_index = Operations.__validated_int("zone_index", zone_index, 0, 7)
        val = ((angle_code << 4) | zone_index)
        ret = await self.__async_write_register(reg = const.REG_V2_OPENING_ANGLE_Z1_Z8, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 opening angle Z1 to Z8')
        return ret

    async def async_v2_opening_angle_z9_z16(self) -> (bool, dict):
        ''' read 40081: opening angle for zones Z9 to Z16 '''
        reg, ret = await self.__async_read_register(const.REG_V2_OPENING_ANGLE_Z9_Z16)
        if not ret:
            _LOGGER.error('Error retreive v2 opening angle Z9 to Z16')
            return ret, {}

        msb = (reg >> 8) & 0xFF
        lsb = reg & 0xFF
        angle_code = (lsb >> 4) & 0x0F
        zone_index = lsb & 0x0F
        return ret, {
            "raw": reg,
            "msb": msb,
            "lsb": lsb,
            "angle_code": angle_code,
            "angle_degrees": {
                0x00: 45,
                0x01: 60,
                0x02: 75,
                0x03: 90,
            }.get(angle_code),
            "zone_index": zone_index,
            "zone_id": zone_index + 9,
        }

    async def async_set_v2_opening_angle_z9_z16(self,
                                                angle_code:int,
                                                zone_index:int,
                                                ) -> bool:
        ''' write 40081: opening angle for zones Z9 to Z16 '''
        angle_code = Operations.__validated_int("angle_code", angle_code, 0x00, 0x03)
        zone_index = Operations.__validated_int("zone_index", zone_index, 8, 15) - 8
        val = ((angle_code << 4) | zone_index)
        ret = await self.__async_write_register(reg = const.REG_V2_OPENING_ANGLE_Z9_Z16, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 opening angle Z9 to Z16')
        return ret

    async def async_v2_floor_water_temperature(self) -> (bool, float):
        ''' read 40082: radiant floor water NTC temperature '''
        reg, ret = await self.__async_read_register(const.REG_V2_FLOOR_WATER_TEMPERATURE)
        if not ret:
            _LOGGER.error('Error retreive v2 floor water temperature')
            return ret, 0.0
        return ret, reg / 10

    async def async_v2_outdoor_temperature(self) -> (bool, float):
        ''' read 40083: outdoor ambient temperature '''
        reg, ret = await self.__async_read_register(const.REG_V2_OUTDOOR_TEMPERATURE)
        if not ret:
            _LOGGER.error('Error retreive v2 outdoor temperature')
            return ret, 0.0

        # Signed 16-bit tenths of degree: FF99 is -103d, so -10.3 C.
        if reg & 0x8000:
            reg -= 0x10000
        return ret, reg / 10

    async def async_v2_aux_temperature(self) -> (bool, float):
        ''' read 40084: auxiliary NTC temperature '''
        reg, ret = await self.__async_read_register(const.REG_V2_AUX_TEMPERATURE)
        if not ret:
            _LOGGER.error('Error retreive v2 auxiliary temperature')
            return ret, 0.0

        # Signed 16-bit tenths of degree: FF99 is -103d, so -10.3 C.
        if reg & 0x8000:
            reg -= 0x10000
        return ret, reg / 10

    async def async_v2_valve_mask(self) -> (bool, dict):
        ''' read 40085: valve mask '''
        reg, ret = await self.__async_read_register(const.REG_V2_VALVE_MASK)
        if not ret:
            _LOGGER.error('Error retreive v2 valve mask')
            return ret, {}

        msb = (reg >> 8) & 0xFF
        lsb = reg & 0xFF
        enabled_zone_indexes = [
            zone_index
            for zone_index in range(16)
            if reg & (1 << zone_index)
        ]
        return ret, {
            "raw": reg,
            "msb": msb,
            "lsb": lsb,
            "enabled_zone_indexes": enabled_zone_indexes,
            "zone_pump_enabled": {
                zone_index: zone_index in enabled_zone_indexes
                for zone_index in range(16)
            },
        }

    async def async_set_v2_valve_mask(self,
                                        raw:int,
                                        ) -> bool:
        ''' write 40085: valve mask '''
        raw = Operations.__validated_int("raw", raw, 0x0000, 0xFFFF)
        ret = await self.__async_write_register(reg = const.REG_V2_VALVE_MASK, val = raw)
        if not ret:
            _LOGGER.error('Error writing v2 valve mask')
        return ret

    async def async_v2_pump_delay_valve_offset(self) -> (bool, dict):
        ''' read 40086: pump delay and valve offset '''
        reg, ret = await self.__async_read_register(const.REG_V2_PUMP_DELAY_VALVE_OFFSET)
        if not ret:
            _LOGGER.error('Error retreive v2 pump delay valve offset')
            return ret, {}

        msb = (reg >> 8) & 0xFF
        lsb = reg & 0xFF
        return ret, {
            "raw": reg,
            "msb": msb,
            "lsb": lsb,
            "valve_origin_offset": msb,
            "pump_delay_seconds": lsb,
            "pump_delay_seconds_valid": 60 <= lsb <= 255,
        }

    async def async_set_v2_pump_delay_valve_offset(self,
                                                    valve_origin_offset:int,
                                                    pump_delay_seconds:int,
                                                    ) -> bool:
        ''' write 40086: pump delay and valve offset '''
        valve_origin_offset = Operations.__validated_int(
            "valve_origin_offset",
            valve_origin_offset,
            0x00,
            0x07,
        )
        pump_delay_seconds = Operations.__validated_int(
            "pump_delay_seconds",
            pump_delay_seconds,
            60,
            255,
        )
        val = (valve_origin_offset << 8) | pump_delay_seconds
        ret = await self.__async_write_register(reg = const.REG_V2_PUMP_DELAY_VALVE_OFFSET, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 pump delay valve offset')
        return ret

    async def async_v2_immersion_heater(self) -> (bool, dict):
        ''' read 40087: immersion heater '''
        reg, ret = await self.__async_read_register(const.REG_V2_IMMERSION_HEATER)
        if not ret:
            _LOGGER.error('Error retreive v2 immersion heater')
            return ret, {}

        msb = (reg >> 8) & 0xFF
        lsb = reg & 0xFF
        activation_temperature = lsb
        if activation_temperature & 0x80:
            activation_temperature -= 0x100
        return ret, {
            "raw": reg,
            "msb": msb,
            "lsb": lsb,
            "activation_delay_minutes": msb,
            "activation_temperature_celsius": activation_temperature,
        }

    async def async_set_v2_immersion_heater(self,
                                            activation_delay_minutes:int,
                                            activation_temperature_celsius:int,
                                            ) -> bool:
        ''' write 40087: immersion heater '''
        activation_delay_minutes = Operations.__validated_int(
            "activation_delay_minutes",
            activation_delay_minutes,
            0,
            255,
        )
        activation_temperature_celsius = Operations.__validated_int(
            "activation_temperature_celsius",
            activation_temperature_celsius,
            -128,
            127,
        )
        val = (activation_delay_minutes << 8) | (activation_temperature_celsius & 0xFF)
        ret = await self.__async_write_register(reg = const.REG_V2_IMMERSION_HEATER, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 immersion heater')
        return ret

    async def async_v2_thermostat_block(self) -> (bool, dict):
        ''' read 40088: thermostat block '''
        reg, ret = await self.__async_read_register(const.REG_V2_THERMOSTAT_BLOCK)
        if not ret:
            _LOGGER.error('Error retreive v2 thermostat block')
            return ret, {}

        msb = (reg >> 8) & 0xFF
        lsb = reg & 0xFF
        return ret, {
            "raw": reg,
            "msb": msb,
            "lsb": lsb,
            "msb_expected_zero": msb == 0,
            "block_level": lsb,
            "block_level_valid": 0x00 <= lsb <= 0x0F,
            "no_block": lsb == 0x00,
            "total_block": lsb == 0x0F,
        }

    async def async_set_v2_thermostat_block(self,
                                            block_level:int,
                                            ) -> bool:
        ''' write 40088: thermostat block '''
        block_level = Operations.__validated_int("block_level", block_level, 0x00, 0x0F)
        ret = await self.__async_write_register(reg = const.REG_V2_THERMOSTAT_BLOCK, val = block_level)
        if not ret:
            _LOGGER.error('Error writing v2 thermostat block')
        return ret

    async def async_v2_auto_mode(self) -> (bool, dict):
        ''' read 40089: automatic mode '''
        reg, ret = await self.__async_read_register(const.REG_V2_AUTO_MODE)
        if not ret:
            _LOGGER.error('Error retreive v2 auto mode')
            return ret, {}

        msb = (reg >> 8) & 0xFF
        lsb = reg & 0xFF
        return ret, {
            "raw": reg,
            "msb": msb,
            "lsb": lsb,
            "cooling_water_threshold_celsius": msb,
            "heating_water_threshold_celsius": lsb,
        }

    async def async_set_v2_auto_mode(self,
                                    cooling_water_threshold_celsius:int,
                                    heating_water_threshold_celsius:int,
                                    ) -> bool:
        ''' write 40089: automatic mode '''
        cooling_water_threshold_celsius = Operations.__validated_int(
            "cooling_water_threshold_celsius",
            cooling_water_threshold_celsius,
            0x00,
            0xFF,
        )
        heating_water_threshold_celsius = Operations.__validated_int(
            "heating_water_threshold_celsius",
            heating_water_threshold_celsius,
            0x00,
            0xFF,
        )
        val = (cooling_water_threshold_celsius << 8) | heating_water_threshold_celsius
        ret = await self.__async_write_register(reg = const.REG_V2_AUTO_MODE, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 auto mode')
        return ret

    async def async_v2_mixing_valve_ambient_temperatures(self) -> (bool, dict):
        ''' read 40090: ambient temperatures for mixing valve control '''
        reg, ret = await self.__async_read_register(const.REG_V2_MIXING_VALVE_AMBIENT_TEMPERATURES)
        if not ret:
            _LOGGER.error('Error retreive v2 mixing valve ambient temperatures')
            return ret, {}

        msb = (reg >> 8) & 0xFF
        lsb = reg & 0xFF
        lower_ambient_temperature = lsb
        if lower_ambient_temperature & 0x80:
            lower_ambient_temperature -= 0x100
        return ret, {
            "raw": reg,
            "msb": msb,
            "lsb": lsb,
            "upper_ambient_temperature_celsius": msb,
            "upper_ambient_temperature_valid": 25 <= msb <= 45,
            "lower_ambient_temperature_celsius": lower_ambient_temperature,
            "lower_ambient_temperature_valid": -20 <= lower_ambient_temperature <= 30,
        }

    async def async_set_v2_mixing_valve_ambient_temperatures(self,
                                                            upper_ambient_temperature_celsius:int,
                                                            lower_ambient_temperature_celsius:int,
                                                            ) -> bool:
        ''' write 40090: ambient temperatures for mixing valve control '''
        upper_ambient_temperature_celsius = Operations.__validated_int(
            "upper_ambient_temperature_celsius",
            upper_ambient_temperature_celsius,
            25,
            45,
        )
        lower_ambient_temperature_celsius = Operations.__validated_int(
            "lower_ambient_temperature_celsius",
            lower_ambient_temperature_celsius,
            -20,
            30,
        )
        val = (
            (upper_ambient_temperature_celsius << 8)
            | (lower_ambient_temperature_celsius & 0xFF)
        )
        ret = await self.__async_write_register(reg = const.REG_V2_MIXING_VALVE_AMBIENT_TEMPERATURES, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 mixing valve ambient temperatures')
        return ret

    async def async_v2_mixing_valve_water_temperatures(self) -> (bool, dict):
        ''' read 40091: water temperatures for mixing valve control '''
        reg, ret = await self.__async_read_register(const.REG_V2_MIXING_VALVE_WATER_TEMPERATURES)
        if not ret:
            _LOGGER.error('Error retreive v2 mixing valve water temperatures')
            return ret, {}

        msb = (reg >> 8) & 0xFF
        lsb = reg & 0xFF
        return ret, {
            "raw": reg,
            "msb": msb,
            "lsb": lsb,
            "upper_water_temperature_celsius": msb,
            "upper_water_temperature_valid": 25 <= msb <= 45,
            "lower_water_temperature_celsius": lsb,
            "lower_water_temperature_valid": 25 <= lsb <= 45,
        }

    async def async_set_v2_mixing_valve_water_temperatures(self,
                                                            upper_water_temperature_celsius:int,
                                                            lower_water_temperature_celsius:int,
                                                            ) -> bool:
        ''' write 40091: water temperatures for mixing valve control '''
        upper_water_temperature_celsius = Operations.__validated_int(
            "upper_water_temperature_celsius",
            upper_water_temperature_celsius,
            25,
            45,
        )
        lower_water_temperature_celsius = Operations.__validated_int(
            "lower_water_temperature_celsius",
            lower_water_temperature_celsius,
            25,
            45,
        )
        val = (upper_water_temperature_celsius << 8) | lower_water_temperature_celsius
        ret = await self.__async_write_register(reg = const.REG_V2_MIXING_VALVE_WATER_TEMPERATURES, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 mixing valve water temperatures')
        return ret

    async def async_v2_mixing_valve_mode_info(self) -> (bool, dict):
        ''' read 40092: mixing valve mode information '''
        reg, ret = await self.__async_read_register(const.REG_V2_MIXING_VALVE_MODE_INFO)
        if not ret:
            _LOGGER.error('Error retreive v2 mixing valve mode info')
            return ret, {}

        msb = (reg >> 8) & 0xFF
        lsb = reg & 0xFF
        safety_factor_code = (reg >> 14) & 0x03
        mode = (reg >> 12) & 0x03
        cooling_supply_temperature = (reg >> 6) & 0x3F
        heating_supply_temperature = reg & 0x3F
        return ret, {
            "raw": reg,
            "msb": msb,
            "lsb": lsb,
            "safety_factor_code": safety_factor_code,
            "safety_factor": {
                0x00: 0,
                0x01: 2,
                0x02: -2,
            }.get(safety_factor_code),
            "mode": mode,
            "cooling_mode": "dew_point" if mode & 0x02 else "fixed",
            "heating_mode": "curve" if mode & 0x01 else "fixed",
            "cooling_supply_temperature_celsius": cooling_supply_temperature,
            "cooling_supply_temperature_valid": 10 <= cooling_supply_temperature <= 22,
            "heating_supply_temperature_celsius": heating_supply_temperature,
            "heating_supply_temperature_valid": 25 <= heating_supply_temperature <= 45,
        }

    async def async_set_v2_mixing_valve_mode_info(self,
                                                    safety_factor_code:int,
                                                    mode:int,
                                                    cooling_supply_temperature_celsius:int,
                                                    heating_supply_temperature_celsius:int,
                                                    ) -> bool:
        ''' write 40092: mixing valve mode information '''
        safety_factor_code = Operations.__validated_int("safety_factor_code", safety_factor_code, 0x00, 0x02)
        mode = Operations.__validated_int("mode", mode, 0x00, 0x03)
        cooling_supply_temperature_celsius = Operations.__validated_int(
            "cooling_supply_temperature_celsius",
            cooling_supply_temperature_celsius,
            10,
            22,
        )
        heating_supply_temperature_celsius = Operations.__validated_int(
            "heating_supply_temperature_celsius",
            heating_supply_temperature_celsius,
            25,
            45,
        )
        val = (
            (safety_factor_code << 14)
            | (mode << 12)
            | (cooling_supply_temperature_celsius << 6)
            | heating_supply_temperature_celsius
        )
        ret = await self.__async_write_register(reg = const.REG_V2_MIXING_VALVE_MODE_INFO, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 mixing valve mode info')
        return ret

    async def async_v2_reserved_40107(self) -> (bool, int):
        ''' read 40107: reserved register '''
        reg, ret = await self.__async_read_register(const.REG_V2_RESERVED_40107)
        if not ret:
            _LOGGER.error('Error retreive v2 reserved register 40107')
            reg = 0
        return ret, reg

    async def async_v2_radiant_floor_demand_count(self) -> (bool, int):
        ''' read 40111: radiant floor heating thermostat demand count '''
        reg, ret = await self.__async_read_register(const.REG_V2_RADIANT_FLOOR_DEMAND_COUNT)
        if not ret:
            _LOGGER.error('Error retreive v2 radiant floor demand count')
            reg = 0
        return ret, reg

    async def async_v2_ac3_air_demand_count(self) -> (bool, int):
        ''' read 40112: AC3 air thermostat demand count '''
        reg, ret = await self.__async_read_register(const.REG_V2_AC3_AIR_DEMAND_COUNT)
        if not ret:
            _LOGGER.error('Error retreive v2 AC3 air demand count')
            reg = 0
        return ret, reg

    async def async_v2_connected_volumes(self) -> (bool, list):
        ''' read connected thermostat volume sum for AC1, AC2, AC3 and AC4 '''
        regs, ret = await self.__async_read_registers(
            const.REG_V2_START_CONNECTED_VOLUME,
            const.NUM_REG_V2_CONNECTED_VOLUME,
        )
        if not ret:
            _LOGGER.error('Error retreive v2 connected volumes')
            regs = []
        return ret, regs

    async def async_v2_active_volumes(self) -> (bool, list):
        ''' read active thermostat demand volume sum for AC1, AC2, AC3 and AC4 '''
        regs, ret = await self.__async_read_registers(
            const.REG_V2_START_ACTIVE_VOLUME,
            const.NUM_REG_V2_ACTIVE_VOLUME,
        )
        if not ret:
            _LOGGER.error('Error retreive v2 active volumes')
            regs = []
        return ret, regs

    async def async_v2_requested_temp_avgs(self) -> (bool, list):
        ''' read requested setpoint temperature average for AC1, AC2, AC3 and AC4 '''
        regs, ret = await self.__async_read_registers(
            const.REG_V2_START_REQUESTED_TEMP_AVG,
            const.NUM_REG_V2_REQUESTED_TEMP_AVG - 1,
        )
        if not ret:
            _LOGGER.error('Error retreive v2 requested temp averages AC1 to AC3')
            return ret, []

        # 40124 is not listed in the official table; AC4 is documented at 40125.
        reg_ac4, ret = await self.__async_read_register(
            const.REG_V2_START_REQUESTED_TEMP_AVG
            + const.NUM_REG_V2_REQUESTED_TEMP_AVG
        )
        if not ret:
            _LOGGER.error('Error retreive v2 requested temp average AC4')
            return ret, []

        regs = list(regs)
        regs.append(reg_ac4)
        return True, regs

    async def async_v2_efficiency_ac3_speed(self) -> (bool, int):
        ''' read 40126: MSB EFI and LSB AC3 speed '''
        reg, ret = await self.__async_read_register(const.REG_V2_EFFICIENCY_AC3_SPEED)
        if not ret:
            _LOGGER.error('Error retreive v2 efficiency AC3 speed')
            reg = 0
        return ret, reg

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
                if const.ZoneRegister((reg >> 1) & 0b1) == const.ZoneRegister.REGISTER_ON:
                    zone_dict['id'] = jdx
                    zone_dict['state'] = const.ZoneState(reg & 0b01)
                    zone_dict['register'] = const.ZoneRegister((reg >> 1) & 0b1)
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
        if const.ZoneRegister((regs[0] >> 1) & 0b1) == const.ZoneRegister.REGISTER_OFF:
            _LOGGER.warning("Zone with id: {} is not registered".format(zone_id))
            return False, {}

        zone_dict['state'] = const.ZoneState(regs[0] & 0b01)
        zone_dict['register'] = const.ZoneRegister((regs[0] >> 1) & 0b1)
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
            if const.ZoneRegister((regs[_idx + const.REG_LOCK_ZONE] >> 1) & 0b1) == const.ZoneRegister.REGISTER_OFF:
                continue

            _area_dict['state'] = const.ZoneState(regs[_idx + const.REG_LOCK_ZONE] & 0b01)
            _area_dict['register'] = const.ZoneRegister((regs[_idx + const.REG_LOCK_ZONE] >> 1) & 0b1)
            _area_dict['fan'] = const.ZoneFanMode((regs[_idx + const.REG_STATE_AND_FLOW] & 0xF0) >> 4)
            _area_dict['clim'] = const.ZoneClimMode(regs[_idx + const.REG_STATE_AND_FLOW] & 0x0F)
            _area_dict['order_temp'] = regs[_idx + const.REG_TEMP_ORDER]/2
            _area_dict['real_temp'] = regs[_idx + const.REG_TEMP_REAL]/2
            _areas_dict[area_idx + 1] = _area_dict
        return True, _areas_dict

    async def async_set_debug(self, val:bool) -> bool:
        ''' Set/Reset Debug Mode '''
        _set_debug_logging(val)
        return True

    async def async_system_status(self) -> (bool, const.SysState):
        ''' Read system status register '''
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_SYS_STATE])
        if not ret:
            _LOGGER.error('Error retreive system status')
            reg = 0
        return ret, const.SysState(reg)

    async def async_set_system_status(self,
                                        opt:const.SysState,
                                        ) -> bool:
        ''' Write system status '''
        ret = await self.__async_write_register(reg = self._registers[const.REG_KEY_SYS_STATE], val = int(opt))
        if not ret:
            _LOGGER.error('Error writing system status')
        return ret

    async def async_global_mode(self) -> (bool, const.GlobalMode):
        ''' Read global mode '''
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_GLOBAL_MODE])
        if not ret:
            _LOGGER.error('Error retreive global mode')
            reg = 1
        return ret, const.GlobalMode(reg)

    async def async_set_global_mode(self,
                                    opt:const.GlobalMode,
                                    ) -> bool:
        ''' Write global mode '''
        ret = await self.__async_write_register(reg = self._registers[const.REG_KEY_GLOBAL_MODE], val = int(opt))
        if not ret:
            _LOGGER.error('Error writing global mode')
        return ret

    async def async_efficiency(self) -> (bool, const.Efficiency):
        ''' read efficiency/speed '''
        if not self.supports_efficiency:
            return True, const.Efficiency.MED_EFF
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_EFFICIENCY])
        if not ret:
            _LOGGER.error('Error retreive efficiency')
            reg = 1
        return ret, const.Efficiency(reg)

    async def async_set_efficiency(self,
                                    opt:const.GlobalMode,
                                    ) -> bool:
        ''' Write efficiency '''
        if not self.supports_efficiency:
            _LOGGER.warning("Efficiency register is not supported by this Modbus table")
            return False
        ret = await self.__async_write_register(reg = self._registers[const.REG_KEY_EFFICIENCY], val = int(opt))
        if not ret:
            _LOGGER.error('Error writing efficiency')
        return ret

    async def async_communication_config(self) -> (bool, int):
        ''' read Modbus communication frequency and parity '''
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_COMM])
        if not ret:
            _LOGGER.error('Error retreive communication config')
            reg = 0
        return ret, reg

    async def async_modbus_address(self) -> (bool, int):
        ''' read Modbus slave address '''
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_ADDR_MODBUS])
        if not ret:
            _LOGGER.error('Error retreive Modbus address')
            reg = 0
        return ret, reg

    async def async_clim_id(self) -> (bool, int):
        ''' read infrared receiver brand, model and machine number '''
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_CLIM_ID])
        if not ret:
            _LOGGER.error('Error retreive infrared receiver id')
            reg = 0
        return ret, reg

    async def async_engines_throughput(self) -> (bool, list):
        ''' read engines throughput AC1, AC2, AC3, AC4 '''
        engines_lst = []
        regs, ret = await self.__async_read_registers(self._registers[const.REG_KEY_START_FLOW_ENGINE],
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
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_START_FLOW_ENGINE] + (engine_id - 1))
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
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_START_FLOW_STATE_ENGINE] + (engine_id - 1))
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
        ret = await self.__async_write_register(reg = self._registers[const.REG_KEY_START_FLOW_STATE_ENGINE] + (engine_id - 1), val = int(opt))
        if not ret:
            _LOGGER.error('Error writing engine state for id:{}'.format(engine_id))
        return ret

    async def async_engine_order_temp(self,
                                        engine_id:int = 0,
                                        ) -> (bool, float):
        ''' read engine order temperature specified by id '''
        if engine_id < 1 or engine_id > 4:
            raise UnitIdError("Engine id must be between 1 and 4")
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_START_ORDER_TEMP] + (engine_id - 1))
        if not ret:
            _LOGGER.error('Error retreive engine order temp for id:{}'.format(engine_id))
            reg = 0
        return ret, reg / 2

    async def async_engine_orders_temp(self) -> (bool, list):
        ''' read orders temperature for engines : AC1, AC2, AC3, AC4 '''
        engines_lst = []
        regs, ret = await self.__async_read_registers(self._registers[const.REG_KEY_START_ORDER_TEMP], const.NUM_OF_ENGINES)
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
        return ret, const.ZoneRegister((reg >> 1) & 0b1), const.ZoneState(reg & 0b01)

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
