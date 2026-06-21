#!/usr/bin/env python3

# @Brief Pymodbus Koolnova Modbus RTU simulator.
#        A simulator datastore with json interface.

import argparse
import asyncio
import logging
import json
from pathlib import Path

from pymodbus import pymodbus_apply_logging_config
from pymodbus.datastore import ModbusServerContext, ModbusSimulatorContext
from pymodbus.server import StartAsyncSerialServer

try:
    from pymodbus.pdu.device import ModbusDeviceIdentification
except ImportError:
    from pymodbus.device import ModbusDeviceIdentification

_logger = logging.getLogger(__file__)

ZONE_COUNT = 16
ZONE_REGISTER_COUNT = 4
ZONE_LOCK_REGISTER_OFFSET = 0
ZONE_MODE_REGISTER_OFFSET = 1
ZONE_STATE_ON = 1
ZONE_STATE_OFF = 0
ZONE_REGISTERED_BIT = 0b10
ZONE_MODE_MASK = 0x0F
ZONE_FAN_MASK = 0xF0

PROFILE_CONFIG = {
    "v1": {
        "global_state_addr": 80,
        "global_mode_addr": 81,
    },
    "v2": {
        "global_state_addr": 108,
        "global_mode_addr": 109,
    },
}


class KoolnovaSimulatorContext(ModbusSimulatorContext):
    """Modbus simulator context with basic Koolnova register correlations."""

    def __init__(self, device_setup: dict, profile: str) -> None:
        """Class constructor."""
        super().__init__(device_setup, None)
        self._profile = profile
        self._profile_config = PROFILE_CONFIG[profile]
        self._sync_zones_from_global_registers()

    def setValues(self, *args, **kwargs):  # noqa: N802 - pymodbus API
        """Store values, then apply Koolnova correlations for linked registers."""
        ret = super().setValues(*args, **kwargs)
        address, values, function_code = self._write_details(args, kwargs)
        if address is not None and values:
            self._apply_correlations(address, values, function_code)
        return ret

    @staticmethod
    def _write_details(args: tuple, kwargs: dict) -> tuple[int | None, list[int], int]:
        """Extract write details from pymodbus setValues call variants."""
        function_code = kwargs.get("fx", kwargs.get("function_code", 3))
        address = kwargs.get("address")
        values = kwargs.get("values")

        if len(args) >= 1:
            function_code = args[0]
        if len(args) >= 2:
            address = args[1]
        if len(args) >= 3:
            values = args[2]

        if values is None:
            values = []
        elif isinstance(values, int):
            values = [values]
        else:
            values = list(values)

        return address, values, function_code

    def _apply_correlations(self,
                            address: int,
                            values: list[int],
                            function_code: int,
                            ) -> None:
        """Apply Koolnova behavior after a write."""
        written_addresses = set(range(address, address + len(values)))
        global_state_addr = self._profile_config["global_state_addr"]
        global_mode_addr = self._profile_config["global_mode_addr"]

        if global_state_addr in written_addresses:
            state = values[global_state_addr - address]
            self._set_all_registered_zone_states(state, function_code)

        if global_mode_addr in written_addresses:
            mode = values[global_mode_addr - address]
            self._set_all_registered_zone_modes(mode, function_code)

        zone_mode_address = self._written_zone_mode_address(written_addresses)
        if zone_mode_address is not None:
            mode = self._read_holding_register(zone_mode_address) & ZONE_MODE_MASK
            self._write_holding_register(global_mode_addr, mode, function_code)
            self._set_all_registered_zone_modes(mode, function_code)

        zone_state_address = self._written_zone_state_address(written_addresses)
        if zone_state_address is not None:
            self._sync_global_state_from_zones(function_code)

    def _sync_zones_from_global_registers(self) -> None:
        """Align initial zone registers with the global state and mode."""
        global_state = self._read_holding_register(self._profile_config["global_state_addr"])
        global_mode = self._read_holding_register(self._profile_config["global_mode_addr"])
        self._set_all_registered_zone_states(global_state, 3)
        self._set_all_registered_zone_modes(global_mode, 3)

    def _registered_zone_lock_addresses(self) -> list[int]:
        """Return lock/state register addresses for registered zones."""
        addresses = []
        for zone_index in range(ZONE_COUNT):
            address = (zone_index * ZONE_REGISTER_COUNT) + ZONE_LOCK_REGISTER_OFFSET
            if self._read_holding_register(address) & ZONE_REGISTERED_BIT:
                addresses.append(address)
        return addresses

    def _set_all_registered_zone_states(self,
                                        state: int,
                                        function_code: int,
                                        ) -> None:
        """Set all registered zone on/off bits from the global system state."""
        normalized_state = ZONE_STATE_ON if int(state) else ZONE_STATE_OFF
        for address in self._registered_zone_lock_addresses():
            current = self._read_holding_register(address)
            updated = (current & ~0b1) | normalized_state
            self._write_holding_register(address, updated, function_code)

    def _set_all_registered_zone_modes(self,
                                       mode: int,
                                       function_code: int,
                                       ) -> None:
        """Set all registered zone climate nibbles from the global mode."""
        normalized_mode = int(mode) & ZONE_MODE_MASK
        for zone_index in range(ZONE_COUNT):
            lock_address = (zone_index * ZONE_REGISTER_COUNT) + ZONE_LOCK_REGISTER_OFFSET
            if not self._read_holding_register(lock_address) & ZONE_REGISTERED_BIT:
                continue
            mode_address = (zone_index * ZONE_REGISTER_COUNT) + ZONE_MODE_REGISTER_OFFSET
            current = self._read_holding_register(mode_address)
            updated = (current & ZONE_FAN_MASK) | normalized_mode
            self._write_holding_register(mode_address, updated, function_code)

    def _sync_global_state_from_zones(self, function_code: int) -> None:
        """Set global system state according to registered zone states."""
        any_zone_on = any(
            self._read_holding_register(address) & ZONE_STATE_ON
            for address in self._registered_zone_lock_addresses()
        )
        self._write_holding_register(
            self._profile_config["global_state_addr"],
            ZONE_STATE_ON if any_zone_on else ZONE_STATE_OFF,
            function_code,
        )

    @staticmethod
    def _written_zone_mode_address(written_addresses: set[int]) -> int | None:
        """Return a written zone mode register address, if any."""
        for zone_index in range(ZONE_COUNT):
            address = (zone_index * ZONE_REGISTER_COUNT) + ZONE_MODE_REGISTER_OFFSET
            if address in written_addresses:
                return address
        return None

    @staticmethod
    def _written_zone_state_address(written_addresses: set[int]) -> int | None:
        """Return a written zone state register address, if any."""
        for zone_index in range(ZONE_COUNT):
            address = (zone_index * ZONE_REGISTER_COUNT) + ZONE_LOCK_REGISTER_OFFSET
            if address in written_addresses:
                return address
        return None

    def _read_holding_register(self, address: int) -> int:
        """Read one holding register from the simulator datastore."""
        return int(super().getValues(3, address, 1)[0])

    def _write_holding_register(self,
                                address: int,
                                value: int,
                                function_code: int,
                                ) -> None:
        """Write one holding register without re-entering correlation handling."""
        super().setValues(function_code, address, [int(value) & 0xFFFF])

def get_commandline() -> argparse.Namespace:
    """ Read and validate command line arguments.
    """
    parser = argparse.ArgumentParser(description="Run koolnova simulator.")
    parser.add_argument("--log",
                        choices=["critical", "error", "warning", "info", "debug"],
                        help="set log level, default is info",
                        default="info",
                        type=str)
    parser.add_argument("--config", help="JSON Config path file", type=str, default="")
    parser.add_argument("--profile",
                        choices=["v1", "v2"],
                        help="built-in Koolnova Modbus table profile, default is v1",
                        default="v1",
                        type=str)
    args = parser.parse_args()
    return args


def get_config_path(args: argparse.Namespace) -> Path:
    """Return the simulator config path."""
    if args.config:
        return Path(args.config)

    config_name = "server-v2.json" if args.profile == "v2" else "server.json"
    return Path(__file__).resolve().parent / config_name


def setup_simulator() -> argparse.Namespace:
    """ Run server setup.
    """
    args = get_commandline()

    pymodbus_apply_logging_config(args.log.upper())
    _logger.setLevel(args.log.upper())

    config_path = get_config_path(args)
    _logger.info("Using simulator config: %s", config_path)

    # open and read json file
    with config_path.open('r') as f:
        setup = json.load(f)

    try:
        # Modbus Simulator
        context = KoolnovaSimulatorContext(setup['device_list']['device'], args.profile)
    except RuntimeError as e:
        _logger.error("error with json file: {}".format(e))
        return None

    # Master collection of device contexts.
    try:
        args.context = ModbusServerContext(devices=context, single=True)
    except TypeError:
        args.context = ModbusServerContext(slaves=context, single=True)
    args.identity = ModbusDeviceIdentification(info_name=setup['server_list']['server']['identity'])
    args.port = setup['server_list']['server']['port']
    args.baudrate = setup['server_list']['server']['baudrate']
    args.stopbits = setup['server_list']['server']['stopbits']
    args.bytesize = setup['server_list']['server']['bytesize']
    args.parity = setup['server_list']['server']['parity']
    args.framer = setup['server_list']['server']['framer']
    return args


async def run_server_simulator(args:argparse.Namespace=None):
    """ Run server.
    """
    _logger.info("### start server simulator")
    await StartAsyncSerialServer(context=args.context,  # Data storage
                                 identity=args.identity, # Server identity
                                 port=args.port, # serial port
                                 baudrate=args.baudrate, # the baud rate to use for the serial device
                                 stopbits=args.stopbits, # the number of stop bits to use
                                 bytesize=args.bytesize, # the bytesize of the serial messages
                                 parity=args.parity, # which kind of parity to use
                                 framer=args.framer) # the framer strategy to use


async def main():
    """ Combine setup and run.
    """
    run_args = setup_simulator()
    if not run_args:
        _logger.error("error append ... :(")
        exit(1)
    await run_server_simulator(run_args)


if __name__ == "__main__":
    asyncio.run(main(), debug=True)
