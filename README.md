# Secure TPMS: ImplementingEncryption for Vehicle Tire Pressure Monitoring Systems

A comprehensive project demonstrating security vulnerabilities in modern TPMS and proposing cryptographic solutions using lightweight encryption.

## Project Overview

Current TPMS implementations transmit unencrypted data with static sensor IDs, enabling vehicle tracking and data interception. This project:

1. Captures and analyzes real TPMS transmissions from a 2012 Subaru
2. Simulates the vulnerability through binary protocol implementation
3. Proposes encryption to secure TPMS communications
4. Implements a proof-of-concept with GNU Radio for RF transmission

## Project Structure

```
├── baseline_no_encryption    # Simple simulation of TPMS and eavesdropping
│   ├── sensor.py             # Basic Schrader SMD3MA4 sensor simulation
│   ├── ecu.py                # ECU receiver
│   └── eavesdropper.py       # Demonstrates interception
│
└── tpms_data_subi.json       # Real HackRF capture data from Oct 26, 2025
```

## Hardware & Tools Used

- **HackRF One**: Software-defined radio for capturing 315 MHz TPMS signals
- **rtl_433**: Protocol decoder for analyzing captured transmissions
- **2012 Subaru**: Test vehicle with Schrader SMD3MA4 sensors
- **Python 3**: Simulation and protocol implementation


## Current Vulnerabilities

1. **Privacy**: Static sensor IDs enable persistent vehicle tracking
2. **Confidentiality**: Plaintext transmission exposes tire pressure data
3. **Authenticity**: No authentication allows packet spoofing attacks
4. **Integrity**: CRC provides error detection but not cryptographic integrity

### Binary Protocol Details

Schrader packets (17 bytes):
```
[Preamble: 8B][Sync: 2B][Sensor ID: 3B][Flags: 1B][Pressure: 1B][CRC: 2B]
```

- Preamble: 0x55 (clock sync)
- Sync: 0x2DD4 (protocol identifier)
- Sensor ID: Static 24-bit identifier
- Pressure: Encoded as PSI × 2.755
- CRC: CRC-16 checksum

## Proposed Solution: ASCON Encryption

ASCON provides lightweight authenticated encryption suitable for resource-constrained TPMS sensors:

- **Nonce-based**: Dynamic identifiers prevent tracking
- **Authenticated encryption**: Protects confidentiality and authenticity
- **Lightweight**: Efficient for embedded systems
- **NIST standard**: Selected for lightweight cryptography (2023)

### Secure Packet Structure
```
[Preamble][Sync][Nonce][Encrypted Data][Authentication Tag]
```

## Implementation Stages

**Stage 1**: Vulnerability demonstration  - COMPLETE
**Stage 2**: ASCON encryption implementation - IN PROGRESS
**Stage 3**: Binary protocol with ASCON
**Stage 4**: GNU Radio RF transmission at 315 MHz

## Future Work

- Complete ASCON encryption integration
- Performance benchmarking on embedded hardware
- Key distribution and management protocols
- Backward compatibility with existing ECUs
- Real-world RF transmission testing

## References

- rtl_433 Schrader decoder: Protocol 156



