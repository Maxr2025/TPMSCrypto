#!/usr/bin/env python3
# the attacker trying to identify a car ID!! 
# We are simulating this, but the tpms_data_subi.json was collected using rtl-433 on a HackRF One 

import socket
import struct
import json
from datetime import datetime

LISTEN_PORT = 5000
SYNC_WORD = bytes([0x2D, 0xD4])


def find_sync_word(data):
    for i in range(len(data) - 1):
        if data[i:i+2] == SYNC_WORD:
            return i
    return -1


def decode_packet(packet):
    # for this simulation, we know it is Suburu format, but RTL-433 tested all. 
    sync_index = find_sync_word(packet)
    if sync_index == -1:
        return None
    
    offset = sync_index + 2
    
    if len(packet) < offset + 7:
        return None
    
    data = packet[offset:offset+5]
    
    # Decode fields
    sensor_id = struct.unpack('>I', b'\x00' + data[0:3])[0]
    flags = data[3]
    pressure_raw = data[4]
    pressure_psi = pressure_raw / 2.755
    
    return {
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'model': 'Schrader-SMD3MA4',
        'type': 'TPMS',
        'flags': flags,
        'id': f"{sensor_id:06X}",
        'pressure_PSI': round(pressure_psi, 3)
    }


def log_interception(packet, log_file, tracked_vehicles):
    """Log intercepted packet."""
    decoded = decode_packet(packet)
    
    if decoded is None:
        return
    
    sensor_id = decoded['id']
    
    print(f"DECODED JSON: {json.dumps(decoded)}")
    
    # Track vehicle
    if sensor_id not in tracked_vehicles:
        tracked_vehicles[sensor_id] = {
            'first_seen': decoded['time'],
            'sightings': []
        }
    
    tracked_vehicles[sensor_id]['sightings'].append({
        'time': decoded['time'],
        'pressure': decoded['pressure_PSI'],
        'flags': decoded['flags']
    })
    
    # Log to file
    log_entry = decoded.copy()
    log_entry['total_sightings'] = len(tracked_vehicles[sensor_id]['sightings'])
    log_file.write(json.dumps(log_entry) + '\n')
    log_file.flush()
    
    print()


def packet_to_hex(packet, max_bytes=20):
    display_bytes = packet[:max_bytes]
    hex_str = ' '.join(f'{b:02X}' for b in display_bytes)
    if len(packet) > max_bytes:
        hex_str += '...'
    return hex_str


def receive_packet(sock):
    try:
        data, address = sock.recvfrom(1024)
        return data
    except socket.timeout:
        return None
    except Exception:
        return None


def run_eavesdropper():
    
    print("EAVESDROPPER -Listening on port {LISTEN_PORT}")

    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', LISTEN_PORT))
    sock.settimeout(1.0)
    
    log_filename = f"eavesdropper_subaru_test.json"
    tracked_vehicles = {}
    
    try:
        with open(log_filename, 'w') as log_file:
            packet_count = 0
            
            while True:
                packet = receive_packet(sock)
                
                if packet:
                    print(f"RAW Signal: {len(packet)} bytes: {packet_to_hex(packet)}")
                    log_interception(packet, log_file, tracked_vehicles)
                    packet_count += 1
                
    except KeyboardInterrupt:

        print(f"Total packets: {packet_count}")
        print(f"Vehicles tracked: {len(tracked_vehicles)}")
       
        
        print(f"Log saved: {log_filename}")

    finally:
        sock.close()


if __name__ == "__main__":
    print("\nStarting eavesdropper...")

    run_eavesdropper()