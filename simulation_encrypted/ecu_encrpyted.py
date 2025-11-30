#!/usr/bin/env python3

import socket
import struct
from datetime import datetime
from ascon import decrypt as ascon_decrypt

LISTEN_PORT = 5000
LOW_PRESSURE_THRESHOLD = 30.0

try:
    import json
    with open('simulation_encrypted/ecu_key.json', 'r') as f:
        config = json.load(f)
        first_sensor = next(iter(config['sensors'].values()))
        SHARED_KEY = bytes.fromhex(first_sensor['key'])
except FileNotFoundError:
    SHARED_KEY = bytes.fromhex('000102030405060708090a0b0c0d0e0f')

SYNC_WORD = bytes([0x2D, 0xD4])


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
    
    plaintext = ascon_decrypt(
        key=SHARED_KEY,
        nonce=nonce,
        associateddata=associated_data,
        ciphertext=ciphertext_with_tag
    )
    
    if plaintext is None:
        return None, "Authentication failed"
    
    if len(plaintext) != 5:
        return None, f"Invalid plaintext length"
    
    sensor_id = struct.unpack('>I', b'\x00' + plaintext[0:3])[0]
    flags = plaintext[3]
    pressure_raw = plaintext[4]
    pressure_psi = pressure_raw / 2.755
    
    return {
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'model': 'Schrader-SMD3MA4-ASCON',
        'type': 'TPMS-Encrypted',
        'id': f"{sensor_id:06X}",
        'flags': flags,
        'pressure_PSI': round(pressure_psi, 3),
        'authenticated': True
    }, None


def process_packet(packet):
    decoded, error = decrypt_and_verify_packet(packet)
    
    if error:
        print(f"Rejected: {error}")
        return
    
    print(f"Sensor {decoded['id']}: {decoded['pressure_PSI']:.3f} PSI (flags: {decoded['flags']})")
    
    if decoded['pressure_PSI'] < LOW_PRESSURE_THRESHOLD:
        print(f"  WARNING: LOW TIRE PRESSURE")


def receive_packet(sock):
    try:
        data, address = sock.recvfrom(1024)
        return data
    except socket.timeout:
        return None
    except Exception:
        return None


def run_ecu():
    print(f"ECU listening on port {LISTEN_PORT}\n")
    
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