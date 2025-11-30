# Secure TPMS with ASCON Encryption

A proof-of-concept implementation of secure Tire Pressure Monitoring System (TPMS) using ASCON-128 authenticated encryption to prevent vehicle tracking and packet spoofing.

ASCON-128 authenticated encryption with:
- Random nonces (prevents tracking)
- Encrypted payloads (protects data)
- Authentication tags (prevents spoofing)
- Unique keys per sensor (key isolation)

## Quick Start

### 1. Pair All Sensors
```bash
python3 pairing.py A0A6F9 front_left
python3 pairing.py B1C2D3 front_right
python3 pairing.py C3E4F5 rear_left
python3 pairing.py D4F6A7 rear_right
```

### 2. Run ECU
```bash
python3 ecu_encrypted.py
```

### 3. Run Sensor(s)
```bash
python3 sensor_encrypted.py
# Select tire: 1 (Front Left), 2 (Front Right), 3 (Rear Left), or 4 (Rear Right)
```

## Files

| File | Purpose |
|------|---------|
| `sensor_encrypted.py` | Encrypted TPMS sensor (select tire 1-4) |
| `ecu_encrypted.py` | ECU receiver (authenticates all sensors) |
| `pairing.py` | Diffie-Hellman key establishment |
| `eavesdropper.py` | Demonstrates encryption prevents attacks |


## Security Features

| Feature | Implementation | Benefit |
|---------|---------------|---------|
| **Privacy** | Random 128-bit nonces | Prevents vehicle tracking |
| **Confidentiality** | ASCON-128 encryption | Hides tire pressure data |
| **Authenticity** | 128-bit auth tags | Prevents packet spoofing |
| **Integrity** | Cryptographic verification | Blocks message tampering |
| **Key Isolation** | Unique key per sensor | Limits compromise impact |

## Packet Format

**Baseline (17 bytes) - Vulnerable:**
```
[Preamble: 8B][Sync: 2B][Sensor ID: 3B][Flags: 1B][Pressure: 1B][CRC: 2B]
                         ^^^^^^^^^^^^                ^^^^^^^^^^^
                         Static (tracking)           Plaintext
```

**ASCON (47 bytes) - Secure:**
```
[Preamble: 8B][Sync: 2B][Nonce: 16B][Encrypted: 5B][Auth Tag: 16B]
                         ^^^^^^^^^^^  ^^^^^^^^^^^^^  ^^^^^^^^^^^^^
                         Random       Hidden         Verified
```

## Demonstration

### Run All 4 Tires Simultaneously

**Terminal 1:** `python3 ecu_encrypted.py`  
**Terminal 2:** `python3 sensor_encrypted.py` (select 1)  
**Terminal 3:** `python3 sensor_encrypted.py` (select 2)  
**Terminal 4:** `python3 sensor_encrypted.py` (select 3)  
**Terminal 5:** `python3 sensor_encrypted.py` (select 4)

### Output
```
ECU:
[A0A6F9] Front Left   37.421 PSI (flags: 5)
[B1C2D3] Front Right  37.289 PSI (flags: 5)
[C3E4F5] Rear Left    36.821 PSI (flags: 7)
[D4F6A7] Rear Right   36.934 PSI (flags: 5)
```

### Show Attack Prevention

**Terminal 3:** `python3 eavesdropper.py`
```
Intercepted ENCRYPTED packet
  Nonce: ab8739bf... (random, cannot track)
  Data: encrypted (cannot read)
```

## Dependencies

```bash
pip install ascon cryptography --break-system-packages
```

## Key Management

Keys established via Diffie-Hellman during pairing. Each sensor gets unique key stored in:
- `keys/sensor_XXXXXX_key.json` (individual sensor)
- `keys/ecu_key.json` (ECU database)

Keys never transmitted over RF after initial pairing.

## References

- ASCON: NIST Lightweight Cryptography Standard (2023)
- Rouf et al. "Security and Privacy Vulnerabilities of In-Car Wireless Networks" (USENIX 2010)
- Nguyen et al. "ASIC Implementation of ASCON Lightweight Cryptography" (IEEE 2025)