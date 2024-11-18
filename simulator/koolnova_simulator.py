#!/usr/bin/env python3

# @Brief Pymodbus Koolnova Modbus RTU simulator.
#        A simulator datastore with json interface.

import os,sys
import argparse
import asyncio
import logging
import json

from pymodbus import pymodbus_apply_logging_config
from pymodbus.datastore import ModbusServerContext, ModbusSimulatorContext
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server import StartAsyncSerialServer

_logger = logging.getLogger(__file__)

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
    args = parser.parse_args()
    return args


def setup_simulator() -> argparse.Namespace:
    """ Run server setup.
    """
    args = get_commandline()
    pymodbus_apply_logging_config(args.log.upper())
    _logger.setLevel(args.log.upper())

    # open and read json file
    with open(args.config, 'r') as f:
        setup = json.load(f)

    try:
        # Modbus Simulator
        context = ModbusSimulatorContext(setup['device_list']['device'], None)
    except RuntimeError as e:
        _logger.error("error with json file: {}".format(e))
        return None

    # Master collection of slave contexts
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
