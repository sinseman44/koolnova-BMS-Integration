#!/usr/bin/env python3

# @Brief Pymodbus Koolnova Modbus RTU simulator.
#        A simulator datastore with json interface.

import argparse
import asyncio
import curses
import logging
import json
import os
import pty
import threading
from dataclasses import dataclass
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

TUI_VIEWS = ("core", "zones", "system", "all")

V1_SYSTEM_REGISTERS = [
    (64, "40065 AC1 airflow"),
    (65, "40066 AC2 airflow"),
    (66, "40067 AC3 airflow"),
    (67, "40068 AC4 airflow"),
    (68, "40069 AC1 target temperature"),
    (69, "40070 AC2 target temperature"),
    (70, "40071 AC3 target temperature"),
    (71, "40072 AC4 target temperature"),
    (72, "40073 AC1 airflow programming"),
    (73, "40074 AC2 airflow programming"),
    (74, "40075 AC3 airflow programming"),
    (75, "40076 AC4 airflow programming"),
    (76, "40077 Modbus comm settings"),
    (77, "40078 Modbus address"),
    (78, "40079 Efficiency"),
    (79, "40080 Receiver"),
    (80, "40081 Global system on/off"),
    (81, "40082 Global HVAC mode"),
]

V2_SYSTEM_REGISTERS = [
    (72, "40073 Model/version"),
    (73, "40074 System parameters"),
    (74, "40075 Active modes"),
    (75, "40076 Temperature limits"),
    (76, "40077 Auto changeover/humidity"),
    (77, "40078 System time"),
    (78, "40079 External inputs"),
    (79, "40080 Opening angle Z1-Z8"),
    (80, "40081 Opening angle Z9-Z16"),
    (81, "40082 Floor water temperature"),
    (82, "40083 Outdoor temperature"),
    (83, "40084 Auxiliary NTC temperature"),
    (84, "40085 Electrovalve mask"),
    (85, "40086 Pump delay / valve offset"),
    (86, "40087 Immersion heater"),
    (87, "40088 Thermostat block"),
    (88, "40089 Automatic mode thresholds"),
    (89, "40090 Mixing valve ambient limits"),
    (90, "40091 Mixing valve water limits"),
    (91, "40092 Mixing valve mode info"),
    (104, "40105 Modbus comm settings"),
    (105, "40106 Modbus address"),
    (106, "40107 Reserved / diagnostic"),
    (107, "40108 Receiver"),
    (108, "40109 Global system on/off"),
    (109, "40110 Global HVAC mode"),
    (110, "40111 Radiant floor demand count"),
    (111, "40112 AC3 air demand count"),
    (112, "40113 AC1 connected volume"),
    (113, "40114 AC2 connected volume"),
    (114, "40115 AC3 connected volume"),
    (115, "40116 AC4 connected volume"),
    (116, "40117 AC1 active volume"),
    (117, "40118 AC2 active volume"),
    (118, "40119 AC3 active volume"),
    (119, "40120 AC4 active volume"),
    (120, "40121 AC1 requested temperature average"),
    (121, "40122 AC2 requested temperature average"),
    (122, "40123 AC3 requested temperature average"),
    (124, "40125 AC4 requested temperature average"),
    (125, "40126 EFI / AC3 speed"),
]

GLOBAL_MODE_NAMES = {
    0: "ventilation",
    1: "cooling",
    2: "heating",
    3: "dehumidification",
    4: "radiant floor heating",
    5: "radiant floor cooling + cooling",
    6: "radiant floor heating + heating",
}

FAN_MODE_NAMES = {
    0: "off",
    1: "low",
    2: "medium",
    3: "high",
    4: "auto",
}

FLOW_PROGRAM_NAMES = {
    1: "manual minimum",
    2: "manual medium",
    3: "manual high",
    4: "automatic",
}

EFFICIENCY_NAMES = {
    1: "lower",
    2: "low",
    3: "medium",
    4: "high",
    5: "higher",
}


@dataclass
class TuiField:
    """One user-facing simulator field."""

    group: str
    label: str
    address: int
    reader: object
    writer: object | None = None
    bounds: str = ""


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
        set_values = getattr(super(), "setValues", None)
        if set_values is None:
            ret = self._set_values(*args, **kwargs)
        else:
            ret = set_values(*args, **kwargs)
        address, values, function_code = self._write_details(args, kwargs)
        if address is not None and values:
            self._apply_correlations(address, values, function_code)
        return ret

    async def async_OLD_setValues(self, *args, **kwargs):  # noqa: N802 - pymodbus API
        """Store values with pymodbus 3.13 simulator API, then apply correlations."""
        ret = await super().async_OLD_setValues(*args, **kwargs)
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
        get_values = getattr(super(), "getValues", None)
        if get_values is not None:
            return int(get_values(3, address, 1)[0])
        real_address = self.fc_offset[3] + address
        return int(self.registers[real_address].value)

    def read_holding_register(self, address: int) -> int:
        """Read one holding register for external simulator tooling."""
        return self._read_holding_register(address)

    def _write_holding_register(self,
                                address: int,
                                value: int,
                                function_code: int,
                                ) -> None:
        """Write one holding register without re-entering correlation handling."""
        set_values = getattr(super(), "setValues", None)
        if set_values is not None:
            set_values(function_code, address, [int(value) & 0xFFFF])
            return

        real_address = self.fc_offset[function_code] + address
        self.registers[real_address].value = int(value) & 0xFFFF
        self.registers[real_address].count_write += 1

    def _set_values(self, *args, **kwargs) -> None:
        """Set values for pymodbus simulator versions without sync setValues."""
        address, values, function_code = self._write_details(args, kwargs)
        if address is None:
            return None
        for index, value in enumerate(values):
            self._write_holding_register(address + index, value, function_code)
        return None

    def write_holding_register(self,
                               address: int,
                               value: int,
                               function_code: int = 6,
                               ) -> None:
        """Write one holding register and apply simulator correlations."""
        self.setValues(function_code, address, [int(value) & 0xFFFF])

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
    parser.add_argument("--tui",
                        action="store_true",
                        help="start a small ncurses interface to inspect and edit simulator registers")
    parser.add_argument("--faketty",
                        action="store_true",
                        help="create a local pseudo-terminal and use it instead of the configured serial port")
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
    args.device_context = context
    args.identity = ModbusDeviceIdentification(info_name=setup['server_list']['server']['identity'])
    args.port = setup['server_list']['server']['port']
    args.baudrate = setup['server_list']['server']['baudrate']
    args.stopbits = setup['server_list']['server']['stopbits']
    args.bytesize = setup['server_list']['server']['bytesize']
    args.parity = setup['server_list']['server']['parity']
    args.framer = setup['server_list']['server']['framer']
    if args.faketty:
        configure_fake_tty(args)
    return args


def configure_fake_tty(args: argparse.Namespace) -> None:
    """Create a pseudo-terminal pair and use the slave as the simulator serial port."""
    master_fd, slave_fd = pty.openpty()
    slave_path = os.ttyname(slave_fd)
    args.fake_tty_master_fd = master_fd
    args.fake_tty_slave_fd = slave_fd
    args.port = slave_path
    _logger.info("Using fake serial port: %s", slave_path)


class RegisterTui:
    """Small curses interface for inspecting and editing holding registers."""

    def __init__(self,
                 context: KoolnovaSimulatorContext,
                 profile: str,
                 ) -> None:
        """Class constructor."""
        self._context = context
        self._profile = profile
        self._view_index = 0
        self._registers = self._build_registers()
        self._selected = 0
        self._message = ""
        self._running = True

    def run(self) -> None:
        """Run the curses application."""
        curses.wrapper(self._main)

    def _main(self, screen) -> None:
        """Main curses loop."""
        self._set_cursor(0)
        screen.nodelay(False)
        while self._running:
            self._draw(screen)
            key = screen.getch()
            self._handle_key(screen, key)

    def _draw(self, screen) -> None:
        """Render the current register list."""
        screen.erase()
        height, width = screen.getmaxyx()
        view = TUI_VIEWS[self._view_index]
        title = "Koolnova simulator register editor ({})  view: {}  rows: {}".format(
            self._profile,
            view,
            len(self._registers),
        )
        screen.addnstr(0, 0, title, width - 1, curses.A_BOLD)
        screen.addnstr(1, 0, "Move: arrows/PgUp/PgDn  Tab: view  e: raw  f: fields  a/g: goto  +/-: step  r: refresh  q: quit", width - 1)
        screen.addnstr(2, 0, "Values are raw holding registers. Logical address = 40001 + offset.", width - 1)

        detail_height = 5
        max_rows = max(0, height - 7 - detail_height)
        start = max(0, self._selected - max_rows + 1)
        visible = self._registers[start:start + max_rows]

        header = "  {:>5} {:>6} {:>6}  {}".format("Reg", "Hex", "Dec", "Name")
        screen.addnstr(3, 0, header, width - 1, curses.A_UNDERLINE)

        for index, (address, label) in enumerate(visible, start=start):
            row = 4 + index - start
            value = self._context.read_holding_register(address)
            marker = ">" if index == self._selected else " "
            attr = curses.A_REVERSE if index == self._selected else curses.A_NORMAL
            line = "{} {:>5}  0x{:04X}  {:>5}  {}".format(
                marker,
                40001 + address,
                value,
                value,
                label,
            )
            screen.addnstr(row, 0, line, width - 1, attr)

        self._draw_detail(screen, height, width)
        if self._message:
            screen.addnstr(height - 1, 0, self._message, width - 1)
        screen.refresh()

    def _handle_key(self, screen, key: int) -> None:
        """Handle one key press."""
        if key in (ord("q"), ord("Q")):
            self._running = False
        elif key in (curses.KEY_UP, ord("k")):
            self._selected = max(0, self._selected - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            self._selected = min(len(self._registers) - 1, self._selected + 1)
        elif key == curses.KEY_PPAGE:
            self._selected = max(0, self._selected - 10)
        elif key == curses.KEY_NPAGE:
            self._selected = min(len(self._registers) - 1, self._selected + 10)
        elif key in (9, ord("\t")):
            self._cycle_view()
        elif key in (ord("e"), ord("E"), curses.KEY_ENTER, 10, 13):
            self._edit_selected(screen)
        elif key in (ord("f"), ord("F")):
            self._edit_decoded_selected(screen)
        elif key in (ord("a"), ord("A"), ord("g"), ord("G")):
            self._edit_arbitrary_register(screen)
        elif key in (ord("+"), ord("=")):
            self._increment_selected(1)
        elif key in (ord("-"), ord("_")):
            self._increment_selected(-1)
        elif key in (ord("r"), ord("R")):
            self._message = "Refreshed."

    def _build_registers(self) -> list[tuple[int, str]]:
        """Build the register list for the current view."""
        view = TUI_VIEWS[self._view_index]
        if view == "core":
            return self._core_registers()
        if view == "zones":
            return self._zone_registers()
        if view == "system":
            return self._system_registers()
        return self._all_registers()

    def _core_registers(self) -> list[tuple[int, str]]:
        """Return the most common registers for quick manual testing."""
        if self._profile == "v2":
            return [
                (72, "40073 Model/version"),
                (74, "40075 Active modes"),
                (75, "40076 Temperature limits"),
                (76, "40077 Auto changeover/humidity"),
                (84, "40085 Electrovalve mask"),
                (88, "40089 Automatic mode thresholds"),
                (108, "40109 Global system on/off"),
                (109, "40110 Global HVAC mode"),
            ]
        return [
            (72, "40073 AC1 airflow programming"),
            (76, "40077 Modbus comm settings"),
            (78, "40079 Efficiency"),
            (80, "40081 Global system on/off"),
            (81, "40082 Global HVAC mode"),
        ]

    @staticmethod
    def _zone_registers() -> list[tuple[int, str]]:
        """Return zone registers 40001 to 40064 with readable labels."""
        registers = []
        field_names = ("lock/state", "mode/fan", "temperature", "target temperature")
        for zone_index in range(ZONE_COUNT):
            zone_id = zone_index + 1
            for field_index, field_name in enumerate(field_names):
                address = (zone_index * ZONE_REGISTER_COUNT) + field_index
                registers.append((address, "Z{} {}".format(zone_id, field_name)))
        return registers

    def _system_registers(self) -> list[tuple[int, str]]:
        """Return the documented system block registers for this profile."""
        return V2_SYSTEM_REGISTERS if self._profile == "v2" else V1_SYSTEM_REGISTERS

    def _all_registers(self) -> list[tuple[int, str]]:
        """Return every register known by the simulator datastore."""
        return [
            (address, self._label_for_address(address))
            for address in range(self._context.register_count)
        ]

    def _label_for_address(self, address: int) -> str:
        """Return a readable label for any holding register offset."""
        for known_address, label in self._system_registers():
            if known_address == address:
                return label
        zone_limit = ZONE_COUNT * ZONE_REGISTER_COUNT
        if 0 <= address < zone_limit:
            return dict(self._zone_registers()).get(address, "Zone register")
        return "Holding register {}".format(40001 + address)

    def _cycle_view(self) -> None:
        """Move to the next register view."""
        self._view_index = (self._view_index + 1) % len(TUI_VIEWS)
        self._registers = self._build_registers()
        self._selected = min(self._selected, len(self._registers) - 1)
        self._message = "View changed to {}.".format(TUI_VIEWS[self._view_index])

    def _draw_detail(self, screen, height: int, width: int) -> None:
        """Draw a small decoded detail panel for the selected register."""
        if not self._registers:
            return
        address, label = self._registers[self._selected]
        value = self._context.read_holding_register(address)
        start_row = max(4, height - 6)
        screen.hline(start_row, 0, "-", max(0, width - 1))
        screen.addnstr(start_row + 1, 0, "{} {} offset {} raw 0x{:04X}/{}".format(
            40001 + address,
            label,
            address,
            value,
            value,
        ), width - 1, curses.A_BOLD)
        for line_index, line in enumerate(self._decode_register(address, value), start=2):
            if start_row + line_index >= height - 1:
                break
            screen.addnstr(start_row + line_index, 0, line, width - 1)

    def _decode_register(self, address: int, value: int) -> list[str]:
        """Return decoded helper text for well-known registers."""
        if 0 <= address < ZONE_COUNT * ZONE_REGISTER_COUNT:
            return self._decode_zone_register(address, value)
        if self._profile == "v2":
            return self._decode_v2_register(address, value)
        return self._decode_v1_register(address, value)

    @staticmethod
    def _decode_zone_register(address: int, value: int) -> list[str]:
        """Decode common zone registers."""
        zone_id = (address // ZONE_REGISTER_COUNT) + 1
        field = address % ZONE_REGISTER_COUNT
        if field == 0:
            return [
                "Zone Z{} registered: {}  state: {}".format(
                    zone_id,
                    "yes" if value & ZONE_REGISTERED_BIT else "no",
                    "on" if value & ZONE_STATE_ON else "off",
                )
            ]
        if field == 1:
            mode = value & ZONE_MODE_MASK
            fan = (value & ZONE_FAN_MASK) >> 4
            return ["Zone Z{} mode: {} ({})  fan code: {}".format(
                zone_id,
                GLOBAL_MODE_NAMES.get(mode, "unknown"),
                mode,
                fan,
            )]
        if field in (2, 3):
            return ["Zone Z{} temperature: {:.1f} C".format(zone_id, value / 2)]
        return []

    @staticmethod
    def _decode_v1_register(address: int, value: int) -> list[str]:
        """Decode selected v1 registers."""
        if address in (80, 81):
            if address == 80:
                return ["Global system state: {}".format("on" if value else "off")]
            return ["Global HVAC mode: {} ({})".format(GLOBAL_MODE_NAMES.get(value, "unknown"), value)]
        if 68 <= address <= 71:
            return ["Engine target temperature: {:.1f} C".format(value / 2)]
        return []

    @staticmethod
    def _decode_v2_register(address: int, value: int) -> list[str]:
        """Decode selected v2 registers."""
        msb = (value >> 8) & 0xFF
        lsb = value & 0xFF
        if address == 74:
            modes = ("ventilation", "cooling", "heating", "dehumidification",
                     "radiant floor", "floor cooling", "floor heating")
            enabled = [name for bit, name in enumerate(modes) if lsb & (1 << bit)]
            return ["Enabled modes: {}".format(", ".join(enabled) if enabled else "none")]
        if address == 75:
            return ["Max heating limit: {:.1f} C  Min cooling limit: {:.1f} C".format(msb / 2, lsb / 2)]
        if address == 76:
            above = (msb >> 4) & 0x0F
            below = msb & 0x0F
            return [
                "Above heating threshold mode: {} ({})".format(GLOBAL_MODE_NAMES.get(above, "unknown"), above),
                "Below cooling threshold mode: {} ({})  Humidity relay threshold: {}".format(
                    GLOBAL_MODE_NAMES.get(below, "unknown"),
                    below,
                    lsb,
                ),
            ]
        if address in (79, 80):
            return ["Opening angle code: {}  zone index: {} (Z{})".format(msb, lsb, lsb + 1)]
        if address == 84:
            enabled = ["Z{}".format(index + 1) for index in range(16) if value & (1 << index)]
            return ["Electrovalves enabled: {}".format(", ".join(enabled) if enabled else "none")]
        if address == 88:
            return ["Cooling water threshold: {} C  Heating water threshold: {} C".format(msb, lsb)]
        if address == 108:
            return ["Global system state: {}".format("on" if value else "off")]
        if address == 109:
            return ["Global HVAC mode: {} ({})".format(GLOBAL_MODE_NAMES.get(value, "unknown"), value)]
        if address == 125:
            return ["EFI: {}  AC3 speed: {}".format(msb, lsb)]
        return []

    def _increment_selected(self, delta: int) -> None:
        """Increment or decrement the selected register."""
        address, _label = self._registers[self._selected]
        value = self._context.read_holding_register(address)
        new_value = value + delta
        if new_value < 0 or new_value > 0xFFFF:
            self._message = "Value must stay between 0 and 65535."
            return
        self._write_value(address, new_value)

    def _edit_selected(self, screen) -> None:
        """Prompt for a new value and write it to the selected register."""
        address, label = self._registers[self._selected]
        current = self._context.read_holding_register(address)
        prompt = "New value for {} ({}, current 0x{:04X}/{}): ".format(
            40001 + address,
            label,
            current,
            current,
        )
        curses.echo()
        self._set_cursor(1)
        height, width = screen.getmaxyx()
        screen.move(height - 1, 0)
        screen.clrtoeol()
        screen.addnstr(height - 1, 0, prompt, width - 1)
        try:
            raw_value = screen.getstr(height - 1, min(len(prompt), width - 1), 16)
            value_text = raw_value.decode("ascii").strip()
            if not value_text:
                self._message = "Edit cancelled."
                return
            value = int(value_text, 0)
            if value < 0 or value > 0xFFFF:
                self._message = "Value must be between 0 and 65535."
                return
            self._context.write_holding_register(address, value, 6)
            self._message = "Wrote {} = 0x{:04X} / {}.".format(40001 + address, value, value)
        except ValueError:
            self._message = "Invalid value. Use decimal or 0x-prefixed hexadecimal."
        finally:
            curses.noecho()
            self._set_cursor(0)

    def _edit_decoded_selected(self, screen) -> None:
        """Edit known decoded fields for the selected register."""
        address, _label = self._registers[self._selected]
        value = self._context.read_holding_register(address)
        if 0 <= address < ZONE_COUNT * ZONE_REGISTER_COUNT:
            self._edit_zone_field(screen, address, value)
            return
        if self._profile == "v2" and address in (75, 76, 88, 108, 109):
            self._edit_v2_field(screen, address, value)
            return
        if self._profile == "v1" and address in (80, 81):
            self._edit_global_field(screen, address, value)
            return
        self._message = "No decoded editor for this register. Use raw edit."

    def _edit_zone_field(self, screen, address: int, value: int) -> None:
        """Edit a decoded zone register field."""
        field = address % ZONE_REGISTER_COUNT
        if field == 0:
            state = self._prompt_optional_int(screen, "Zone state 0=off 1=on: ")
            if state is None:
                return
            updated = (value & ~ZONE_STATE_ON) | (ZONE_STATE_ON if state else ZONE_STATE_OFF)
        elif field == 1:
            mode = self._prompt_optional_int(screen, "Zone mode code 0..6: ")
            if mode is None:
                return
            fan = self._prompt_optional_int(screen, "Fan code 0..15 blank=keep: ", allow_blank=True)
            current_fan = (value & ZONE_FAN_MASK) >> 4
            fan = current_fan if fan is None else fan
            updated = ((fan & 0x0F) << 4) | (mode & ZONE_MODE_MASK)
        elif field in (2, 3):
            temperature = self._prompt_optional_float(screen, "Temperature C, 0.5 step: ")
            if temperature is None:
                return
            raw = int(round(temperature * 2))
            if abs((temperature * 2) - raw) > 0.000001 or raw < 0 or raw > 0xFFFF:
                self._message = "Temperature must fit a non-negative 0.5 C step."
                return
            updated = raw
        else:
            self._message = "No decoded editor for this zone register."
            return
        self._write_value(address, updated)

    def _edit_v2_field(self, screen, address: int, value: int) -> None:
        """Edit selected decoded v2 fields."""
        msb = (value >> 8) & 0xFF
        lsb = value & 0xFF
        if address == 75:
            max_heat = self._prompt_optional_float(screen, "Max heating limit C blank=keep: ", allow_blank=True)
            min_cool = self._prompt_optional_float(screen, "Min cooling limit C blank=keep: ", allow_blank=True)
            max_raw = msb if max_heat is None else int(round(max_heat * 2))
            min_raw = lsb if min_cool is None else int(round(min_cool * 2))
            if max_raw < 0 or max_raw > 0xFF or min_raw < 0 or min_raw > 0xFF:
                self._message = "40076 fields must encode to bytes 0..255."
                return
            updated = (max_raw << 8) | min_raw
        elif address == 76:
            above = self._prompt_optional_int(screen, "Mode above heating threshold blank=keep: ", allow_blank=True)
            below = self._prompt_optional_int(screen, "Mode below cooling threshold blank=keep: ", allow_blank=True)
            humidity = self._prompt_optional_int(screen, "Humidity relay threshold blank=keep: ", allow_blank=True)
            above = ((msb >> 4) & 0x0F) if above is None else above
            below = (msb & 0x0F) if below is None else below
            humidity = lsb if humidity is None else humidity
            if above < 0 or above > 0x0F or below < 0 or below > 0x0F or humidity < 0 or humidity > 0xFF:
                self._message = "40077 modes must be 0..15 and humidity 0..255."
                return
            updated = (((above & 0x0F) << 4) | (below & 0x0F)) << 8 | humidity
        elif address == 88:
            cooling = self._prompt_optional_int(screen, "Cooling water threshold C blank=keep: ", allow_blank=True)
            heating = self._prompt_optional_int(screen, "Heating water threshold C blank=keep: ", allow_blank=True)
            cooling = msb if cooling is None else cooling
            heating = lsb if heating is None else heating
            if cooling < 0 or cooling > 0xFF or heating < 0 or heating > 0xFF:
                self._message = "40089 thresholds must be 0..255."
                return
            updated = (cooling << 8) | heating
        elif address in (108, 109):
            self._edit_global_field(screen, address, value)
            return
        else:
            self._message = "No decoded editor for this register."
            return
        self._write_value(address, updated)

    def _edit_global_field(self, screen, address: int, value: int) -> None:
        """Edit global system state or mode."""
        if address in (80, 108):
            new_value = self._prompt_optional_int(screen, "Global state 0=off 1=on: ")
        else:
            new_value = self._prompt_optional_int(screen, "Global mode code 0..6: ")
        if new_value is None:
            return
        self._write_value(address, new_value)

    def _edit_arbitrary_register(self, screen) -> None:
        """Prompt for any holding register and value."""
        register_text = self._prompt(screen, "Register logical address or offset: ", 12)
        if not register_text:
            self._message = "Edit cancelled."
            return

        try:
            address = int(register_text, 0)
        except ValueError:
            self._message = "Invalid register address."
            return

        if address >= 40001:
            address -= 40001
        if address < 0:
            self._message = "Register address must be positive."
            return

        current = self._context.read_holding_register(address)
        value_text = self._prompt(
            screen,
            "New value for {} current 0x{:04X}/{}: ".format(40001 + address, current, current),
            16,
        )
        if not value_text:
            self._message = "Edit cancelled."
            return
        try:
            value = int(value_text, 0)
            if value < 0 or value > 0xFFFF:
                self._message = "Value must be between 0 and 65535."
                return
            self._write_value(address, value)
        except ValueError:
            self._message = "Invalid value. Use decimal or 0x-prefixed hexadecimal."

    def _write_value(self, address: int, value: int) -> None:
        """Write one raw register and update the status message."""
        if value < 0 or value > 0xFFFF:
            self._message = "Value must be between 0 and 65535."
            return
        self._context.write_holding_register(address, value, 6)
        self._message = "Wrote {} = 0x{:04X} / {}.".format(40001 + address, value, value)

    def _prompt_optional_int(self,
                             screen,
                             prompt: str,
                             allow_blank: bool = False,
                             ) -> int | None:
        """Prompt for an integer and return None on cancel or blank when allowed."""
        value_text = self._prompt(screen, prompt, 16)
        if not value_text:
            if allow_blank:
                return None
            self._message = "Edit cancelled."
            return None
        try:
            return int(value_text, 0)
        except ValueError:
            self._message = "Invalid integer."
            return None

    def _prompt_optional_float(self,
                               screen,
                               prompt: str,
                               allow_blank: bool = False,
                               ) -> float | None:
        """Prompt for a float and return None on cancel or blank when allowed."""
        value_text = self._prompt(screen, prompt, 16)
        if not value_text:
            if allow_blank:
                return None
            self._message = "Edit cancelled."
            return None
        try:
            return float(value_text)
        except ValueError:
            self._message = "Invalid number."
            return None

    @staticmethod
    def _prompt(screen,
                prompt: str,
                max_length: int,
                ) -> str:
        """Read one prompt value from the status line."""
        curses.echo()
        RegisterTui._set_cursor(1)
        height, width = screen.getmaxyx()
        screen.move(height - 1, 0)
        screen.clrtoeol()
        screen.addnstr(height - 1, 0, prompt, width - 1)
        try:
            raw_value = screen.getstr(height - 1, min(len(prompt), width - 1), max_length)
            return raw_value.decode("ascii").strip()
        finally:
            curses.noecho()
            RegisterTui._set_cursor(0)

    @staticmethod
    def _set_cursor(visibility: int) -> None:
        """Best-effort cursor visibility update for terminals that support it."""
        try:
            curses.curs_set(visibility)
        except curses.error:
            pass


class FriendlyRegisterTui:
    """User-friendly grouped editor for Koolnova simulator fields."""

    def __init__(self,
                 context: KoolnovaSimulatorContext,
                 profile: str,
                 ) -> None:
        """Class constructor."""
        self._context = context
        self._profile = profile
        self._fields = self._build_fields()
        self._groups = list(self._fields)
        self._group_index = 0
        self._selected = 0
        self._message = ""
        self._running = True

    def run(self) -> None:
        """Run the curses application."""
        curses.wrapper(self._main)

    def _main(self, screen) -> None:
        """Main curses loop."""
        self._set_cursor(0)
        screen.nodelay(False)
        while self._running:
            self._draw(screen)
            self._handle_key(screen, screen.getch())

    def _draw(self, screen) -> None:
        """Draw the grouped field editor."""
        screen.erase()
        height, width = screen.getmaxyx()
        group = self._groups[self._group_index]
        fields = self._current_fields()
        title = "Koolnova simulator ({})  group: {}  fields: {}".format(
            self._profile,
            group,
            len(fields),
        )
        screen.addnstr(0, 0, title, width - 1, curses.A_BOLD)
        screen.addnstr(1, 0, "Tab: group  arrows/PgUp/PgDn: move  Enter/e: edit  r: refresh  b: raw register view  q: quit", width - 1)
        screen.addnstr(2, 0, "Edits are bounded by the known Koolnova Modbus table ranges.", width - 1)

        header = "  {:<34} {:<24} {:<24} {:>6}".format("Field", "Value", "Allowed", "Reg")
        screen.addnstr(4, 0, header, width - 1, curses.A_UNDERLINE)

        max_rows = max(0, height - 8)
        start = max(0, self._selected - max_rows + 1)
        visible = fields[start:start + max_rows]
        for index, field in enumerate(visible, start=start):
            row = 5 + index - start
            attr = curses.A_REVERSE if index == self._selected else curses.A_NORMAL
            marker = ">" if index == self._selected else " "
            line = "{} {:<34} {:<24} {:<24} {:>6}".format(
                marker,
                field.label[:34],
                str(field.reader())[:24],
                field.bounds[:24],
                40001 + field.address,
            )
            screen.addnstr(row, 0, line, width - 1, attr)

        if fields:
            selected = fields[self._selected]
            raw = self._context.read_holding_register(selected.address)
            screen.hline(height - 3, 0, "-", max(0, width - 1))
            screen.addnstr(height - 2, 0, "{} raw register {} offset {} = 0x{:04X}/{}".format(
                selected.label,
                40001 + selected.address,
                selected.address,
                raw,
                raw,
            ), width - 1)
        if self._message:
            screen.addnstr(height - 1, 0, self._message, width - 1)
        screen.refresh()

    def _handle_key(self, screen, key: int) -> None:
        """Handle one key press."""
        fields = self._current_fields()
        if key in (ord("q"), ord("Q")):
            self._running = False
        elif key in (9, ord("\t")):
            self._group_index = (self._group_index + 1) % len(self._groups)
            self._selected = 0
            self._message = "Group changed to {}.".format(self._groups[self._group_index])
        elif key in (curses.KEY_UP, ord("k")):
            self._selected = max(0, self._selected - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            self._selected = min(len(fields) - 1, self._selected + 1)
        elif key == curses.KEY_PPAGE:
            self._selected = max(0, self._selected - 10)
        elif key == curses.KEY_NPAGE:
            self._selected = min(len(fields) - 1, self._selected + 10)
        elif key in (ord("e"), ord("E"), curses.KEY_ENTER, 10, 13):
            self._edit_selected(screen)
        elif key in (ord("r"), ord("R")):
            self._message = "Refreshed."
        elif key in (ord("b"), ord("B")):
            self._run_raw_view(screen)

    def _run_raw_view(self, screen) -> None:
        """Temporarily enter the raw register view."""
        self._message = "Raw view is available by restarting with the previous register editor code path."
        screen.addnstr(3, 0, "Raw register view was superseded by grouped fields. Use group 'raw common' or add a field.", 120)

    def _current_fields(self) -> list[TuiField]:
        """Return fields for the current group."""
        return self._fields[self._groups[self._group_index]]

    def _edit_selected(self, screen) -> None:
        """Edit the selected bounded field."""
        fields = self._current_fields()
        if not fields:
            return
        field = fields[self._selected]
        if field.writer is None:
            self._message = "Read-only field."
            return
        value_text = self._prompt(screen, "New value for {} ({}): ".format(field.label, field.bounds), 32)
        if not value_text:
            self._message = "Edit cancelled."
            return
        try:
            field.writer(value_text)
            self._message = "Updated {}.".format(field.label)
        except ValueError as err:
            self._message = str(err)

    def _build_fields(self) -> dict[str, list[TuiField]]:
        """Build grouped field definitions for the active profile."""
        fields = {
            "zones": self._zone_fields(),
            "global": self._global_fields(),
        }
        if self._profile == "v2":
            fields.update({
                "v2 modes": self._v2_mode_fields(),
                "v2 auto": self._v2_auto_fields(),
                "v2 airflow": self._v2_airflow_fields(),
                "v2 water": self._v2_water_fields(),
                "v2 advanced": self._v2_advanced_fields(),
            })
        else:
            fields.update({
                "engines": self._v1_engine_fields(),
                "communication": self._v1_communication_fields(),
            })
        return fields

    def _zone_fields(self) -> list[TuiField]:
        """Build fields for zones 1 to 16."""
        fields = []
        for zone_index in range(ZONE_COUNT):
            zone_id = zone_index + 1
            lock_addr = zone_index * ZONE_REGISTER_COUNT
            mode_addr = lock_addr + 1
            real_temp_addr = lock_addr + 2
            target_temp_addr = lock_addr + 3
            fields.append(self._bit_field(
                "zones", "Z{} enabled".format(zone_id), lock_addr, 0,
                {0: "off", 1: "on"},
            ))
            fields.append(TuiField(
                "zones",
                "Z{} registered".format(zone_id),
                lock_addr,
                lambda addr=lock_addr: "yes" if self._context.read_holding_register(addr) & ZONE_REGISTERED_BIT else "no",
                None,
                "read-only",
            ))
            fields.append(self._nibble_field(
                "zones", "Z{} HVAC mode".format(zone_id), mode_addr, 0, ZONE_MODE_MASK,
                GLOBAL_MODE_NAMES,
            ))
            fields.append(self._nibble_field(
                "zones", "Z{} fan mode".format(zone_id), mode_addr, 4, 0x0F,
                FAN_MODE_NAMES,
            ))
            fields.append(self._half_degree_field(
                "zones", "Z{} current temperature".format(zone_id), real_temp_addr,
                0, 50, writable=False,
            ))
            fields.append(self._half_degree_field(
                "zones", "Z{} target temperature".format(zone_id), target_temp_addr,
                15, 35, writable=True,
            ))
        return fields

    def _global_fields(self) -> list[TuiField]:
        """Build global fields."""
        if self._profile == "v2":
            state_addr = 108
            mode_addr = 109
            mode_choices = GLOBAL_MODE_NAMES
        else:
            state_addr = 80
            mode_addr = 81
            mode_choices = {
                1: "cooling",
                2: "heating",
                4: "radiant floor heating",
                5: "radiant floor cooling + cooling",
                6: "radiant floor heating + heating",
            }
        return [
            self._choice_field("global", "Global HVAC state", state_addr, {0: "off", 1: "on"}),
            self._choice_field("global", "Global HVAC mode", mode_addr, mode_choices),
        ]

    def _v1_engine_fields(self) -> list[TuiField]:
        """Build v1 engine fields."""
        fields = []
        for index in range(4):
            engine_id = index + 1
            fields.append(self._int_field("engines", "AC{} airflow".format(engine_id), 64 + index, 0, 15))
            fields.append(self._half_degree_field("engines", "AC{} target temperature".format(engine_id), 68 + index, 15, 35, True))
            fields.append(self._choice_field("engines", "AC{} airflow program".format(engine_id), 72 + index, FLOW_PROGRAM_NAMES))
        return fields

    def _v1_communication_fields(self) -> list[TuiField]:
        """Build v1 communication/config fields."""
        return [
            self._int_field("communication", "Modbus address", 77, 1, 247),
            self._choice_field("communication", "Efficiency", 78, EFFICIENCY_NAMES),
        ]

    def _v2_mode_fields(self) -> list[TuiField]:
        """Build v2 mode availability fields."""
        mode_bits = (
            ("Ventilation available", 0),
            ("Cooling available", 1),
            ("Heating available", 2),
            ("Dehumidification available", 3),
            ("Radiant floor available", 4),
            ("Radiant floor cooling available", 5),
            ("Radiant floor heating available", 6),
        )
        fields = [
            self._choice_field("v2 modes", "Global HVAC mode", 109, GLOBAL_MODE_NAMES),
        ]
        fields.extend(
            self._bit_field("v2 modes", label, 74, bit, {0: "hidden", 1: "available"})
            for label, bit in mode_bits
        )
        return fields

    def _v2_auto_fields(self) -> list[TuiField]:
        """Build v2 automatic changeover fields."""
        return [
            self._byte_field("v2 auto", "Cooling water threshold", 88, "msb", 0, 255, "C"),
            self._byte_field("v2 auto", "Heating water threshold", 88, "lsb", 0, 255, "C"),
            self._nibble_field("v2 auto", "Mode above heating threshold", 76, 12, 0x0F, {
                2: "heating",
                4: "radiant floor heating",
                6: "radiant floor heating + heating",
            }),
            self._nibble_field("v2 auto", "Mode below cooling threshold", 76, 8, 0x0F, {
                1: "cooling",
                5: "radiant floor cooling + cooling",
            }),
            self._byte_field("v2 auto", "Humidity relay threshold", 76, "lsb", 0, 255, "raw"),
        ]

    def _v2_airflow_fields(self) -> list[TuiField]:
        """Build v2 airflow/engine fields."""
        fields = []
        for index in range(4):
            engine_id = index + 1
            fields.append(self._int_field("v2 airflow", "AC{} airflow".format(engine_id), 92 + index, 0, 15))
            fields.append(self._half_degree_field("v2 airflow", "AC{} target temperature".format(engine_id), 96 + index, 15, 35, True))
            fields.append(self._choice_field("v2 airflow", "AC{} airflow program".format(engine_id), 100 + index, FLOW_PROGRAM_NAMES))
        return fields

    def _v2_water_fields(self) -> list[TuiField]:
        """Build v2 water temperature/config fields."""
        return [
            self._half_degree_byte_field("v2 water", "Maximum heating limit", 75, "msb", 0, 127.5),
            self._half_degree_byte_field("v2 water", "Minimum cooling limit", 75, "lsb", 0, 127.5),
            self._tenths_signed_field("v2 water", "Floor water temperature", 81),
            self._tenths_signed_field("v2 water", "Outdoor temperature", 82),
            self._tenths_signed_field("v2 water", "Auxiliary NTC temperature", 83),
        ]

    def _v2_advanced_fields(self) -> list[TuiField]:
        """Build v2 advanced configuration fields."""
        fields = [
            self._int_field("v2 advanced", "Modbus address", 105, 1, 247),
            self._byte_field("v2 advanced", "Valve origin offset", 85, "msb", 0, 7, "raw"),
            self._byte_field("v2 advanced", "Pump delay", 85, "lsb", 60, 255, "s"),
            self._byte_field("v2 advanced", "Immersion heater delay", 86, "msb", 0, 255, "min"),
            self._signed_byte_field("v2 advanced", "Immersion heater activation temp", 86, "lsb", -128, 127, "C"),
            self._nibble_field("v2 advanced", "Thermostat block level", 87, 0, 0x0F, {i: str(i) for i in range(16)}),
        ]
        fields.extend(self._v2_last_opening_angle_fields())
        for zone_index in range(16):
            fields.append(self._bit_field(
                "v2 advanced",
                "Z{} electrovalve enabled".format(zone_index + 1),
                84,
                zone_index,
                {0: "disabled", 1: "enabled"},
            ))
        return fields

    def _v2_last_opening_angle_fields(self) -> list[TuiField]:
        """Build read-only fields for the last v2 opening-angle commands."""
        angle_by_code = {
            0: "45",
            1: "60",
            2: "75",
            3: "90",
        }

        def last_angle(addr):
            raw = self._context.read_holding_register(addr)
            lsb = raw & 0xFF
            angle_code = (lsb >> 4) & 0x0F
            return "{} ({})".format(angle_by_code.get(angle_code, "unknown"), angle_code)

        def last_zone(addr, first_zone_id):
            raw = self._context.read_holding_register(addr)
            zone_index = raw & 0x0F
            return "Z{} ({})".format(first_zone_id + zone_index, zone_index)

        return [
            TuiField("v2 advanced", "Z1-Z8 last opening angle", 79, lambda: last_angle(79), None, "read-only"),
            TuiField("v2 advanced", "Z1-Z8 last opening angle zone", 79, lambda: last_zone(79, 1), None, "read-only"),
            TuiField("v2 advanced", "Z9-Z16 last opening angle", 80, lambda: last_angle(80), None, "read-only"),
            TuiField("v2 advanced", "Z9-Z16 last opening angle zone", 80, lambda: last_zone(80, 9), None, "read-only"),
        ]

    def _choice_field(self, group: str, label: str, address: int, choices: dict[int, str]) -> TuiField:
        """Build a whole-register choice field."""
        def read(addr=address, opts=choices):
            value = self._context.read_holding_register(addr)
            return "{} ({})".format(opts.get(value, "unknown"), value)

        def write(value_text, addr=address, opts=choices):
            value = self._parse_int(value_text)
            if value not in opts:
                raise ValueError("Allowed values: {}".format(self._choices_label(opts)))
            self._context.write_holding_register(addr, value, 6)

        return TuiField(group, label, address, read, write, self._choices_label(choices))

    def _int_field(self, group: str, label: str, address: int, minimum: int, maximum: int, unit: str = "") -> TuiField:
        """Build a bounded integer field."""
        def read(addr=address, suffix=unit):
            return "{}{}".format(self._context.read_holding_register(addr), " " + suffix if suffix else "")

        def write(value_text, addr=address, lo=minimum, hi=maximum):
            value = self._parse_int(value_text)
            if value < lo or value > hi:
                raise ValueError("{} must be between {} and {}.".format(label, lo, hi))
            self._context.write_holding_register(addr, value, 6)

        bounds = "{}..{}{}".format(minimum, maximum, " " + unit if unit else "")
        return TuiField(group, label, address, read, write, bounds)

    def _half_degree_field(self, group: str, label: str, address: int,
                           minimum: float, maximum: float, writable: bool) -> TuiField:
        """Build a whole-register half-degree Celsius field."""
        def read(addr=address):
            return "{:.1f} C".format(self._context.read_holding_register(addr) / 2)

        def write(value_text, addr=address, lo=minimum, hi=maximum):
            raw = self._parse_half_degree(value_text, lo, hi)
            self._context.write_holding_register(addr, raw, 6)

        return TuiField(
            group,
            label,
            address,
            read,
            write if writable else None,
            "{:.1f}..{:.1f} C step 0.5".format(minimum, maximum),
        )

    def _half_degree_byte_field(self, group: str, label: str, address: int,
                                byte: str, minimum: float, maximum: float) -> TuiField:
        """Build a byte field encoded as half-degree Celsius."""
        def read(addr=address, part=byte):
            raw = self._get_byte(addr, part)
            return "{:.1f} C".format(raw / 2)

        def write(value_text, addr=address, part=byte, lo=minimum, hi=maximum):
            raw = self._parse_half_degree(value_text, lo, hi)
            if raw > 0xFF:
                raise ValueError("{} must encode to one byte.".format(label))
            self._set_byte(addr, part, raw)

        return TuiField(group, label, address, read, write, "{:.1f}..{:.1f} C step 0.5".format(minimum, maximum))

    def _byte_field(self, group: str, label: str, address: int,
                    byte: str, minimum: int, maximum: int, unit: str) -> TuiField:
        """Build a bounded MSB/LSB field."""
        def read(addr=address, part=byte, suffix=unit):
            value = self._get_byte(addr, part)
            return "{}{}".format(value, " " + suffix if suffix else "")

        def write(value_text, addr=address, part=byte, lo=minimum, hi=maximum):
            value = self._parse_int(value_text)
            if value < lo or value > hi:
                raise ValueError("{} must be between {} and {}.".format(label, lo, hi))
            self._set_byte(addr, part, value)

        return TuiField(group, label, address, read, write, "{}..{} {}".format(minimum, maximum, unit).strip())

    def _signed_byte_field(self, group: str, label: str, address: int,
                           byte: str, minimum: int, maximum: int, unit: str) -> TuiField:
        """Build a signed byte field."""
        def read(addr=address, part=byte, suffix=unit):
            raw = self._get_byte(addr, part)
            value = raw - 256 if raw & 0x80 else raw
            return "{}{}".format(value, " " + suffix if suffix else "")

        def write(value_text, addr=address, part=byte, lo=minimum, hi=maximum):
            value = self._parse_int(value_text)
            if value < lo or value > hi:
                raise ValueError("{} must be between {} and {}.".format(label, lo, hi))
            self._set_byte(addr, part, value & 0xFF)

        return TuiField(group, label, address, read, write, "{}..{} {}".format(minimum, maximum, unit).strip())

    def _tenths_signed_field(self, group: str, label: str, address: int) -> TuiField:
        """Build a signed tenths-of-degree read-only field."""
        def read(addr=address):
            raw = self._context.read_holding_register(addr)
            value = raw - 0x10000 if raw & 0x8000 else raw
            return "{:.1f} C".format(value / 10)

        return TuiField(group, label, address, read, None, "read-only")

    def _nibble_field(self, group: str, label: str, address: int, shift: int,
                      mask: int, choices: dict[int, str]) -> TuiField:
        """Build a nibble choice field."""
        def read(addr=address, bit_shift=shift, opts=choices):
            raw = self._context.read_holding_register(addr)
            value = (raw >> bit_shift) & mask
            return "{} ({})".format(opts.get(value, "unknown"), value)

        def write(value_text, addr=address, bit_shift=shift, opts=choices):
            value = self._parse_int(value_text)
            if value not in opts:
                raise ValueError("Allowed values: {}".format(self._choices_label(opts)))
            raw = self._context.read_holding_register(addr)
            updated = (raw & ~(mask << bit_shift)) | ((value & mask) << bit_shift)
            self._context.write_holding_register(addr, updated, 6)

        return TuiField(group, label, address, read, write, self._choices_label(choices))

    def _bit_field(self, group: str, label: str, address: int, bit: int,
                   choices: dict[int, str]) -> TuiField:
        """Build a boolean bit field."""
        def read(addr=address, bit_index=bit, opts=choices):
            value = 1 if self._context.read_holding_register(addr) & (1 << bit_index) else 0
            return "{} ({})".format(opts[value], value)

        def write(value_text, addr=address, bit_index=bit):
            value = self._parse_int(value_text)
            if value not in (0, 1):
                raise ValueError("{} must be 0 or 1.".format(label))
            raw = self._context.read_holding_register(addr)
            updated = (raw | (1 << bit_index)) if value else (raw & ~(1 << bit_index))
            self._context.write_holding_register(addr, updated, 6)

        return TuiField(group, label, address, read, write, self._choices_label(choices))

    def _get_byte(self, address: int, byte: str) -> int:
        """Read one byte from a 16-bit register."""
        raw = self._context.read_holding_register(address)
        return ((raw >> 8) & 0xFF) if byte == "msb" else (raw & 0xFF)

    def _set_byte(self, address: int, byte: str, value: int) -> None:
        """Write one byte while preserving the other byte."""
        raw = self._context.read_holding_register(address)
        if byte == "msb":
            updated = ((value & 0xFF) << 8) | (raw & 0x00FF)
        else:
            updated = (raw & 0xFF00) | (value & 0xFF)
        self._context.write_holding_register(address, updated, 6)

    @staticmethod
    def _parse_int(value_text: str) -> int:
        """Parse an integer from decimal or hexadecimal input."""
        return int(value_text.strip(), 0)

    @staticmethod
    def _parse_half_degree(value_text: str, minimum: float, maximum: float) -> int:
        """Parse and validate a half-degree Celsius value."""
        value = float(value_text.strip())
        if value < minimum or value > maximum:
            raise ValueError("Value must be between {} and {} C.".format(minimum, maximum))
        raw = round(value * 2)
        if abs((value * 2) - raw) > 0.000001:
            raise ValueError("Value must use 0.5 C steps.")
        return raw

    @staticmethod
    def _choices_label(choices: dict[int, str]) -> str:
        """Return a compact choice description."""
        return ", ".join("{}={}".format(key, value) for key, value in choices.items())

    @staticmethod
    def _prompt(screen,
                prompt: str,
                max_length: int,
                ) -> str:
        """Read one prompt value from the status line."""
        curses.echo()
        FriendlyRegisterTui._set_cursor(1)
        height, width = screen.getmaxyx()
        screen.move(height - 1, 0)
        screen.clrtoeol()
        screen.addnstr(height - 1, 0, prompt, width - 1)
        try:
            raw_value = screen.getstr(height - 1, min(len(prompt), width - 1), max_length)
            return raw_value.decode("ascii").strip()
        finally:
            curses.noecho()
            FriendlyRegisterTui._set_cursor(0)

    @staticmethod
    def _set_cursor(visibility: int) -> None:
        """Best-effort cursor visibility update for terminals that support it."""
        try:
            curses.curs_set(visibility)
        except curses.error:
            pass


def start_tui(args: argparse.Namespace) -> None:
    """Start the optional register TUI in a daemon thread."""
    if not args.tui:
        return
    thread = threading.Thread(
        target=FriendlyRegisterTui(args.device_context, args.profile).run,
        name="koolnova-register-tui",
        daemon=True,
    )
    thread.start()


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
    start_tui(run_args)
    await run_server_simulator(run_args)


if __name__ == "__main__":
    asyncio.run(main())
