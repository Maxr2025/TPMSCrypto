#!/usr/bin/env python3

import socket
import time
import struct
import secrets
from datetime import datetime
from ascon import encrypt as ascon_encrypt

SENSOR_ID = 0xA0A6F9      
TIRE_POSITION = "front_left"
BASE_PRESSURE = 37.5     
BROADCAST_PORT = 5000
BROADCAST_INTERVAL = 2.0

try:
    import json
    with open('simulation_encrypted/sensor_key.json', 'r') as f:
        config = json.load(f)
        SHARED_KEY = bytes.fromhex(config['key'])
except FileNotFoundError:
    SHARED_KEY = bytes.fromhex('000102030405060708090a0b0c0d0e0f')

PREAMBLE = bytes([0x55] * 8)
SYNC_WORD = bytes([0x2D, 0xD4])


def create_plaintext_payload(sensor_id, pressure_psi, flags=5):
    data = bytearray()
    data.extend(struct.pack('>I', sensor_id)[1:])
    data.append(flags & 0xFF)
    pressure_raw = int(pressure_psi * 2.755)
    data.append(pressure_raw & 0xFF)
    return bytes(data)


def create_encrypted_packet(sensor_id, pressure_psi, flags=5):
    nonce = secrets.token_bytes(16)
    plaintext = create_plaintext_payload(sensor_id, pressure_psi, flags)
    associated_data = b''
    
    ciphertext = ascon_encrypt(
        key=SHARED_KEY,
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


def broadcast_packet(sock, packet, sensor_id, pressure, nonce):
    sock.sendto(packet, ('<broadcast>', BROADCAST_PORT))
    print(f"[{sensor_id:06X}] {pressure:.3f} PSI | Nonce: {nonce.hex()[:16]}...")


def run_sensor():
    print(f"Sensor {SENSOR_ID:06X} starting on port {BROADCAST_PORT}")
    print(f"Broadcasting every {BROADCAST_INTERVAL}s\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    try:
        packet_count = 0
        while True:
            import random
            pressure = BASE_PRESSURE + random.uniform(-0.3, 0.3)
            flags = 5 if packet_count % 5 != 0 else 7
            
            packet, nonce = create_encrypted_packet(
                sensor_id=SENSOR_ID,
                pressure_psi=pressure,
                flags=flags
            )
            
            broadcast_packet(sock, packet, SENSOR_ID, pressure, nonce)
            packet_count += 1
            time.sleep(BROADCAST_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\nSensor stopped. Sent {packet_count} encrypted packets.")
    finally:
        sock.close()


if __name__ == "__main__":
    run_sensor()