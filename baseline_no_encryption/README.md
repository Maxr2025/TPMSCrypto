# TPMS Binary Protocol Simulation 

Simulates the exact binary packet format used by 2012 Subaru TPMS sensors (Schrader SMD3MA4). This was collected in tpms_data_subi.json

## Packet Structure

17-byte packets matching real RF transmissions:

```
[Preamble: 8B][Sync: 2B][ID: 3B][Flags: 1B][Pressure: 1B][CRC: 2B]
55 55 55 55... 2D D4    A0A6F9  05        67          XX XX
```

- **Preamble**: Clock synchronization (0x55 repeated)
- **Sync Word**: 0x2DD4 (identifies Schrader sensor)
- **Sensor ID**: 3-byte unique identifier (static, never changes)
- **Flags**: Status byte (typically 5 or 7)
- **Pressure**: Encoded as PSI × 2.755
- **CRC**: CRC-16 checksum for integrity

## Files
- `sensor_subaru.py` - Broadcasts binary TPMS packets
- `ecu_subaru.py` - Receives and decodes packets
- `eavesdropper_subaru.py` - Intercepts packets (demonstrates vulnerability)


## Usage

Open three terminals:

```bash
# Terminal 1: Sensor
python3 sensor_subaru.py

# Terminal 2: ECU
python3 ecu_subaru.py

# Terminal 3: Eavesdropper
python3 eavesdropper_subaru.py
```

## What This Demonstrates

**Privacy Vulnerability**: Static sensor IDs enable vehicle tracking. The eavesdropper can intercept broadcasts and track vehicles by their unchanging sensor IDs.

**No Encryption**: All data transmitted in plaintext. Anyone with an SDR can decode pressure and identify vehicles.

**No Authentication**: CRC provides integrity but not authenticity.

## Output Format

Matches rtl_433 decoder output:

```json
{
  "time": "2025-10-26 17:20:42",
  "model": "Schrader-SMD3MA4",
  "type": "TPMS",
  "flags": 5,
  "id": "A0A6F9",
  "pressure_PSI": 37.050
}
```

## Technical Details

- Protocol: Schrader TPMS (rtl_433 Protocol 156)
- Frequency: 315 MHz (North America)
- Modulation: FSK (simulated via UDP broadcast)
- Packet Size: 17 bytes
- Transmission: UDP broadcast on port 5000



