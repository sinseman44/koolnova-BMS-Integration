# Koolnova RTU Simulator

```
usage: koolnova_simulator.py [-h] [--log {critical,error,warning,info,debug}] [--config CONFIG]

Run koolnova simulator.

optional arguments:
  -h, --help            show this help message and exit
  --log {critical,error,warning,info,debug}
                        set log level, default is info
  --config CONFIG       JSON Config path file
```

Example :<br />
```
Koolnova-Simulator|⇒  python3 koolnova_simulator.py --log=debug --config server.json

2024-11-05 19:50:56,447 DEBUG transport:250 Awaiting connections server_listener
2024-11-05 19:50:56,459 INFO  async_io:301 Server listening.
2024-11-05 19:50:56,460 DEBUG transport:270 Connected to server
2024-11-05 19:52:26,303 DEBUG transport:322 recv: 0x1 0x3 0x0 old_data:  addr=None
2024-11-05 19:52:26,303 DEBUG async_io:123 Handling data: 0x1 0x3 0x0
2024-11-05 19:52:26,303 DEBUG base:92 Processing: 0x1 0x3 0x0
2024-11-05 19:52:26,303 DEBUG rtu:105 Short frame: 0x1 0x3 0x0 wait for more data
2024-11-05 19:52:26,319 DEBUG transport:322 recv: 0x50 0x0 0x1 0x84 0x1b old_data:  addr=None
2024-11-05 19:52:26,319 DEBUG async_io:123 Handling data: 0x1 0x3 0x0 0x50 0x0 0x1 0x84 0x1b
2024-11-05 19:52:26,319 DEBUG base:92 Processing: 0x1 0x3 0x0 0x50 0x0 0x1 0x84 0x1b
2024-11-05 19:52:26,319 DEBUG decoders:103 decode PDU for 3
2024-11-05 19:52:26,319 DEBUG base:102 Frame advanced, resetting header!!
2024-11-05 19:52:26,320 DEBUG transport:379 send: 0x1 0x3 0x2 0x0 0x1 0x79 0x84
2024-11-05 19:52:35,733 DEBUG transport:322 recv: 0x1 0x3 0x0 0x8 0x0 old_data:  addr=None
2024-11-05 19:52:35,733 DEBUG async_io:123 Handling data: 0x1 0x3 0x0 0x8 0x0
2024-11-05 19:52:35,733 DEBUG base:92 Processing: 0x1 0x3 0x0 0x8 0x0
2024-11-05 19:52:35,733 DEBUG rtu:115 Frame - not ready
2024-11-05 19:52:35,751 DEBUG transport:322 recv: 0x4 0xc5 0xcb old_data:  addr=None
2024-11-05 19:52:35,752 DEBUG async_io:123 Handling data: 0x1 0x3 0x0 0x8 0x0 0x4 0xc5 0xcb
2024-11-05 19:52:35,752 DEBUG base:92 Processing: 0x1 0x3 0x0 0x8 0x0 0x4 0xc5 0xcb
2024-11-05 19:52:35,752 DEBUG decoders:103 decode PDU for 3
```
