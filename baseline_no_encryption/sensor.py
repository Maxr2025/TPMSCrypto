#!/usr/bin/env python3
# REALISTIC TPMS SENSOR - Exact 2012 Subaru Format

import socket
import time
import struct
from datetime import datetime

# Configuration - from tpms_data_subi.json
SENSOR_ID = 0xA0A6F9      
TIRE_POSITION = "front_left"
BASE_PRESSURE = 37.5     
BROADCAST_PORT = 5000
BROADCAST_INTERVAL = 2.0

# Schrader Protocol Constants
PREAMBLE = bytes([0x55] * 8)         # 8 bytes of 0x55
SYNC_WORD = bytes([0x2D, 0xD4])      # Schrader sync


def calculate_crc(data):
    #Calculate CRC-16 checksum.
    
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return struct.pack('>H', crc)


def create_binary_packet(sensor_id, pressure_psi, flags=5):
 # Create binary TPMS packet matching YOUR 2012 Subaru.

    data = bytearray()
    
    # Sensor ID (3 bytes, big-endian)
    data.extend(struct.pack('>I', sensor_id)[1:])
    
    # Flags (1 byte)
    data.append(flags & 0xFF)
    
    # Pressure encoding (1 byte)
    # Schrader encoding: raw = PSI * 2.755
    pressure_raw = int(pressure_psi * 2.755)
    data.append(pressure_raw & 0xFF)
    
    # Calculate CRC over the data
    crc = calculate_crc(data)
    
    packet = bytearray()
    packet.extend(PREAMBLE)      # 8 bytes
    packet.extend(SYNC_WORD)     # 2 bytes
    packet.extend(data)          # 5 bytes (ID + flags + pressure)
    packet.extend(crc)           # 2 bytes
    
    return bytes(packet)


def packet_to_hex_string(packet):
    #Convert packet bytes to readable hex string.
    return ' '.join(f'{b:02X}' for b in packet)


def broadcast_packet(sock, packet, sensor_id, pressure):
    # Broadcast binary packet over UDP.
    
    sock.sendto(packet, ('<broadcast>', BROADCAST_PORT))
    
    print(f"[SENSOR {sensor_id:06X}] Broadcasted: {pressure:.3f} PSI")
    print(f"  Binary ({len(packet)} bytes): {packet_to_hex_string(packet)}")


def decode_own_packet(packet):
    # decoding packet to see I am sending correcnt thing
    
    offset = 10
    
    # sensor ID 
    sensor_id = struct.unpack('>I', b'\x00' + packet[offset:offset+3])[0]
    offset += 3
    
    # flags
    flags = packet[offset]
    offset += 1
    
    #  pressure
    pressure_raw = packet[offset]
    pressure_psi = pressure_raw / 2.755
    
    # Return in same format as my rtl_433 capture in tpms_data_subi.json
    return {
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'model': 'Schrader-SMD3MA4',
        'type': 'TPMS',
        'flags': flags,
        'id': f"{sensor_id:06X}",
        'pressure_PSI': round(pressure_psi, 3)
    }


def run_sensor():
        # broadcasts realistic TPMS data continuously.
    
    print(f"Starting Broadcast Every {BROADCAST_INTERVAL} seconds on port {BROADCAST_PORT}")
    print(f"Sensor ID: {SENSOR_ID:06X} ")
    print(f"Base Pressure: {BASE_PRESSURE} PSI")

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    try:
        packet_count = 0
        while True:
            # Simulate pressure variation
            import random
            pressure = BASE_PRESSURE + random.uniform(-0.3, 0.3)
            
            # Alternate flags 
            flags = 5 if packet_count % 5 != 0 else 7
            
            packet = create_binary_packet(
                sensor_id=SENSOR_ID,
                pressure_psi=pressure,
                flags=flags
            )
            
            broadcast_packet(sock, packet, SENSOR_ID, pressure)
            
            decoded = decode_own_packet(packet)
            print(f"JSON: {decoded}")
            print()
            
            packet_count += 1
            time.sleep(BROADCAST_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n\nSensor stopped. Sent {packet_count} packets.")
    finally:
        sock.close()


if __name__ == "__main__":
    print("\nStarting TPMS sensor (2012 Subaru format - no temperature)...")
    print("Press Ctrl+C to stop\n")
    run_sensor()