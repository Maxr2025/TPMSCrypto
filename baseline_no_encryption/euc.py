#!/usr/bin/env python3
# ECU (Engine Control Unit) - this is what is supposed to get the TPMS signals 
# 2012 Suburu Protocols 

import socket
import struct
from datetime import datetime

# Configuration
LISTEN_PORT = 5000
LOW_PRESSURE_THRESHOLD = 30.0

# Schrader Protocol Constants
SYNC_WORD = bytes([0x2D, 0xD4])


def find_sync_word(data):
    for i in range(len(data) - 1):
        if data[i:i+2] == SYNC_WORD:
            return i
    return -1


def calculate_crc(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return crc


def decode_packet(packet):
# to be able to read it. 
    sync_index = find_sync_word(packet)
    if sync_index == -1:
        return None
    
    offset = sync_index + 2
    
    if len(packet) < offset + 7:
        return None
    
    data = packet[offset:offset+5]
    
    received_crc = struct.unpack('>H', packet[offset+5:offset+7])[0]
    calculated_crc = calculate_crc(data)
    
    crc_valid = (received_crc == calculated_crc)
    
    if not crc_valid:
        print(f"[ECU] ⚠️  CRC MISMATCH! Received: {received_crc:04X}, "
              f"Calculated: {calculated_crc:04X}")
    
    sensor_id = struct.unpack('>I', b'\x00' + data[0:3])[0]
    flags = data[3]
    pressure_raw = data[4]
    
    # Convert pressure
    pressure_psi = pressure_raw / 2.755
    
    # Return in rtl_433 format, this was used for tpms_data_subi.json capture 
    return {
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'model': 'Schrader-SMD3MA4',
        'type': 'TPMS',
        'flags': flags,
        'id': f"{sensor_id:06X}",
        'pressure_PSI': round(pressure_psi, 3),
        'crc_valid': crc_valid
    }


def process_packet(packet):
    decoded = decode_packet(packet)
    
    if decoded is None:
        print(f"Invalid packet (no sync or too short)")
        return
    
    # Display in format similar to rtl_433
    crc_status = "✓" if decoded['crc_valid'] else "✗"
    
    print(f"**** Received from sensor {decoded['id']}:")
    print(f"Pressure: {decoded['pressure_PSI']:.3f} PSI")
    print(f"Flags: {decoded['flags']}")
    print(f"CRC: {'Valid' if decoded['crc_valid'] else 'INVALID'}")
    
    # Low pressure warning
    if decoded['pressure_PSI'] < LOW_PRESSURE_THRESHOLD:
        print(f"WARNING: LOW TIRE PRESSURE!!!!!!")
    
    # Show as JSON (like rtl_433 output)
    import json
    json_output = {k: v for k, v in decoded.items() if k != 'crc_valid'}
    print(f"JSON: {json.dumps(json_output)}")
    print()


def receive_packet(sock):
    try:
        data, address = sock.recvfrom(1024)
        return data
    except socket.timeout:
        return None
    except Exception as e:
        print(f"[ECU] Error: {e}")
        return None


def run_ecu():
    

    print("ECU RECEIVER - Listening on port {LISTEN_PORT}\n")
    
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', LISTEN_PORT))
    sock.settimeout(1.0)
    
    try:
        packet_count = 0
        while True:
            packet = receive_packet(sock)
            
            if packet:
                process_packet(packet)
                packet_count += 1
            
    except KeyboardInterrupt:
        print(f"\n\nECU stopped. Received {packet_count} packets.")
    finally:
        sock.close()


if __name__ == "__main__":
    print("\nStarting ECU...")
    run_ecu()