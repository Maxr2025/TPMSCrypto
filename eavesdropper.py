#!/usr/bin/env python3

import socket
import struct
from datetime import datetime

LISTEN_PORT = 5000
SYNC_WORD = bytes([0x2D, 0xD4])


def find_sync_word(data):
    for i in range(len(data) - 1):
        if data[i:i+2] == SYNC_WORD:
            return i
    return -1


def attempt_decode_baseline(packet, sync_index):
    offset = sync_index + 2
    
    if len(packet) < offset + 7:
        return None
    
    data = packet[offset:offset+5]
    sensor_id = struct.unpack('>I', b'\x00' + data[0:3])[0]
    flags = data[3]
    pressure_raw = data[4]
    pressure_psi = pressure_raw / 2.755
    
    return {
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'type': 'BASELINE',
        'id': f"{sensor_id:06X}",
        'pressure_PSI': round(pressure_psi, 3),
        'flags': flags,
        'tracking_possible': True
    }


def attempt_decode_encrypted(packet, sync_index):
    offset = sync_index + 2
    
    if len(packet) < offset + 37:
        return None
    
    nonce = packet[offset:offset+16]
    
    return {
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'type': 'ENCRYPTED',
        'nonce': nonce.hex()[:32],
        'tracking_possible': False
    }


def analyze_packet(packet, tracked_vehicles):
    sync_index = find_sync_word(packet)
    if sync_index == -1:
        return None
    
    offset = sync_index + 2
    remaining = len(packet) - offset
    
    if remaining >= 37:
        result = attempt_decode_encrypted(packet, sync_index)
    elif remaining >= 7:
        result = attempt_decode_baseline(packet, sync_index)
    else:
        return None
    
    if result is None:
        return None
    
    print(f"Intercepted {result['type']} packet at {result['time']}")
    
    if result['type'] == 'BASELINE':
        sensor_id = result['id']
        
        if sensor_id not in tracked_vehicles:
            tracked_vehicles[sensor_id] = []
            print(f"  New vehicle: {sensor_id}")
        
        tracked_vehicles[sensor_id].append(result['time'])
        print(f"  Sensor ID: {sensor_id} (static, can track)")
        print(f"  Pressure: {result['pressure_PSI']:.3f} PSI (plaintext)")
        print(f"  Total sightings: {len(tracked_vehicles[sensor_id])}")
        
    else:
        print(f"  Nonce: {result['nonce']}... (random, cannot track)")
        print(f"  Data: encrypted (cannot read)")
    
    print()
    return result


def run_eavesdropper():
    print(f"Eavesdropper listening on port {LISTEN_PORT}\n")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', LISTEN_PORT))
    sock.settimeout(1.0)
    
    tracked_vehicles = {}
    
    try:
        packet_count = 0
        baseline_count = 0
        encrypted_count = 0
        
        while True:
            try:
                data, address = sock.recvfrom(1024)
            except socket.timeout:
                continue
            
            result = analyze_packet(data, tracked_vehicles)
            
            if result:
                packet_count += 1
                if result['type'] == 'BASELINE':
                    baseline_count += 1
                else:
                    encrypted_count += 1
            
    except KeyboardInterrupt:
        print(f"\nEavesdropper stopped")
        print(f"Total packets: {packet_count}")
        print(f"Baseline: {baseline_count} | Encrypted: {encrypted_count}")
        print(f"Vehicles tracked: {len(tracked_vehicles)}")
    finally:
        sock.close()


if __name__ == "__main__":
    run_eavesdropper()