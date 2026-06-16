Here is the comparative technical review of the two Koolnova Modbus tables: **Koolnova v1.0** and **Koolnova 2.0**.

## Quick summary

The **Modbus communication layer and zone registers 40001 to 40064** remain broadly compatible between the two versions: Modbus RTU over RS485, 9600/19200 baud rates, default format 9600 8E1, default address 49, Modbus functions 03 and 06, 16 climate zones with 4 registers per zone.

However, **from register 40065 onward, the 2.0 table changes significantly**. The v1.0 system registers are not simply extended: they are **moved and replaced by a much richer new mapping**.

---

## 1. Modbus layer: overall stability

Both versions use:

| Element             |                                               v1.0 |                                               v2.0 | Impact                 |
| ------------------- | -------------------------------------------------: | -------------------------------------------------: | ---------------------- |
| Physical layer      |                              Modbus RTU over RS485 |                              Modbus RTU over RS485 | Identical              |
| Baud rates          |                                       9600 / 19200 |                                       9600 / 19200 | Identical              |
| Default format      |                                           9600 8E1 |                                           9600 8E1 | Identical              |
| Default address     |                                                 49 |                                                 49 | Identical              |
| Supported functions | 03 Read Holding Register, 06 Write Single Register | 03 Read Holding Register, 06 Write Single Register | Identical              |
| Number of zones     |                                           16 zones |                                           16 zones | Identical              |
| Zone registers      |                                     40001 to 40064 |                                     40001 to 40064 | Functionally identical |

For wiring, both documents keep the same recommendation: shielded twisted pair cable, 120 Ω termination if distances are significant, shield connected to reference/GND, daisy-chain topology, and no star topology.

---

## 2. Zone registers 40001 to 40064: compatibility preserved

The zone structure remains the same:

| Relative zone register | Function                 | Access | Comment                                               |
| ---------------------- | ------------------------ | -----: | ----------------------------------------------------- |
| 40001, 40005, etc.     | Zone status / activation |     RW | bit0 = active/on zone, bit1 = zone present/registered |
| 40002, 40006, etc.     | Mode + fan speed         |     RW | high nibble = fan speed, low nibble = mode            |
| 40003, 40007, etc.     | Setpoint temperature     |     RW | value / 2, range 15 to 35 °C                          |
| 40004, 40008, etc.     | Actual temperature       |      R | value / 2, range 0 to 50 °C                           |

v1.0 refers to “zone in demand”, whereas v2.0 rather refers to “zone on”, but the encoding remains similar: bit0 controls the active/inactive state and bit1 indicates whether the zone exists.

The mode/fan speed register keeps the same logic:

| Value | Meaning                             |
| ----: | ----------------------------------- |
|  0x0X | Fan off / possible general shutdown |
|  0x1X | Low fan speed                       |
|  0x2X | Medium fan speed                    |
|  0x3X | High fan speed                      |
|  0x4X | Automatic fan speed                 |
|  0xX1 | Cooling                             |
|  0xX2 | Heating                             |
|  0xX4 | Underfloor heating                  |
|  0xX5 | Underfloor cooling + cold air       |
|  0xX6 | Underfloor heating + warm air       |

Therefore, for basic zone supervision — opening/closing a zone, reading setpoint, writing setpoint, reading temperature, forcing mode/fan speed — the migration appears relatively straightforward.

---

## 3. Major change: system registers are moved

This is the main point.

In v1.0, the system registers start directly at 40065 with machine-related information:

| v1.0 function                           |   v1.0 address |
| --------------------------------------- | -------------: |
| AC1 to AC4 machine airflow              | 40065 to 40068 |
| AC1 to AC4 machine setpoint temperature | 40069 to 40072 |
| AC1 to AC4 machine airflow programming  | 40073 to 40076 |
| Modbus communication parameters         |          40077 |
| Modbus address                          |          40078 |
| Efficiency/speed balance                |          40079 |
| Infrared gateway code                   |          40080 |
| General system on/off                   |          40081 |
| Global machine mode                     |          40082 |

In v2.0, these functions are moved much further:

| Equivalent function                     |        v1.0 |        v2.0 |
| --------------------------------------- | ----------: | ----------: |
| AC1 to AC4 machine airflow              | 40065-40068 | 40093-40096 |
| AC1 to AC4 machine setpoint temperature | 40069-40072 | 40097-40100 |
| AC1 to AC4 machine airflow programming  | 40073-40076 | 40101-40104 |
| Modbus communication parameters         |       40077 |       40105 |
| Modbus address                          |       40078 |       40106 |
| Infrared gateway code                   |       40080 |       40108 |
| General system on/off                   |       40081 |       40109 |
| Global machine mode                     |       40082 |       40110 |

The v1.0 document describes these functions between 40065 and 40082. The v2.0 document relocates them between 40093 and 40110.

Practical consequence: **compatibility is not guaranteed beyond 40064**. A v1.0 write to 40081 to shut down the system corresponds in v2.0 to a Z9 to Z16 opening-angle register, not to general on/off. This could be functionally dangerous.

---

## 4. New v2.0 registers between 40065 and 40092

v2.0 introduces an advanced system area between 40065 and 40092. This block either did not exist in v1.0.

| v2.0 address | Function                             | Technical comment                                                        |
| -----------: | ------------------------------------ | ------------------------------------------------------------------------ |
|  40065-40072 | Control unit key                     | Key sent digit by digit in ASCII                                         |
|        40073 | CU model and version                 | Model/software version identification                                    |
|        40074 | System parameters                    | Efficiency, ECO, STOP, antifreeze, humidity, DIN/AUX/heating/pump relays |
|        40075 | Active modes                         | Mask of modes available to the user                                      |
|        40076 | Temperature limits                   | Max heating / min cooling                                                |
|        40077 | Automatic changeover + humidity      | Destination modes and humidity threshold                                 |
|        40078 | System time                          | Day/hour/minute bit encoding                                             |
|        40079 | External inputs DIN1/DIN2            | External input configuration                                             |
|        40080 | Opening angle zones 1 to 8           | 45°, 60°, 75°, 90°                                                       |
|        40081 | Opening angle zones 9 to 16          | 45°, 60°, 75°, 90°                                                       |
|        40082 | Underfloor heating water temperature | Reading in tenths of a degree                                            |
|        40083 | Outdoor temperature                  | Signed 16-bit value in tenths of a degree                                |
|        40084 | Auxiliary NTC                        | Signed 16-bit value in tenths of a degree                                |
|        40085 | Electrovalve mask                    | Zones activating the pump or not                                         |
|        40086 | Pump delay + electrovalve offset     | LSB delay, MSB offset                                                    |
|        40087 | Immersion heater                     | Delay + outdoor temperature threshold                                    |
|        40088 | Thermostat lockout                   | 0x00 to 0x0F                                                             |
|        40089 | MAU automatic mode                   | Cold/hot water thresholds                                                |
|  40090-40092 | Mixing valve                         | Curves, temperatures, dew point                                          |

v2.0 therefore adds much more advanced regulation functions: humidity management, active modes, external inputs, opening angles, electrovalves, underfloor heating, outdoor temperature, immersion heater, thermostat lockout, automatic changeover, and mixing valve.

---

## 5. Evolution of the global mode register

In v1.0, the global machine mode register is 40082 with the following values:

| Value | v1.0                          |
| ----: | ----------------------------- |
|     1 | Cooling                       |
|     2 | Heating                       |
|     4 | Underfloor heating            |
|     5 | Underfloor cooling + cold air |
|     6 | Underfloor heating + warm air |

In v2.0, the equivalent function moves to 40110 and adds two modes:

| Value | v2.0                          |
| ----: | ----------------------------- |
|     0 | Ventilation                   |
|     1 | Cooling                       |
|     2 | Heating                       |
|     3 | Dehumidification              |
|     4 | Underfloor heating            |
|     5 | Underfloor cooling + cold air |
|     6 | Underfloor heating + warm air |

v2.0 therefore explicitly adds **ventilation only** and **dehumidification** at global level.

---

## 6. Diagnostic / supervision registers added in v2.0

v2.0 also adds useful read-only registers for detailed supervision:

| v2.0 address | Function                                                         |
| -----------: | ---------------------------------------------------------------- |
|        40111 | Number of thermostats requesting underfloor heating              |
|        40112 | Number of thermostats requesting air in AC3                      |
|  40113-40116 | Sum of the volume of all thermostats connected per AC1 to AC4    |
|  40117-40120 | Sum of the volume of active thermostats in demand per AC1 to AC4 |
|  40121-40125 | Average requested setpoint temperatures per AC1 to AC4           |
|        40126 | MSB = EFI, LSB = AC3 speed                                       |

These registers have no equivalent in v1.0. 
They are useful for a home automation supervisor or BMS, because they make it possible to understand the internal demand, volume, and aggregated setpoint logic.

---

## 7. Documentation quality points to watch

Several points require caution before integration.
* some v2.0 registers use more complex bit-level or MSB/LSB encodings. This is the case for 40074, 40075, 40077, 40078, and 40092. Misinterpreting endianness / high byte / low byte may produce unexpected behavior.
* v2.0 introduces signed and unsigned values depending on the register. For example, 40082 is an unsigned water temperature in tenths of a degree, whereas 40083 and 40084 are signed temperatures in tenths of a degree.
* v2.0 seems to contain a numbering anomaly: average temperatures are listed as 40121, 40122, 40123, then 40125, with 40124 missing in the excerpt. It should be verified on real equipment whether 40124 is actually absent, reserved, or whether this is a documentation typo.

---

## 9. Integration recommendation

For a home automation / BMS / PLC integration, I would split the driver into two profiles:

### Common v1.0 / v2.0 profile

Keep as-is:

| Block                   |        Addresses |
| ----------------------- | ---------------: |
| Zones 1 to 16           |   40001 to 40064 |
| Zone status             | zone register +0 |
| Zone mode/fan speed     | zone register +1 |
| Zone setpoint           | zone register +2 |
| Zone actual temperature | zone register +3 |

### Specific v1.0 profile

Use the old block:

| Function            |     Address |
| ------------------- | ----------: |
| Machine airflow     | 40065-40068 |
| Machine setpoints   | 40069-40072 |
| Airflow programming | 40073-40076 |
| Communication       |       40077 |
| Modbus address      |       40078 |
| General on/off      |       40081 |
| Global mode         |       40082 |

### Specific v2.0 profile

Use the new block:

| Function                   |     Address |
| -------------------------- | ----------: |
| CU identification          | 40065-40073 |
| Advanced system parameters | 40074-40092 |
| Machine airflow            | 40093-40096 |
| Machine setpoints          | 40097-40100 |
| Airflow programming        | 40101-40104 |
| Communication              |       40105 |
| Modbus address             |       40106 |
| General on/off             |       40109 |
| Global mode                |       40110 |
| Advanced supervision       | 40111-40126 |

---
