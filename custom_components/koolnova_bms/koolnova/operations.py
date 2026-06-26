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
    """Set debug logger levels without changing Home Assistant handlers.

    Args:
        enabled: Whether debug logging should be enabled.

    Returns:
        None.
    """
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
        """Class constructor

        Args:
            mode: Modbus transport mode to configure.
            timeout: Modbus client timeout in seconds.
            debug: Whether debug logging should be enabled.
            **kwargs: Transport and register-table options.

        Returns:
            None.
        """
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
        """Read one holding register (code 0x03)

        Args:
            reg: Zero-based Modbus register address.

        Returns:
            Tuple of register value and success flag.
        """
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
        """Read holding registers (code 0x03)

        Args:
            start_reg: First zero-based Modbus register address to read.
            count: Number of contiguous registers to read.

        Returns:
            Tuple of register values and success flag.
        """
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
        """Write one register (code 0x06)

        Args:
            reg: Zero-based Modbus register address.
            val: Value to write or set.

        Returns:
            Operation success flag.
        """
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
        """connect to the modbus serial server

        Returns:
            None.
        """
        async with Operations._lock:
            await self._client.connect()

    def connected(self) -> bool:
        """get modbus client status

        Returns:
            True when the underlying Modbus client is connected.
        """
        return self._client.connected

    @staticmethod
    def __validated_int(name:str, value:int, minimum:int, maximum:int) -> int:
        """Validate an integer value against documented Modbus bounds

        Args:
            name: Human-readable field name used in validation errors.
            value: Value to validate.
            minimum: Inclusive minimum accepted value.
            maximum: Inclusive maximum accepted value.

        Returns:
            Validated integer value.
        """
        value = int(value)
        if value < minimum or value > maximum:
            raise ValueError("{} must be between {} and {}".format(name, minimum, maximum))
        return value

    @staticmethod
    def __validated_half_degree_raw(name:str, value:float) -> int:
        """Validate a Celsius value encoded as half-degree Modbus steps.

        Args:
            name: Human-readable field name used in validation errors.
            value: Value to validate.

        Returns:
            Raw half-degree encoded integer value.
        """
        raw = float(value) * 2
        rounded_raw = round(raw)
        if abs(raw - rounded_raw) > 0.000001:
            raise ValueError("{} must use 0.5°C steps".format(name))
        return Operations.__validated_int(name, rounded_raw, 0x00, 0xFF)

    @property
    def supports_efficiency(self) -> bool:
        """Return whether the selected register map supports efficiency.

        Returns:
            True when the selected table version exposes the efficiency register.
        """
        return self._registers[const.REG_KEY_EFFICIENCY] is not None

    def disconnect(self) -> None:
        """close the underlying socket connection

        Returns:
            None.
        """
        if self._client.connected:
            self._client.close()

    async def async_test_communication(self) -> bool:
        """Test communication using a common zone register.

        Returns:
            Operation success flag.
        """
        _, ret = await self.__async_read_register(const.REG_START_ZONE)
        return ret

    async def async_detect_table_version(self) -> (bool, str):
        """Detect the Koolnova Modbus table version.

        Register 40073 is used as the discriminator:
        - v1.0 uses it as AC1 airflow programming, with legal values 1..4.
        - v2.0 uses it as control unit model/software version.

        Returns:
            Tuple of success flag and decoded value.
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

    @staticmethod
    def __bytes_from(raw:int) -> tuple[int, int]:
        """Split one Modbus 16-bit register into its high and low bytes.

        The Koolnova v2 table packs many independent fields into one register.
        Keeping byte extraction here avoids duplicating masks in each decoder.

        Args:
            raw: Raw register value.

        Returns:
            Tuple of decoded integer values.
        """
        return (raw >> 8) & 0xFF, raw & 0xFF

    @staticmethod
    def __signed_16(raw:int) -> int:
        """Decode a signed 16-bit register value.

        Temperature diagnostics such as outdoor and auxiliary NTC values are
        encoded as two's-complement tenths of a degree.

        Args:
            raw: Raw register value.

        Returns:
            Register value.
        """
        if raw & 0x8000:
            raw -= 0x10000
        return raw

    @staticmethod
    def __signed_8(raw:int) -> int:
        """Decode a signed 8-bit value stored in a register byte.

        Some v2 settings pack signed Celsius offsets in the LSB while the MSB
        carries a separate unsigned setting.

        Args:
            raw: Raw register value.

        Returns:
            Register value.
        """
        if raw & 0x80:
            raw -= 0x100
        return raw

    @staticmethod
    def __register_at(registers:list, start_reg:int, address:int) -> int:
        """Return a register value from a contiguous Modbus read.

        Args:
            registers: Values returned by a contiguous Modbus read.
            start_reg: First zero-based Modbus register address to read.
            address: Zero-based Modbus register address to extract.

        Returns:
            Register value.
        """
        return registers[address - start_reg]

    @staticmethod
    def __v2_main_register(registers:list, address:int) -> int:
        """Return a value from the v2 40073-40092 register block.

        This block contains the compact v2 system configuration and diagnostics
        registers. It is contiguous in the official table and safe to read as a
        single Modbus request.

        Args:
            registers: Values returned by a contiguous Modbus read.
            address: Zero-based Modbus register address to extract.

        Returns:
            Register value.
        """
        return Operations.__register_at(
            registers,
            const.REG_V2_MODEL_VERSION,
            address,
        )

    @staticmethod
    def __v2_demand_register(registers:list, address:int) -> int:
        """Return a value from the v2 40107-40123 register block.

        The next logical address, 40124, is not defined in the Koolnova v2
        table, so values after 40123 must be read from the tail block instead.

        Args:
            registers: Values returned by a contiguous Modbus read.
            address: Zero-based Modbus register address to extract.

        Returns:
            Register value.
        """
        return Operations.__register_at(
            registers,
            const.REG_V2_RESERVED_40107,
            address,
        )

    @staticmethod
    def __v2_tail_register(registers:list, address:int) -> int:
        """Return a value from the v2 40125-40126 register block.

        This intentionally starts after the undocumented 40124 gap. Some Modbus
        devices reject a block read crossing an undefined register.

        Args:
            registers: Values returned by a contiguous Modbus read.
            address: Zero-based Modbus register address to extract.

        Returns:
            Register value.
        """
        return Operations.__register_at(
            registers,
            const.REG_V2_START_REQUESTED_TEMP_AVG + const.NUM_REG_V2_REQUESTED_TEMP_AVG,
            address,
        )

    @staticmethod
    def __decode_v2_parameters(raw:int) -> dict:
        """Decode 40074: humidity, antifreeze, ECO/STOP and relay flags.

        Args:
            raw: Raw register value.

        Returns:
            Decoded register values.
        """
        msb, lsb = Operations.__bytes_from(raw)
        return {
            "raw": raw,
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

    @staticmethod
    def __decode_v2_active_modes(raw:int) -> dict:
        """Decode 40075: available or hidden operating modes.

        Args:
            raw: Raw register value.

        Returns:
            Decoded register values.
        """
        msb, lsb = Operations.__bytes_from(raw)
        return {
            "raw": raw,
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

    @staticmethod
    def __decode_v2_temperature_limits(raw:int) -> dict:
        """Decode 40076: max heating and min cooling limits in 0.5 C steps.

        Args:
            raw: Raw register value.

        Returns:
            Decoded register values.
        """
        msb, lsb = Operations.__bytes_from(raw)
        return {
            "raw": raw,
            "msb": msb,
            "lsb": lsb,
            "max_heating_limit": msb / 2,
            "min_cooling_limit": lsb / 2,
        }

    @staticmethod
    def __decode_v2_auto_changeover_humidity(raw:int) -> dict:
        """Decode 40077: auto changeover modes and humidity relay threshold.

        Args:
            raw: Raw register value.

        Returns:
            Decoded register values.
        """
        msb, lsb = Operations.__bytes_from(raw)
        mode_when_above = (msb >> 4) & 0x0F
        mode_when_below = msb & 0x0F
        return {
            "raw": raw,
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

    @staticmethod
    def __decode_v2_system_time(raw:int) -> dict:
        """Decode 40078: weekday, hour and minute stored in bit fields.

        Args:
            raw: Raw register value.

        Returns:
            Decoded register values.
        """
        day = (raw >> 11) & 0x07
        return {
            "raw": raw,
            "reserved_prefix": (raw >> 14) & 0x03,
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
            "hour": (raw >> 6) & 0x1F,
            "minute": raw & 0x3F,
        }

    @staticmethod
    def __decode_v2_external_inputs(raw:int) -> dict:
        """Decode 40079: DIN2 and DIN1 function nibbles.

        Args:
            raw: Raw register value.

        Returns:
            Decoded register values.
        """
        msb, lsb = Operations.__bytes_from(raw)
        return {
            "raw": raw,
            "msb": msb,
            "lsb": lsb,
            "din2_function": (lsb >> 4) & 0x0F,
            "din1_function": lsb & 0x0F,
        }

    @staticmethod
    def __decode_v2_opening_angle(raw:int, base_zone_id:int) -> dict:
        """Decode 40080/40081 opening-angle commands.

        Args:
            raw: Raw register value.
            base_zone_id: First zone represented by the decoded register.

        Returns:
            Decoded register values.
        """
        msb, lsb = Operations.__bytes_from(raw)
        angle_code = (lsb >> 4) & 0x0F
        zone_index = lsb & 0x0F
        return {
            "raw": raw,
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
            "zone_id": zone_index + base_zone_id,
        }

    @staticmethod
    def __decode_v2_valve_mask(raw:int) -> dict:
        """Decode 40085: per-zone pump/valve enable mask.

        Args:
            raw: Raw register value.

        Returns:
            Decoded register values.
        """
        msb, lsb = Operations.__bytes_from(raw)
        enabled_zone_indexes = [
            zone_index
            for zone_index in range(16)
            if raw & (1 << zone_index)
        ]
        return {
            "raw": raw,
            "msb": msb,
            "lsb": lsb,
            "enabled_zone_indexes": enabled_zone_indexes,
            "zone_pump_enabled": {
                zone_index: zone_index in enabled_zone_indexes
                for zone_index in range(16)
            },
        }

    @staticmethod
    def __decode_v2_pump_delay_valve_offset(raw:int) -> dict:
        """Decode 40086: valve origin offset and pump delay seconds.

        Args:
            raw: Raw register value.

        Returns:
            Decoded register values.
        """
        msb, lsb = Operations.__bytes_from(raw)
        return {
            "raw": raw,
            "msb": msb,
            "lsb": lsb,
            "valve_origin_offset": msb,
            "pump_delay_seconds": lsb,
            "pump_delay_seconds_valid": 60 <= lsb <= 255,
        }

    @staticmethod
    def __decode_v2_immersion_heater(raw:int) -> dict:
        """Decode 40087: immersion heater delay and signed activation temp.

        Args:
            raw: Raw register value.

        Returns:
            Decoded register values.
        """
        msb, lsb = Operations.__bytes_from(raw)
        return {
            "raw": raw,
            "msb": msb,
            "lsb": lsb,
            "activation_delay_minutes": msb,
            "activation_temperature_celsius": Operations.__signed_8(lsb),
        }

    @staticmethod
    def __decode_v2_thermostat_block(raw:int) -> dict:
        """Decode 40088: thermostat blocking level.

        Args:
            raw: Raw register value.

        Returns:
            Decoded register values.
        """
        msb, lsb = Operations.__bytes_from(raw)
        return {
            "raw": raw,
            "msb": msb,
            "lsb": lsb,
            "msb_expected_zero": msb == 0,
            "block_level": lsb,
            "block_level_valid": 0x00 <= lsb <= 0x0F,
            "no_block": lsb == 0x00,
            "total_block": lsb == 0x0F,
        }

    @staticmethod
    def __decode_v2_auto_mode(raw:int) -> dict:
        """Decode 40089: cooling and heating water thresholds.

        Args:
            raw: Raw register value.

        Returns:
            Decoded register values.
        """
        msb, lsb = Operations.__bytes_from(raw)
        return {
            "raw": raw,
            "msb": msb,
            "lsb": lsb,
            "cooling_water_threshold_celsius": msb,
            "heating_water_threshold_celsius": lsb,
        }

    @staticmethod
    def __decode_v2_mixing_valve_ambient_temperatures(raw:int) -> dict:
        """Decode 40090: mixing-valve ambient temperature limits.

        Args:
            raw: Raw register value.

        Returns:
            Decoded register values.
        """
        msb, lsb = Operations.__bytes_from(raw)
        lower_ambient_temperature = Operations.__signed_8(lsb)
        return {
            "raw": raw,
            "msb": msb,
            "lsb": lsb,
            "upper_ambient_temperature_celsius": msb,
            "upper_ambient_temperature_valid": 25 <= msb <= 45,
            "lower_ambient_temperature_celsius": lower_ambient_temperature,
            "lower_ambient_temperature_valid": -20 <= lower_ambient_temperature <= 30,
        }

    @staticmethod
    def __decode_v2_mixing_valve_water_temperatures(raw:int) -> dict:
        """Decode 40091: mixing-valve water temperature limits.

        Args:
            raw: Raw register value.

        Returns:
            Decoded register values.
        """
        msb, lsb = Operations.__bytes_from(raw)
        return {
            "raw": raw,
            "msb": msb,
            "lsb": lsb,
            "upper_water_temperature_celsius": msb,
            "upper_water_temperature_valid": 25 <= msb <= 45,
            "lower_water_temperature_celsius": lsb,
            "lower_water_temperature_valid": 25 <= lsb <= 45,
        }

    @staticmethod
    def __decode_v2_mixing_valve_mode_info(raw:int) -> dict:
        """Decode 40092: mixing-valve mode and fixed supply temperatures.

        Args:
            raw: Raw register value.

        Returns:
            Decoded register values.
        """
        msb, lsb = Operations.__bytes_from(raw)
        safety_factor_code = (raw >> 14) & 0x03
        mode = (raw >> 12) & 0x03
        cooling_supply_temperature = (raw >> 6) & 0x3F
        heating_supply_temperature = raw & 0x3F
        return {
            "raw": raw,
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

    @staticmethod
    def __decode_area_registers(regs:list, offset:int = 0) -> dict | None:
        """Decode one Koolnova zone from a four-register area block.

        Args:
            regs: Register values containing one or more area blocks.
            offset: Index of the first register for the area inside `regs`.

        Returns:
            Decoded area dictionary when the zone is registered; None otherwise.
        """
        lock_reg = regs[offset + const.REG_LOCK_ZONE]
        register = const.ZoneRegister((lock_reg >> 1) & 0b1)
        if register == const.ZoneRegister.REGISTER_OFF:
            return None

        state_and_flow = regs[offset + const.REG_STATE_AND_FLOW]
        return {
            "state": const.ZoneState(lock_reg & 0b01),
            "register": register,
            "fan": const.ZoneFanMode((state_and_flow & 0xF0) >> 4),
            "clim": const.ZoneClimMode(state_and_flow & 0x0F),
            "order_temp": regs[offset + const.REG_TEMP_ORDER] / 2,
            "real_temp": regs[offset + const.REG_TEMP_REAL] / 2,
        }

    @staticmethod
    def __zone_id_ranges(zone_ids:list[int]) -> list[tuple[int, int]]:
        """Group one-based zone ids into contiguous ranges.

        Args:
            zone_ids: One-based zone ids to read.

        Returns:
            List of inclusive start/end ranges.
        """
        ranges = []
        sorted_zone_ids = sorted(set(zone_ids))
        if not sorted_zone_ids:
            return ranges

        range_start = sorted_zone_ids[0]
        previous_zone_id = range_start
        for zone_id in sorted_zone_ids[1:]:
            if zone_id == previous_zone_id + 1:
                previous_zone_id = zone_id
                continue

            ranges.append((range_start, previous_zone_id))
            range_start = zone_id
            previous_zone_id = zone_id

        ranges.append((range_start, previous_zone_id))
        return ranges

    async def async_v2_model_version(self) -> (bool, int):
        """Read 40073: control unit model and software version.

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_MODEL_VERSION)
        if not ret:
            _LOGGER.error('Error retreive v2 model version')
            reg = 0
        return ret, reg

    async def async_v2_parameters(self) -> (bool, dict):
        """Read 40074: system parameters.

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_PARAMETERS)
        if not ret:
            _LOGGER.error('Error retreive v2 parameters')
            return ret, {}
        return ret, Operations.__decode_v2_parameters(reg)

    async def async_set_v2_parameters(self,
                                        raw:int,
                                        ) -> bool:
        """write 40074: system parameters

        Args:
            raw: Raw register value.

        Returns:
            Operation success flag.
        """
        raw = Operations.__validated_int("raw", raw, 0x0000, 0xFFFF)
        ret = await self.__async_write_register(reg = const.REG_V2_PARAMETERS, val = int(raw))
        if not ret:
            _LOGGER.error('Error writing v2 parameters')
        return ret

    async def async_v2_active_modes(self) -> (bool, dict):
        """read 40075: active modes

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_ACTIVE_MODES)
        if not ret:
            _LOGGER.error('Error retreive v2 active modes')
            return ret, {}
        return ret, Operations.__decode_v2_active_modes(reg)

    async def async_set_v2_active_modes(self,
                                        raw:int,
                                        ) -> bool:
        """write 40075: active modes

        Args:
            raw: Raw register value.

        Returns:
            Operation success flag.
        """
        raw = Operations.__validated_int("raw", raw, 0x0000, 0xFFFF)
        if raw & 0x0080:
            raise ValueError("raw bit 7 of LSB must be 0")
        ret = await self.__async_write_register(reg = const.REG_V2_ACTIVE_MODES, val = int(raw))
        if not ret:
            _LOGGER.error('Error writing v2 active modes')
        return ret

    async def async_v2_temperature_limits(self) -> (bool, dict):
        """read 40076: temperature limits

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_TEMPERATURE_LIMITS)
        if not ret:
            _LOGGER.error('Error retreive v2 temperature limits')
            return ret, {}
        return ret, Operations.__decode_v2_temperature_limits(reg)

    async def async_set_v2_temperature_limits(self,
                                                max_heating_limit:float,
                                                min_cooling_limit:float,
                                                ) -> bool:
        """write 40076: temperature limits

        Args:
            max_heating_limit: Maximum heating limit in Celsius.
            min_cooling_limit: Minimum cooling limit in Celsius.

        Returns:
            Operation success flag.
        """
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
        """read 40077: automatic changeover modes and humidity control

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_AUTO_CHANGEOVER_HUMIDITY)
        if not ret:
            _LOGGER.error('Error retreive v2 auto changeover humidity')
            return ret, {}
        return ret, Operations.__decode_v2_auto_changeover_humidity(reg)

    async def async_set_v2_auto_changeover_humidity(self,
                                                    mode_when_water_above_threshold:int,
                                                    mode_when_water_below_threshold:int,
                                                    humidity_relay_threshold:int,
                                                    ) -> bool:
        """write 40077: automatic changeover modes and humidity control

        Args:
            mode_when_water_above_threshold: Mode code used when water is above the threshold.
            mode_when_water_below_threshold: Mode code used when water is below the threshold.
            humidity_relay_threshold: Humidity relay threshold value.

        Returns:
            Operation success flag.
        """
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
        """read 40078: system time

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_SYSTEM_TIME)
        if not ret:
            _LOGGER.error('Error retreive v2 system time')
            return ret, {}
        return ret, Operations.__decode_v2_system_time(reg)

    async def async_set_v2_system_time(self,
                                        day:int,
                                        hour:int,
                                        minute:int,
                                        ) -> bool:
        """write 40078: system time

        Args:
            day: Weekday value encoded by the controller.
            hour: Hour value to encode.
            minute: Minute value to encode.

        Returns:
            Operation success flag.
        """
        day = Operations.__validated_int("day", day, 1, 7)
        hour = Operations.__validated_int("hour", hour, 0, 23)
        minute = Operations.__validated_int("minute", minute, 0, 59)
        val = (day << 11) | (hour << 6) | minute
        ret = await self.__async_write_register(reg = const.REG_V2_SYSTEM_TIME, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 system time')
        return ret

    async def async_v2_external_inputs(self) -> (bool, dict):
        """read 40079: external inputs

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_EXTERNAL_INPUTS)
        if not ret:
            _LOGGER.error('Error retreive v2 external inputs')
            return ret, {}
        return ret, Operations.__decode_v2_external_inputs(reg)

    async def async_set_v2_external_inputs(self,
                                            din2_function:int,
                                            din1_function:int,
                                            ) -> bool:
        """write 40079: external inputs

        Args:
            din2_function: DIN2 input function code.
            din1_function: DIN1 input function code.

        Returns:
            Operation success flag.
        """
        din2_function = Operations.__validated_int("din2_function", din2_function, 0x00, 0x0F)
        din1_function = Operations.__validated_int("din1_function", din1_function, 0x00, 0x0F)
        val = ((din2_function << 4) | din1_function)
        ret = await self.__async_write_register(reg = const.REG_V2_EXTERNAL_INPUTS, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 external inputs')
        return ret

    async def async_v2_opening_angle_z1_z8(self) -> (bool, dict):
        """read 40080: opening angle for zones Z1 to Z8

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_OPENING_ANGLE_Z1_Z8)
        if not ret:
            _LOGGER.error('Error retreive v2 opening angle Z1 to Z8')
            return ret, {}
        return ret, Operations.__decode_v2_opening_angle(reg, 1)

    async def async_set_v2_opening_angle_z1_z8(self,
                                                angle_code:int,
                                                zone_index:int,
                                                ) -> bool:
        """write 40080: opening angle for zones Z1 to Z8

        Args:
            angle_code: Opening angle code.
            zone_index: Zero-based zone index for the target register group.

        Returns:
            Operation success flag.
        """
        angle_code = Operations.__validated_int("angle_code", angle_code, 0x00, 0x03)
        zone_index = Operations.__validated_int("zone_index", zone_index, 0, 7)
        val = ((angle_code << 4) | zone_index)
        ret = await self.__async_write_register(reg = const.REG_V2_OPENING_ANGLE_Z1_Z8, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 opening angle Z1 to Z8')
        return ret

    async def async_v2_opening_angle_z9_z16(self) -> (bool, dict):
        """read 40081: opening angle for zones Z9 to Z16

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_OPENING_ANGLE_Z9_Z16)
        if not ret:
            _LOGGER.error('Error retreive v2 opening angle Z9 to Z16')
            return ret, {}
        return ret, Operations.__decode_v2_opening_angle(reg, 9)

    async def async_set_v2_opening_angle_z9_z16(self,
                                                angle_code:int,
                                                zone_index:int,
                                                ) -> bool:
        """write 40081: opening angle for zones Z9 to Z16

        Args:
            angle_code: Opening angle code.
            zone_index: Zero-based zone index for the target register group.

        Returns:
            Operation success flag.
        """
        angle_code = Operations.__validated_int("angle_code", angle_code, 0x00, 0x03)
        zone_index = Operations.__validated_int("zone_index", zone_index, 8, 15) - 8
        val = ((angle_code << 4) | zone_index)
        ret = await self.__async_write_register(reg = const.REG_V2_OPENING_ANGLE_Z9_Z16, val = val)
        if not ret:
            _LOGGER.error('Error writing v2 opening angle Z9 to Z16')
        return ret

    async def async_v2_floor_water_temperature(self) -> (bool, float):
        """read 40082: radiant floor water NTC temperature

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_FLOOR_WATER_TEMPERATURE)
        if not ret:
            _LOGGER.error('Error retreive v2 floor water temperature')
            return ret, 0.0
        return ret, reg / 10

    async def async_v2_outdoor_temperature(self) -> (bool, float):
        """read 40083: outdoor ambient temperature

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_OUTDOOR_TEMPERATURE)
        if not ret:
            _LOGGER.error('Error retreive v2 outdoor temperature')
            return ret, 0.0
        return ret, Operations.__signed_16(reg) / 10

    async def async_v2_aux_temperature(self) -> (bool, float):
        """read 40084: auxiliary NTC temperature

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_AUX_TEMPERATURE)
        if not ret:
            _LOGGER.error('Error retreive v2 auxiliary temperature')
            return ret, 0.0
        return ret, Operations.__signed_16(reg) / 10

    async def async_v2_valve_mask(self) -> (bool, dict):
        """read 40085: valve mask

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_VALVE_MASK)
        if not ret:
            _LOGGER.error('Error retreive v2 valve mask')
            return ret, {}
        return ret, Operations.__decode_v2_valve_mask(reg)

    async def async_set_v2_valve_mask(self,
                                        raw:int,
                                        ) -> bool:
        """write 40085: valve mask

        Args:
            raw: Raw register value.

        Returns:
            Operation success flag.
        """
        raw = Operations.__validated_int("raw", raw, 0x0000, 0xFFFF)
        ret = await self.__async_write_register(reg = const.REG_V2_VALVE_MASK, val = raw)
        if not ret:
            _LOGGER.error('Error writing v2 valve mask')
        return ret

    async def async_v2_pump_delay_valve_offset(self) -> (bool, dict):
        """read 40086: pump delay and valve offset

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_PUMP_DELAY_VALVE_OFFSET)
        if not ret:
            _LOGGER.error('Error retreive v2 pump delay valve offset')
            return ret, {}
        return ret, Operations.__decode_v2_pump_delay_valve_offset(reg)

    async def async_set_v2_pump_delay_valve_offset(self,
                                                    valve_origin_offset:int,
                                                    pump_delay_seconds:int,
                                                    ) -> bool:
        """write 40086: pump delay and valve offset

        Args:
            valve_origin_offset: Valve origin offset value.
            pump_delay_seconds: Pump delay in seconds.

        Returns:
            Operation success flag.
        """
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
        """read 40087: immersion heater

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_IMMERSION_HEATER)
        if not ret:
            _LOGGER.error('Error retreive v2 immersion heater')
            return ret, {}
        return ret, Operations.__decode_v2_immersion_heater(reg)

    async def async_set_v2_immersion_heater(self,
                                            activation_delay_minutes:int,
                                            activation_temperature_celsius:int,
                                            ) -> bool:
        """write 40087: immersion heater

        Args:
            activation_delay_minutes: Immersion heater activation delay in minutes.
            activation_temperature_celsius: Immersion heater activation temperature in Celsius.

        Returns:
            Operation success flag.
        """
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
        """read 40088: thermostat block

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_THERMOSTAT_BLOCK)
        if not ret:
            _LOGGER.error('Error retreive v2 thermostat block')
            return ret, {}
        return ret, Operations.__decode_v2_thermostat_block(reg)

    async def async_set_v2_thermostat_block(self,
                                            block_level:int,
                                            ) -> bool:
        """write 40088: thermostat block

        Args:
            block_level: Thermostat block level.

        Returns:
            Operation success flag.
        """
        block_level = Operations.__validated_int("block_level", block_level, 0x00, 0x0F)
        ret = await self.__async_write_register(reg = const.REG_V2_THERMOSTAT_BLOCK, val = block_level)
        if not ret:
            _LOGGER.error('Error writing v2 thermostat block')
        return ret

    async def async_v2_auto_mode(self) -> (bool, dict):
        """read 40089: automatic mode

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_AUTO_MODE)
        if not ret:
            _LOGGER.error('Error retreive v2 auto mode')
            return ret, {}
        return ret, Operations.__decode_v2_auto_mode(reg)

    async def async_set_v2_auto_mode(self,
                                    cooling_water_threshold_celsius:int,
                                    heating_water_threshold_celsius:int,
                                    ) -> bool:
        """write 40089: automatic mode

        Args:
            cooling_water_threshold_celsius: Cooling water threshold in Celsius.
            heating_water_threshold_celsius: Heating water threshold in Celsius.

        Returns:
            Operation success flag.
        """
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
        """read 40090: ambient temperatures for mixing valve control

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_MIXING_VALVE_AMBIENT_TEMPERATURES)
        if not ret:
            _LOGGER.error('Error retreive v2 mixing valve ambient temperatures')
            return ret, {}
        return ret, Operations.__decode_v2_mixing_valve_ambient_temperatures(reg)

    async def async_set_v2_mixing_valve_ambient_temperatures(self,
                                                            upper_ambient_temperature_celsius:int,
                                                            lower_ambient_temperature_celsius:int,
                                                            ) -> bool:
        """write 40090: ambient temperatures for mixing valve control

        Args:
            upper_ambient_temperature_celsius: Upper ambient temperature in Celsius.
            lower_ambient_temperature_celsius: Lower ambient temperature in Celsius.

        Returns:
            Operation success flag.
        """
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
        """read 40091: water temperatures for mixing valve control

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_MIXING_VALVE_WATER_TEMPERATURES)
        if not ret:
            _LOGGER.error('Error retreive v2 mixing valve water temperatures')
            return ret, {}
        return ret, Operations.__decode_v2_mixing_valve_water_temperatures(reg)

    async def async_set_v2_mixing_valve_water_temperatures(self,
                                                            upper_water_temperature_celsius:int,
                                                            lower_water_temperature_celsius:int,
                                                            ) -> bool:
        """write 40091: water temperatures for mixing valve control

        Args:
            upper_water_temperature_celsius: Upper water temperature in Celsius.
            lower_water_temperature_celsius: Lower water temperature in Celsius.

        Returns:
            Operation success flag.
        """
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
        """read 40092: mixing valve mode information

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_MIXING_VALVE_MODE_INFO)
        if not ret:
            _LOGGER.error('Error retreive v2 mixing valve mode info')
            return ret, {}
        return ret, Operations.__decode_v2_mixing_valve_mode_info(reg)

    async def async_set_v2_mixing_valve_mode_info(self,
                                                    safety_factor_code:int,
                                                    mode:int,
                                                    cooling_supply_temperature_celsius:int,
                                                    heating_supply_temperature_celsius:int,
                                                    ) -> bool:
        """write 40092: mixing valve mode information

        Args:
            safety_factor_code: Mixing-valve safety factor code.
            mode: Modbus transport mode to configure.
            cooling_supply_temperature_celsius: Cooling supply temperature in Celsius.
            heating_supply_temperature_celsius: Heating supply temperature in Celsius.

        Returns:
            Operation success flag.
        """
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
        """read 40107: reserved register

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_RESERVED_40107)
        if not ret:
            _LOGGER.error('Error retreive v2 reserved register 40107')
            reg = 0
        return ret, reg

    async def async_v2_radiant_floor_demand_count(self) -> (bool, int):
        """read 40111: radiant floor heating thermostat demand count

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_RADIANT_FLOOR_DEMAND_COUNT)
        if not ret:
            _LOGGER.error('Error retreive v2 radiant floor demand count')
            reg = 0
        return ret, reg

    async def async_v2_ac3_air_demand_count(self) -> (bool, int):
        """read 40112: AC3 air thermostat demand count

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_AC3_AIR_DEMAND_COUNT)
        if not ret:
            _LOGGER.error('Error retreive v2 AC3 air demand count')
            reg = 0
        return ret, reg

    async def async_v2_connected_volumes(self) -> (bool, list):
        """read connected thermostat volume sum for AC1, AC2, AC3 and AC4

        Returns:
            Tuple of success flag and decoded value.
        """
        regs, ret = await self.__async_read_registers(
            const.REG_V2_START_CONNECTED_VOLUME,
            const.NUM_REG_V2_CONNECTED_VOLUME,
        )
        if not ret:
            _LOGGER.error('Error retreive v2 connected volumes')
            regs = []
        return ret, regs

    async def async_v2_active_volumes(self) -> (bool, list):
        """read active thermostat demand volume sum for AC1, AC2, AC3 and AC4

        Returns:
            Tuple of success flag and decoded value.
        """
        regs, ret = await self.__async_read_registers(
            const.REG_V2_START_ACTIVE_VOLUME,
            const.NUM_REG_V2_ACTIVE_VOLUME,
        )
        if not ret:
            _LOGGER.error('Error retreive v2 active volumes')
            regs = []
        return ret, regs

    async def async_v2_requested_temp_avgs(self) -> (bool, list):
        """read requested setpoint temperature average for AC1, AC2, AC3 and AC4

        Returns:
            Tuple of success flag and decoded value.
        """
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
        return True, [reg / 2 for reg in regs]

    async def async_v2_efficiency_ac3_speed(self) -> (bool, int):
        """read 40126: MSB EFI and LSB AC3 speed

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(const.REG_V2_EFFICIENCY_AC3_SPEED)
        if not ret:
            _LOGGER.error('Error retreive v2 efficiency AC3 speed')
            reg = 0
        return ret, reg

    async def async_discover_registered_areas(self) -> list:
        """Discover all areas registered to the system

        Returns:
            Decoded values.
        """
        regs, ret = await self.__async_read_registers(start_reg=const.REG_START_ZONE,
                                                        count=const.NB_ZONE_MAX * const.NUM_REG_PER_ZONE)
        if not ret:
            raise ReadRegistersError("Read holding regsiter error")
        zones_lst = []
        for area_idx in range(const.NB_ZONE_MAX):
            offset = area_idx * const.NUM_REG_PER_ZONE
            zone_dict = self.__decode_area_registers(regs, offset)
            if zone_dict is None:
                continue
            zone_dict["id"] = area_idx + 1
            zones_lst.append(zone_dict)
        return zones_lst

    async def async_area_registered(self,
                                    zone_id:int = 0,
                                    ) -> (bool, dict):
        """Get Area status from id

        Args:
            zone_id: One-based Koolnova zone id.

        Returns:
            Tuple of success flag and decoded value.
        """
        #_LOGGER.debug("Area : {}".format(zone_id))
        if zone_id > const.NB_ZONE_MAX or zone_id == 0:
            raise ZoneIdError('Zone Id must be between 1 to {}'.format(const.NB_ZONE_MAX))
        regs, ret = await self.__async_read_registers(start_reg = const.REG_START_ZONE + (4 * (zone_id - 1)),
                                                count = const.NUM_REG_PER_ZONE)
        if not ret:
            raise ReadRegistersError("Error reading holding register")
        zone_dict = self.__decode_area_registers(regs)
        if zone_dict is None:
            _LOGGER.warning("Zone with id: {} is not registered".format(zone_id))
            return False, {}

        return True, zone_dict

    async def async_areas_registered(self,
                                    zone_ids:list[int] | None = None,
                                    ) -> (bool, dict):
        """Get values for registered areas from zone register block reads.

        Args:
            zone_ids: Optional one-based zone ids to refresh. When omitted, all
                16 possible zones are scanned. Contiguous requested zones are
                grouped into the same Modbus read.

        Returns:
            Tuple of success flag and dictionary keyed by one-based zone id.
        """
        areas:dict = {}
        if zone_ids is None:
            zone_ids = list(range(1, const.NB_ZONE_MAX + 1))

        for zone_id in zone_ids:
            if zone_id < 1 or zone_id > const.NB_ZONE_MAX:
                raise ZoneIdError('Zone Id must be between 1 to {}'.format(const.NB_ZONE_MAX))

        for start_zone_id, end_zone_id in self.__zone_id_ranges(zone_ids):
            start_reg = const.REG_START_ZONE + (
                const.NUM_REG_PER_ZONE * (start_zone_id - 1)
            )
            count = const.NUM_REG_PER_ZONE * (end_zone_id - start_zone_id + 1)
            regs, ret = await self.__async_read_registers(
                start_reg = start_reg,
                count = count,
            )
            if not ret:
                raise ReadRegistersError("Error reading holding register")

            for zone_id in range(start_zone_id, end_zone_id + 1):
                offset = const.NUM_REG_PER_ZONE * (zone_id - start_zone_id)
                area = self.__decode_area_registers(regs, offset)
                if area is None:
                    continue

                areas[zone_id] = area
        return True, areas

    async def async_set_debug(self, val:bool) -> bool:
        """Set/Reset Debug Mode

        Args:
            val: Value to write or set.

        Returns:
            Operation success flag.
        """
        _set_debug_logging(val)
        return True

    async def async_system_status(self) -> (bool, const.SysState):
        """Read system status register

        Returns:
            (bool, const.SysState) value.
        """
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_SYS_STATE])
        if not ret:
            _LOGGER.error('Error retreive system status')
            reg = 0
        return ret, const.SysState(reg)

    async def async_set_system_status(self,
                                        opt:const.SysState,
                                        ) -> bool:
        """Write system status

        Args:
            opt: Enum value to write.

        Returns:
            Operation success flag.
        """
        ret = await self.__async_write_register(reg = self._registers[const.REG_KEY_SYS_STATE], val = int(opt))
        if not ret:
            _LOGGER.error('Error writing system status')
        return ret

    async def async_global_mode(self) -> (bool, const.GlobalMode):
        """Read global mode

        Returns:
            (bool, const.GlobalMode) value.
        """
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_GLOBAL_MODE])
        if not ret:
            _LOGGER.error('Error retreive global mode')
            reg = 1
        return ret, const.GlobalMode(reg)

    async def async_set_global_mode(self,
                                    opt:const.GlobalMode,
                                    ) -> bool:
        """Write global mode

        Args:
            opt: Enum value to write.

        Returns:
            Operation success flag.
        """
        ret = await self.__async_write_register(reg = self._registers[const.REG_KEY_GLOBAL_MODE], val = int(opt))
        if not ret:
            _LOGGER.error('Error writing global mode')
        return ret

    async def async_efficiency(self) -> (bool, const.Efficiency):
        """read efficiency/speed

        Returns:
            (bool, const.Efficiency) value.
        """
        if not self.supports_efficiency:
            return True, const.Efficiency.MED_EFF
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_EFFICIENCY])
        if not ret:
            _LOGGER.error('Error retreive efficiency')
            reg = 1
        return ret, const.Efficiency(reg)

    async def async_system_snapshot(self) -> (bool, dict):
        """Read common system registers as one contiguous snapshot.

        This covers the shared V1/V2 system area from communication settings to
        global HVAC mode. V2 does not expose the legacy efficiency register, so
        the returned efficiency falls back to MED_EFF for that table.

        Returns:
            Tuple of success flag and decoded value.
        """
        start_reg = self._registers[const.REG_KEY_COMM]
        end_reg = self._registers[const.REG_KEY_GLOBAL_MODE]
        regs, ret = await self.__async_read_registers(start_reg, end_reg - start_reg + 1)
        if not ret:
            _LOGGER.error('Error retreive system snapshot')
            return ret, {}

        values = {
            "communication_config": Operations.__register_at(
                regs,
                start_reg,
                self._registers[const.REG_KEY_COMM],
            ),
            "modbus_address": Operations.__register_at(
                regs,
                start_reg,
                self._registers[const.REG_KEY_ADDR_MODBUS],
            ),
            "infrared_receiver_id": Operations.__register_at(
                regs,
                start_reg,
                self._registers[const.REG_KEY_CLIM_ID],
            ),
            "system_status": const.SysState(Operations.__register_at(
                regs,
                start_reg,
                self._registers[const.REG_KEY_SYS_STATE],
            )),
            "global_mode": const.GlobalMode(Operations.__register_at(
                regs,
                start_reg,
                self._registers[const.REG_KEY_GLOBAL_MODE],
            )),
            "efficiency": const.Efficiency.MED_EFF,
        }
        if self.supports_efficiency:
            values["efficiency"] = const.Efficiency(Operations.__register_at(
                regs,
                start_reg,
                self._registers[const.REG_KEY_EFFICIENCY],
            ))
        return True, values

    async def async_engines_snapshot(self) -> (bool, list):
        """Read all engine throughput, order temperature and state registers.

        The AC1-AC4 engine registers are contiguous in both V1 and V2 maps:
        throughput block, order temperature block, then flow-state block. A
        single block read avoids twelve unit reads during every coordinator
        refresh.

        Returns:
            Tuple of success flag and decoded value.
        """
        start_reg = self._registers[const.REG_KEY_START_FLOW_ENGINE]
        end_reg = (
            self._registers[const.REG_KEY_START_FLOW_STATE_ENGINE]
            + const.NUM_OF_ENGINES
            - 1
        )
        regs, ret = await self.__async_read_registers(start_reg, end_reg - start_reg + 1)
        if not ret:
            _LOGGER.error('Error retreive engines snapshot')
            return ret, []

        engines = []
        for engine_index in range(const.NUM_OF_ENGINES):
            engines.append({
                "throughput": Operations.__register_at(
                    regs,
                    start_reg,
                    self._registers[const.REG_KEY_START_FLOW_ENGINE] + engine_index,
                ),
                "order_temp": Operations.__register_at(
                    regs,
                    start_reg,
                    self._registers[const.REG_KEY_START_ORDER_TEMP] + engine_index,
                ) / 2,
                "state": const.FlowEngine(
                    Operations.__register_at(
                        regs,
                        start_reg,
                        (
                            self._registers[const.REG_KEY_START_FLOW_STATE_ENGINE]
                            + engine_index
                        ),
                    )
                ),
            })
        return True, engines

    async def async_v2_registers_snapshot(self) -> (bool, dict):
        """Read Koolnova 2.0 advanced registers using safe block reads.

        The v2 table has one compact contiguous block from 40073 to 40092, then
        demand/volume diagnostics around 40107 to 40126. Register 40124 is not
        defined in the official table, so the latter range is deliberately split
        into 40107-40123 and 40125-40126 to avoid crossing that gap.

        Returns:
            Tuple of success flag and decoded value.
        """
        regs_main, ret = await self.__async_read_registers(
            const.REG_V2_MODEL_VERSION,
            const.REG_V2_MIXING_VALVE_MODE_INFO - const.REG_V2_MODEL_VERSION + 1,
        )
        if not ret:
            _LOGGER.error('Error retreive v2 40073-40092 snapshot')
            return ret, {}

        demand_start = const.REG_V2_RESERVED_40107
        demand_end = (
            const.REG_V2_START_REQUESTED_TEMP_AVG
            + const.NUM_REG_V2_REQUESTED_TEMP_AVG
            - 2
        )
        regs_demand, ret = await self.__async_read_registers(
            demand_start,
            demand_end - demand_start + 1,
        )
        if not ret:
            _LOGGER.error('Error retreive v2 40107-40123 snapshot')
            return ret, {}

        # 40124 is not defined in the v2 table, so keep it out of block reads.
        tail_start = (
            const.REG_V2_START_REQUESTED_TEMP_AVG
            + const.NUM_REG_V2_REQUESTED_TEMP_AVG
        )
        tail_end = const.REG_V2_EFFICIENCY_AC3_SPEED
        regs_tail, ret = await self.__async_read_registers(
            tail_start,
            tail_end - tail_start + 1,
        )
        if not ret:
            _LOGGER.error('Error retreive v2 40125-40126 snapshot')
            return ret, {}

        values = {
            "40073_model_version": Operations.__v2_main_register(
                regs_main,
                const.REG_V2_MODEL_VERSION,
            ),
            "40074_parameters": Operations.__decode_v2_parameters(
                Operations.__v2_main_register(
                    regs_main,
                    const.REG_V2_PARAMETERS,
                )
            ),
            "40075_active_modes": Operations.__decode_v2_active_modes(
                Operations.__v2_main_register(
                    regs_main,
                    const.REG_V2_ACTIVE_MODES,
                )
            ),
            "40076_temperature_limits": Operations.__decode_v2_temperature_limits(
                Operations.__v2_main_register(
                    regs_main,
                    const.REG_V2_TEMPERATURE_LIMITS,
                )
            ),
            "40077_auto_changeover_humidity": (
                Operations.__decode_v2_auto_changeover_humidity(
                    Operations.__v2_main_register(
                        regs_main,
                        const.REG_V2_AUTO_CHANGEOVER_HUMIDITY,
                    )
                )
            ),
            "40078_system_time": Operations.__decode_v2_system_time(
                Operations.__v2_main_register(
                    regs_main,
                    const.REG_V2_SYSTEM_TIME,
                )
            ),
            "40079_external_inputs": Operations.__decode_v2_external_inputs(
                Operations.__v2_main_register(
                    regs_main,
                    const.REG_V2_EXTERNAL_INPUTS,
                )
            ),
            "40080_opening_angle_z1_z8": Operations.__decode_v2_opening_angle(
                Operations.__v2_main_register(
                    regs_main,
                    const.REG_V2_OPENING_ANGLE_Z1_Z8,
                ),
                1,
            ),
            "40081_opening_angle_z9_z16": Operations.__decode_v2_opening_angle(
                Operations.__v2_main_register(
                    regs_main,
                    const.REG_V2_OPENING_ANGLE_Z9_Z16,
                ),
                9,
            ),
            "40082_floor_water_temperature": (
                Operations.__v2_main_register(
                    regs_main,
                    const.REG_V2_FLOOR_WATER_TEMPERATURE,
                ) / 10
            ),
            "40083_outdoor_temperature": (
                Operations.__signed_16(
                    Operations.__v2_main_register(
                        regs_main,
                        const.REG_V2_OUTDOOR_TEMPERATURE,
                    )
                ) / 10
            ),
            "40084_aux_temperature": (
                Operations.__signed_16(
                    Operations.__v2_main_register(
                        regs_main,
                        const.REG_V2_AUX_TEMPERATURE,
                    )
                ) / 10
            ),
            "40085_valve_mask": Operations.__decode_v2_valve_mask(
                Operations.__v2_main_register(
                    regs_main,
                    const.REG_V2_VALVE_MASK,
                )
            ),
            "40086_pump_delay_valve_offset": (
                Operations.__decode_v2_pump_delay_valve_offset(
                    Operations.__v2_main_register(
                        regs_main,
                        const.REG_V2_PUMP_DELAY_VALVE_OFFSET,
                    )
                )
            ),
            "40087_immersion_heater": Operations.__decode_v2_immersion_heater(
                Operations.__v2_main_register(
                    regs_main,
                    const.REG_V2_IMMERSION_HEATER,
                )
            ),
            "40088_thermostat_block": Operations.__decode_v2_thermostat_block(
                Operations.__v2_main_register(
                    regs_main,
                    const.REG_V2_THERMOSTAT_BLOCK,
                )
            ),
            "40089_auto_mode": Operations.__decode_v2_auto_mode(
                Operations.__v2_main_register(
                    regs_main,
                    const.REG_V2_AUTO_MODE,
                )
            ),
            "40090_mixing_valve_ambient_temperatures": (
                Operations.__decode_v2_mixing_valve_ambient_temperatures(
                    Operations.__v2_main_register(
                        regs_main,
                        const.REG_V2_MIXING_VALVE_AMBIENT_TEMPERATURES,
                    )
                )
            ),
            "40091_mixing_valve_water_temperatures": (
                Operations.__decode_v2_mixing_valve_water_temperatures(
                    Operations.__v2_main_register(
                        regs_main,
                        const.REG_V2_MIXING_VALVE_WATER_TEMPERATURES,
                    )
                )
            ),
            "40092_mixing_valve_mode_info": (
                Operations.__decode_v2_mixing_valve_mode_info(
                    Operations.__v2_main_register(
                        regs_main,
                        const.REG_V2_MIXING_VALVE_MODE_INFO,
                    )
                )
            ),
            "40107_reserved": Operations.__v2_demand_register(
                regs_demand,
                const.REG_V2_RESERVED_40107,
            ),
            "40111_radiant_floor_demand_count": Operations.__v2_demand_register(
                regs_demand,
                const.REG_V2_RADIANT_FLOOR_DEMAND_COUNT
            ),
            "40112_ac3_air_demand_count": Operations.__v2_demand_register(
                regs_demand,
                const.REG_V2_AC3_AIR_DEMAND_COUNT
            ),
            "40126_efficiency_ac3_speed": Operations.__v2_tail_register(
                regs_tail,
                const.REG_V2_EFFICIENCY_AC3_SPEED
            ),
        }

        for idx in range(const.NUM_REG_V2_CONNECTED_VOLUME):
            engine_id = idx + 1
            reg = const.REG_V2_START_CONNECTED_VOLUME + idx
            values["{}_connected_volume_ac{}".format(
                reg + const.MODBUS_LOGICAL_ADDRESS_BASE,
                engine_id,
            )] = Operations.__v2_demand_register(
                regs_demand,
                reg,
            )

        for idx in range(const.NUM_REG_V2_ACTIVE_VOLUME):
            engine_id = idx + 1
            reg = const.REG_V2_START_ACTIVE_VOLUME + idx
            values["{}_active_volume_ac{}".format(
                reg + const.MODBUS_LOGICAL_ADDRESS_BASE,
                engine_id,
            )] = Operations.__v2_demand_register(
                regs_demand,
                reg,
            )

        for idx in range(const.NUM_REG_V2_REQUESTED_TEMP_AVG):
            engine_id = idx + 1
            reg = const.REG_V2_START_REQUESTED_TEMP_AVG + idx
            if engine_id == 4:
                reg += 1
                values["{}_requested_temp_avg_ac{}".format(
                    reg + const.MODBUS_LOGICAL_ADDRESS_BASE,
                    engine_id,
                )] = Operations.__v2_tail_register(
                    regs_tail,
                    reg,
                )
                continue
            values["{}_requested_temp_avg_ac{}".format(
                reg + const.MODBUS_LOGICAL_ADDRESS_BASE,
                engine_id,
            )] = Operations.__v2_demand_register(
                regs_demand,
                reg,
            )

        return True, values

    async def async_set_efficiency(self,
                                    opt:const.GlobalMode,
                                    ) -> bool:
        """Write efficiency

        Args:
            opt: Enum value to write.

        Returns:
            Operation success flag.
        """
        if not self.supports_efficiency:
            _LOGGER.warning("Efficiency register is not supported by this Modbus table")
            return False
        ret = await self.__async_write_register(reg = self._registers[const.REG_KEY_EFFICIENCY], val = int(opt))
        if not ret:
            _LOGGER.error('Error writing efficiency')
        return ret

    async def async_communication_config(self) -> (bool, int):
        """read Modbus communication frequency and parity

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_COMM])
        if not ret:
            _LOGGER.error('Error retreive communication config')
            reg = 0
        return ret, reg

    async def async_modbus_address(self) -> (bool, int):
        """read Modbus slave address

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_ADDR_MODBUS])
        if not ret:
            _LOGGER.error('Error retreive Modbus address')
            reg = 0
        return ret, reg

    async def async_clim_id(self) -> (bool, int):
        """read infrared receiver brand, model and machine number

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_CLIM_ID])
        if not ret:
            _LOGGER.error('Error retreive infrared receiver id')
            reg = 0
        return ret, reg

    async def async_engines_throughput(self) -> (bool, list):
        """read engines throughput AC1, AC2, AC3, AC4

        Returns:
            Tuple of success flag and decoded value.
        """
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
        """read engine throughput specified by id

        Args:
            engine_id: One-based AC engine id.

        Returns:
            Tuple of success flag and decoded value.
        """
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
        """read engine state specified by id

        Args:
            engine_id: One-based AC engine id.

        Returns:
            (bool, const.FlowEngine) value.
        """
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
        """write engine state specified by id

        Args:
            engine_id: One-based AC engine id.
            opt: Enum value to write.

        Returns:
            Operation success flag.
        """
        if engine_id < 1 or engine_id > 4:
            raise UnitIdError("Engine id must be between 1 and 4")
        ret = await self.__async_write_register(reg = self._registers[const.REG_KEY_START_FLOW_STATE_ENGINE] + (engine_id - 1), val = int(opt))
        if not ret:
            _LOGGER.error('Error writing engine state for id:{}'.format(engine_id))
        return ret

    async def async_engine_order_temp(self,
                                        engine_id:int = 0,
                                        ) -> (bool, float):
        """read engine order temperature specified by id

        Args:
            engine_id: One-based AC engine id.

        Returns:
            Tuple of success flag and decoded value.
        """
        if engine_id < 1 or engine_id > 4:
            raise UnitIdError("Engine id must be between 1 and 4")
        reg, ret = await self.__async_read_register(self._registers[const.REG_KEY_START_ORDER_TEMP] + (engine_id - 1))
        if not ret:
            _LOGGER.error('Error retreive engine order temp for id:{}'.format(engine_id))
            reg = 0
        return ret, reg / 2

    async def async_engine_orders_temp(self) -> (bool, list):
        """read orders temperature for engines : AC1, AC2, AC3, AC4

        Returns:
            Tuple of success flag and decoded value.
        """
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
        """Set area target temperature

        Args:
            zone_id: One-based Koolnova zone id.
            val: Value to write or set.

        Returns:
            Operation success flag.
        """
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
        """get temperature of specific area id

        Args:
            id_zone: One-based Koolnova zone id.

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_TEMP_REAL)
        if not ret:
            _LOGGER.error('Error retreive area real temp')
            reg = 0
        return ret, reg / 2

    async def async_area_target_temp(self,
                                    id_zone:int = 0,
                                    ) -> (bool, float):
        """get target temperature of specific area id

        Args:
            id_zone: One-based Koolnova zone id.

        Returns:
            Tuple of success flag and decoded value.
        """
        reg, ret = await self.__async_read_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_TEMP_ORDER)
        if not ret:
            _LOGGER.error('Error retreive area target temp')
            reg = 0
        return ret, reg / 2

    async def async_area_clim_and_fan_mode(self,
                                            id_zone:int = 0,
                                            ) -> (bool, const.ZoneFanMode, const.ZoneClimMode):
        """get climate and fan mode of specific area id

        Args:
            id_zone: One-based Koolnova zone id.

        Returns:
            (bool, const.ZoneFanMode, const.ZoneClimMode) value.
        """
        reg, ret = await self.__async_read_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_STATE_AND_FLOW)
        if not ret:
            _LOGGER.error('Error retreive area fan and climate values')
            reg = 0
        return ret, const.ZoneFanMode((reg & 0xF0) >> 4), const.ZoneClimMode(reg & 0x0F)

    async def async_area_state_and_register(self,
                                            id_zone:int = 0,
                                            ) -> (bool, const.ZoneRegister, const.ZoneState):
        """get area state and register

        Args:
            id_zone: One-based Koolnova zone id.

        Returns:
            (bool, const.ZoneRegister, const.ZoneState) value.
        """
        reg, ret = await self.__async_read_register(reg = const.REG_START_ZONE + (4 * (id_zone - 1)) + const.REG_LOCK_ZONE)
        if not ret:
            _LOGGER.error('Error retreive area register value')
            reg = 0
        return ret, const.ZoneRegister((reg >> 1) & 0b1), const.ZoneState(reg & 0b01)

    async def async_set_area_state(self,
                                    id_zone:int = 0,
                                    val:const.ZoneState = const.ZoneState.STATE_OFF,
                                    ) -> bool:
        """set area state

        Args:
            id_zone: One-based Koolnova zone id.
            val: Value to write or set.

        Returns:
            Operation success flag.
        """
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
        """set area clim mode

        Args:
            id_zone: One-based Koolnova zone id.
            val: Value to write or set.

        Returns:
            Operation success flag.
        """
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
        """set area fan mode

        Args:
            id_zone: One-based Koolnova zone id.
            val: Value to write or set.

        Returns:
            Operation success flag.
        """
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
        """Class Constructor

        Args:
            msg: Exception message.

        Returns:
            None.
        """
        self._msg = msg

    def __str__(self):
        """print the message

        Returns:
            String representation.
        """
        return self._msg

class ModbusConnexionError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        """Class Constructor

        Args:
            msg: Exception message.

        Returns:
            None.
        """
        self._msg = msg

    def __str__(self):
        """print the message

        Returns:
            String representation.
        """
        return self._msg

class ReadRegistersError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        """Class Constructor

        Args:
            msg: Exception message.

        Returns:
            None.
        """
        self._msg = msg

    def __str__(self):
        """print the message

        Returns:
            String representation.
        """
        return self._msg

class ZoneIdError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        """Class Constructor

        Args:
            msg: Exception message.

        Returns:
            None.
        """
        self._msg = msg

    def __str__(self):
        """print the message

        Returns:
            String representation.
        """
        return self._msg

class UnitIdError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        """Class Constructor

        Args:
            msg: Exception message.

        Returns:
            None.
        """
        self._msg = msg

    def __str__(self):
        """print the message

        Returns:
            String representation.
        """
        return self._msg
