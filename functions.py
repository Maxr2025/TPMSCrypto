#!/usr/bin/env python3

import struct
import secrets
import json
from ascon import encrypt as ascon_encrypt, decrypt as ascon_decrypt

# Constants
PREAMBLE = bytes([0x55] * 8)
SYNC_WORD = bytes([0x2D, 0xD4])

# Tire configurations
TIRE_CONFIGS = {
    0xA0A6F9: {'position': 'front_left', 'key_file': 'simulation_encrypted/keys/sensor_A0A6F9_key.json'},
    0xB1C2D3: {'position': 'front_right', 'key_file': 'simulation_encrypted/keys/sensor_B1C2D3_key.json'},
    0xC3E4F5: {'position': 'rear_left', 'key_file': 'simulation_encrypted/keys/sensor_C3E4F5_key.json'},
    0xD4F6A7: {'position': 'rear_right', 'key_file': 'simulation_encrypted/keys/sensor_D4F6A7_key.json'}
}


def load_sensor_key(sensor_id):
    
    if sensor_id not in TIRE_CONFIGS:
        raise ValueError(f"Unknown sensor ID: 0x{sensor_id:06X}")
    
    key_file = TIRE_CONFIGS[sensor_id]['key_file']
    
    try:
        with open(key_file, 'r') as f:
            config = json.load(f)
            return bytes.fromhex(config['key'])
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Key file not found: {key_file}\n"
            f"Run: python3 pairing.py {sensor_id:06X} {TIRE_CONFIGS[sensor_id]['position']}"
        )


def load_all_sensor_keys():
    
    try:
        with open('simulation_encrypted/keys/ecu_key.json', 'r') as f:
            config = json.load(f)
            sensor_keys = {}
            for sensor_id_hex, sensor_data in config['sensors'].items():
                sensor_id = int(sensor_id_hex, 16)
                sensor_keys[sensor_id] = {
                    'key': bytes.fromhex(sensor_data['key']),
                    'position': sensor_data.get('tire_position', 'unknown')
                }
            return sensor_keys
    except FileNotFoundError:
        raise FileNotFoundError(
            "ECU key file not found: simulation_encrypted/keys/ecu_key.json\n"
            "Pair sensors first using pairing.py"
        )


def encrypt_tpms_packet(sensor_id, pressure_psi, flags=5):
    
    # Load the encryption key for this sensor
    shared_key = load_sensor_key(sensor_id)
    
    # Generate random 128-bit nonce (prevents tracking)
    nonce = secrets.token_bytes(16)
    
    # Create plaintext payload (5 bytes)
    plaintext = bytearray()
    plaintext.extend(struct.pack('>I', sensor_id)[1:])  # 3 bytes: sensor ID
    plaintext.append(flags & 0xFF)                       # 1 byte: flags
    pressure_raw = int(pressure_psi * 2.755)
    plaintext.append(pressure_raw & 0xFF)                # 1 byte: pressure
    plaintext = bytes(plaintext)
    
    # Encrypt with ASCON-128 (produces ciphertext + 16-byte auth tag)
    associated_data = b''
    ciphertext = ascon_encrypt(
        key=shared_key,
        nonce=nonce,
        associateddata=associated_data,
        plaintext=plaintext
    )
    
    # Build complete packet
    packet = bytearray()
    packet.extend(PREAMBLE)      # 8 bytes
    packet.extend(SYNC_WORD)     # 2 bytes
    packet.extend(nonce)         # 16 bytes
    packet.extend(ciphertext)    # 21 bytes (5 encrypted + 16 auth tag)
    
    return bytes(packet)


def decrypt_tpms_packet(bitstream):
    
    # Find sync word
    sync_index = -1
    for i in range(len(bitstream) - 1):
        if bitstream[i:i+2] == SYNC_WORD:
            sync_index = i
            break
    
    if sync_index == -1:
        return None  # No sync word found
    
    # Parse packet structure
    offset = sync_index + 2
    expected_length = 16 + 5 + 16  # nonce + plaintext + auth_tag
    
    if len(bitstream) < offset + expected_length:
        return None  # Packet too short
    
    nonce = bitstream[offset:offset+16]
    offset += 16
    ciphertext_with_tag = bitstream[offset:offset+21]
    associated_data = b''
    
    # Load all known sensor keys
    try:
        sensor_keys = load_all_sensor_keys()
    except FileNotFoundError:
        return None
    
    # Try decrypting with each known sensor key
    for sensor_id, sensor_info in sensor_keys.items():
        try:
            plaintext = ascon_decrypt(
                key=sensor_info['key'],
                nonce=nonce,
                associateddata=associated_data,
                ciphertext=ciphertext_with_tag
            )
            
            if plaintext is not None and len(plaintext) == 5:
                # Decode plaintext
                decoded_sensor_id = struct.unpack('>I', b'\x00' + plaintext[0:3])[0]
                
                # Verify the sensor ID matches
                if decoded_sensor_id == sensor_id:
                    flags = plaintext[3]
                    pressure_raw = plaintext[4]
                    pressure_psi = pressure_raw / 2.755
                    
                    return {
                        'sensor_id': f"{sensor_id:06X}",
                        'position': sensor_info['position'],
                        'pressure_psi': round(pressure_psi, 3),
                        'flags': flags,
                        'authenticated': True
                    }
        except Exception:
            continue
    
    return None  # Authentication failed


if __name__ == "__main__":
    # Example usage and testing
    print("TPMS Encryption/Decryption Functions")
    print("=" * 50)
    print()
    
    # Test encoding
    print("Test 1: Encrypt TPMS packet")
    print("-" * 50)
    sensor_id = 0xA0A6F9
    pressure = 37.5
    flags = 5
    
    try:
        packet = encrypt_tpms_packet(sensor_id, pressure, flags)
        print(f"Sensor ID: 0x{sensor_id:06X}")
        print(f"Pressure: {pressure} PSI")
        print(f"Flags: {flags}")
        print(f"Packet length: {len(packet)} bytes")
        print(f"Packet hex: {packet.hex()}")
        print()
        
        # Test decoding
        print("Test 2: Decrypt TPMS packet")
        print("-" * 50)
        decoded = decrypt_tpms_packet(packet)
        
        if decoded:
            print(f"✓ Authentication successful")
            print(f"  Sensor ID: {decoded['sensor_id']}")
            print(f"  Position: {decoded['position']}")
            print(f"  Pressure: {decoded['pressure_psi']:.3f} PSI")
            print(f"  Flags: {decoded['flags']}")
        else:
            print("✗ Authentication failed")
        
        print()
        
        # Test with all sensors
        print("Test 3: All sensors")
        print("-" * 50)
        test_sensors = [
            (0xA0A6F9, 37.5, "Front Left"),
            (0xB1C2D3, 37.3, "Front Right"),
            (0xC3E4F5, 36.8, "Rear Left"),
            (0xD4F6A7, 36.9, "Rear Right")
        ]
        
        for sid, psi, name in test_sensors:
            try:
                pkt = encrypt_tpms_packet(sid, psi)
                dec = decrypt_tpms_packet(pkt)
                if dec:
                    print(f"✓ [{dec['sensor_id']}] {name:12s} {dec['pressure_psi']:.3f} PSI")
                else:
                    print(f"✗ [{sid:06X}] {name:12s} Authentication failed")
            except Exception as e:
                print(f"✗ [{sid:06X}] {name:12s} Error: {e}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print()
        print("Please pair sensors first:")
        print("  python3 pairing.py A0A6F9 front_left")
        print("  python3 pairing.py B1C2D3 front_right")
        print("  python3 pairing.py C3E4F5 rear_left")
        print("  python3 pairing.py D4F6A7 rear_right")
    except Exception as e:
        print(f"Error: {e}")