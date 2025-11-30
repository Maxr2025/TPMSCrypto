#!/usr/bin/env python3

import socket
import time
import struct
import secrets
import json
from datetime import datetime
from ascon import encrypt as ascon_encrypt

BROADCAST_PORT = 5000
BROADCAST_INTERVAL = 2.0

PREAMBLE = bytes([0x55] * 8)
SYNC_WORD = bytes([0x2D, 0xD4])

# Tire configurations
TIRES = {
    '1': {'id': 0xA0A6F9, 'position': 'front_left', 'base_pressure': 37.5},
    '2': {'id': 0xB1C2D3, 'position': 'front_right', 'base_pressure': 37.3},
    '3': {'id': 0xC3E4F5, 'position': 'rear_left', 'base_pressure': 36.8},
    '4': {'id': 0xD4F6A7, 'position': 'rear_right', 'base_pressure': 36.9}
}


def load_sensor_key(sensor_id):
    # Try to load from individual sensor key file
    sensor_key_file = f"keys/sensor_{sensor_id:06X}_key.json"
    
    try:
        with open(sensor_key_file, 'r') as f:
            config = json.load(f)
            return bytes.fromhex(config['key']), sensor_key_file
    except FileNotFoundError:
        # Fallback to hardcoded key
        return bytes.fromhex('000102030405060708090a0b0c0d0e0f'), None


def select_tire():
    print("\nSelect tire to simulate:")
    print("  1. Front Left  (0xA0A6F9)")
    print("  2. Front Right (0xB1C2D3)")
    print("  3. Rear Left   (0xC3E4F5)")
    print("  4. Rear Right  (0xD4F6A7)")
    print()
    
    while True:
        choice = input("Enter tire number (1-4): ").strip()
        if choice in TIRES:
            return choice
        print("Invalid choice. Please enter 1, 2, 3, or 4.")


def create_plaintext_payload(sensor_id, pressure_psi, flags=5):
    data = bytearray()
    data.extend(struct.pack('>I', sensor_id)[1:])
    data.append(flags & 0xFF)
    pressure_raw = int(pressure_psi * 2.755)
    data.append(pressure_raw & 0xFF)
    return bytes(data)


def create_encrypted_packet(sensor_id, pressure_psi, flags, shared_key):
    nonce = secrets.token_bytes(16)
    plaintext = create_plaintext_payload(sensor_id, pressure_psi, flags)
    associated_data = b''
    
    ciphertext = ascon_encrypt(
        key=shared_key,
        nonce=nonce,
        associateddata=associated_data,
        plaintext=plaintext
    )
    
    packet = bytearray()
    packet.extend(PREAMBLE)
    packet.extend(SYNC_WORD)
    packet.extend(nonce)
    packet.extend(ciphertext)
    
    return bytes(packet), nonce


def broadcast_packet(sock, packet, sensor_id, pressure, position):
    sock.sendto(packet, ('<broadcast>', BROADCAST_PORT))
    print(f"[{sensor_id:06X}] {position:12s} {pressure:.3f} PSI")


def run_sensor():
    choice = select_tire()
    tire = TIRES[choice]
    
    sensor_id = tire['id']
    position = tire['position']
    base_pressure = tire['base_pressure']
    sensor_id_hex = f"0x{sensor_id:06X}"
    
    shared_key, key_file = load_sensor_key(sensor_id)
    
    print()
    print(f"Simulating: {position.upper().replace('_', ' ')}")
    print(f"Sensor ID: {sensor_id_hex}")
    print(f"Base pressure: {base_pressure} PSI")
    
    if key_file:
        print(f"Loaded key from: {key_file}")
    else:
        print(f"Using hardcoded key (sensor not paired)")
        print(f"Run: python3 pairing.py {sensor_id:06X} {position}")
    
    print(f"Broadcasting every {BROADCAST_INTERVAL}s on port {BROADCAST_PORT}")
    print()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    try:
        packet_count = 0
        while True:
            import random
            pressure = base_pressure + random.uniform(-0.3, 0.3)
            flags = 5 if packet_count % 5 != 0 else 7
            
            packet, nonce = create_encrypted_packet(sensor_id, pressure, flags, shared_key)
            broadcast_packet(sock, packet, sensor_id, pressure, position)
            
            packet_count += 1
            time.sleep(BROADCAST_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\nSensor stopped. Sent {packet_count} encrypted packets.")
    finally:
        sock.close()


if __name__ == "__main__":
    run_sensor()