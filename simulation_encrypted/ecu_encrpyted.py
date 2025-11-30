#!/usr/bin/env python3

import socket
import struct
import json
from datetime import datetime
from ascon import decrypt as ascon_decrypt

LISTEN_PORT = 5000
LOW_PRESSURE_THRESHOLD = 30.0

SYNC_WORD = bytes([0x2D, 0xD4])

# Load all sensor keys from ECU database
def load_sensor_keys():
    try:
        with open('keys/ecu_key.json', 'r') as f:
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
        # Fallback to single hardcoded key for default sensor
        return {
            0xA0A6F9: {
                'key': bytes.fromhex('000102030405060708090a0b0c0d0e0f'),
                'position': 'front_left'
            }
        }


SENSOR_KEYS = load_sensor_keys()


def find_sync_word(data):
    for i in range(len(data) - 1):
        if data[i:i+2] == SYNC_WORD:
            return i
    return -1


def decrypt_and_verify_packet(packet):
    sync_index = find_sync_word(packet)
    if sync_index == -1:
        return None, "No sync word"
    
    offset = sync_index + 2
    expected_length = 16 + 5 + 16
    
    if len(packet) < offset + expected_length:
        return None, "Packet too short"
    
    nonce = packet[offset:offset+16]
    offset += 16
    ciphertext_with_tag = packet[offset:offset+21]
    associated_data = b''
    
    # Try decrypting with each known sensor key
    for sensor_id, sensor_info in SENSOR_KEYS.items():
        plaintext = ascon_decrypt(
            key=sensor_info['key'],
            nonce=nonce,
            associateddata=associated_data,
            ciphertext=ciphertext_with_tag
        )
        
        if plaintext is not None:
            # Successfully decrypted with this key
            if len(plaintext) != 5:
                continue
            
            decoded_sensor_id = struct.unpack('>I', b'\x00' + plaintext[0:3])[0]
            
            # Verify the sensor ID matches
            if decoded_sensor_id == sensor_id:
                flags = plaintext[3]
                pressure_raw = plaintext[4]
                pressure_psi = pressure_raw / 2.755
                
                return {
                    'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'id': f"{sensor_id:06X}",
                    'position': sensor_info['position'],
                    'flags': flags,
                    'pressure_PSI': round(pressure_psi, 3),
                    'authenticated': True
                }, None
    
    return None, "Authentication failed - unknown sensor"


def process_packet(packet):
    decoded, error = decrypt_and_verify_packet(packet)
    
    if error:
        print(f"Rejected: {error}")
        return
    
    position_display = decoded['position'].replace('_', ' ').title()
    print(f"[{decoded['id']}] {position_display:12s} {decoded['pressure_PSI']:.3f} PSI (flags: {decoded['flags']})")
    
    if decoded['pressure_PSI'] < LOW_PRESSURE_THRESHOLD:
        print("WARNING: LOW TIRE PRESSURE")


def receive_packet(sock):
    try:
        data, address = sock.recvfrom(1024)
        return data
    except socket.timeout:
        return None
    except Exception:
        return None


def run_ecu():
    print(f"ECU listening on port {LISTEN_PORT}")
    print(f"Monitoring {len(SENSOR_KEYS)} sensor(s):")
    for sensor_id, info in SENSOR_KEYS.items():
        position = info['position'].replace('_', ' ').title()
        print(f"  - 0x{sensor_id:06X}: {position}")
    print()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', LISTEN_PORT))
    sock.settimeout(1.0)
    
    try:
        packet_count = 0
        authenticated_count = 0
        rejected_count = 0
        
        while True:
            packet = receive_packet(sock)
            
            if packet:
                packet_count += 1
                decoded, error = decrypt_and_verify_packet(packet)
                
                if decoded:
                    authenticated_count += 1
                    process_packet(packet)
                else:
                    rejected_count += 1
                    print(f"Rejected: {error}")
            
    except KeyboardInterrupt:
        print(f"\nECU stopped")
        print(f"Packets: {packet_count} | Authenticated: {authenticated_count} | Rejected: {rejected_count}")
    finally:
        sock.close()


if __name__ == "__main__":
    run_ecu()