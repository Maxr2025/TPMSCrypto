#!/usr/bin/env python3

import time
import statistics
import csv
import struct
import secrets
from ascon import encrypt as ascon_encrypt

NUM_ITERATIONS = 500000
SENSOR_ID = 0xA0A6F9
PRESSURE_PSI = 37.5
FLAGS = 5
SHARED_KEY = bytes.fromhex('000102030405060708090a0b0c0d0e0f')

MCU_VOLTAGE = 3.0
MCU_ACTIVE_CURRENT = 0.005
RF_TX_CURRENT = 0.015
RF_BITRATE = 10000
TRANSMISSIONS_PER_DAY = 60
CR2032_CAPACITY_MAH = 220
CR2032_VOLTAGE = 3.0


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
    return struct.pack('>H', crc)


def create_binary_packet(sensor_id, pressure_psi, flags=5):
    data = bytearray()
    data.extend(struct.pack('>I', sensor_id)[1:])
    data.append(flags & 0xFF)
    pressure_raw = int(pressure_psi * 2.755)
    data.append(pressure_raw & 0xFF)
    crc = calculate_crc(data)
    
    preamble = bytes([0x55] * 8)
    sync_word = bytes([0x2D, 0xD4])
    packet = preamble + sync_word + data + crc
    
    return bytes(packet)


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
    
    ciphertext = ascon_encrypt(
        key=shared_key,
        nonce=nonce,
        associateddata=b'',
        plaintext=plaintext
    )
    
    preamble = bytes([0x55] * 8)
    sync_word = bytes([0x2D, 0xD4])
    packet = preamble + sync_word + nonce + ciphertext
    
    return bytes(packet), nonce

def benchmark_baseline():
    print(f"Benchmarking baseline ({NUM_ITERATIONS} iterations)...")
    creation_times = []
    
    for _ in range(NUM_ITERATIONS):
        start = time.perf_counter()
        packet = create_binary_packet(SENSOR_ID, PRESSURE_PSI, FLAGS)
        end = time.perf_counter()
        creation_times.append((end - start) * 1e6)
    
    return {
        'packet_size': 17,
        'creation_mean': statistics.mean(creation_times),
        'creation_stdev': statistics.stdev(creation_times),
    }


def benchmark_encrypted():
    print(f"Benchmarking ASCON ({NUM_ITERATIONS} iterations)...")
    creation_times = []
    
    for _ in range(NUM_ITERATIONS):
        start = time.perf_counter()
        packet, nonce = create_encrypted_packet(SENSOR_ID, PRESSURE_PSI, FLAGS, SHARED_KEY)
        end = time.perf_counter()
        creation_times.append((end - start) * 1e6)
    
    return {
        'packet_size': 47,
        'creation_mean': statistics.mean(creation_times),
        'creation_stdev': statistics.stdev(creation_times),
    }


def calculate_power(packet_size, comp_time_us):
    comp_time_s = comp_time_us / 1e6
    comp_energy_uj = MCU_VOLTAGE * MCU_ACTIVE_CURRENT * comp_time_s * 1e6
    
    tx_time_s = (packet_size * 8) / RF_BITRATE
    tx_energy_uj = MCU_VOLTAGE * RF_TX_CURRENT * tx_time_s * 1e6
    
    total_energy_uj = comp_energy_uj + tx_energy_uj
    daily_energy_j = (total_energy_uj * TRANSMISSIONS_PER_DAY) / 1e6
    
    return {
        'comp_time_ms': comp_time_us / 1000,
        'comp_energy_uj': comp_energy_uj,
        'tx_time_ms': tx_time_s * 1000,
        'tx_energy_uj': tx_energy_uj,
        'total_energy_uj': total_energy_uj,
        'daily_energy_j': daily_energy_j,
    }


def calculate_battery_life(daily_energy_j):
    battery_j = (CR2032_CAPACITY_MAH / 1000) * CR2032_VOLTAGE * 3600
    years = (battery_j / daily_energy_j) / 365.25
    return min(years, 10)


def print_results(baseline, encrypted):
    b_power = calculate_power(baseline['packet_size'], baseline['creation_mean'])
    e_power = calculate_power(encrypted['packet_size'], encrypted['creation_mean'])
    
    print("\nBaseline:")
    print(f"  Creation time: {baseline['creation_mean']:.2f} μs")
    print(f"  Energy per packet: {b_power['total_energy_uj']:.2f} μJ")
    print(f"  Battery life: {calculate_battery_life(b_power['daily_energy_j']):.1f} years")
    
    print("\nASCON:")
    print(f"  Creation time: {encrypted['creation_mean']:.2f} μs")
    print(f"  Energy per packet: {e_power['total_energy_uj']:.2f} μJ")
    print(f"  Battery life: {calculate_battery_life(e_power['daily_energy_j']):.1f} years")
    
    print(f"\nOverhead: +{encrypted['creation_mean'] - baseline['creation_mean']:.2f} μs, +{e_power['total_energy_uj'] - b_power['total_energy_uj']:.2f} μJ")


def export_timing_table(baseline, encrypted):
    b_power = calculate_power(baseline['packet_size'], baseline['creation_mean'])
    e_power = calculate_power(encrypted['packet_size'], encrypted['creation_mean'])
    
    # Timing table
    with open('timing_results.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Metric', 'Baseline', 'ASCON', 'Factor'])
        
        writer.writerow([
            'Packet Size (bytes)',
            f"{baseline['packet_size']}",
            f"{encrypted['packet_size']}",
            f"{encrypted['packet_size'] / baseline['packet_size']:.2f}x"
        ])
        
        writer.writerow([
            'Computation Time (ms)',
            f"{baseline['creation_mean'] / 1000:.4f}",
            f"{encrypted['creation_mean'] / 1000:.4f}",
            f"{encrypted['creation_mean'] / baseline['creation_mean']:.2f}x"
        ])
        
        writer.writerow([
            'Transmission Time (ms)',
            f"{b_power['tx_time_ms']:.2f}",
            f"{e_power['tx_time_ms']:.2f}",
            f"{e_power['tx_time_ms'] / b_power['tx_time_ms']:.2f}x"
        ])
    
    # Power table
    with open('power_results.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Metric', 'Baseline', 'ASCON', 'Factor'])
        
        writer.writerow([
            'Computation Energy (μJ)',
            f"{b_power['comp_energy_uj']:.2f}",
            f"{e_power['comp_energy_uj']:.2f}",
            f"{e_power['comp_energy_uj'] / b_power['comp_energy_uj']:.2f}x"
        ])
        
        writer.writerow([
            'Transmission Energy (μJ)',
            f"{b_power['tx_energy_uj']:.2f}",
            f"{e_power['tx_energy_uj']:.2f}",
            f"{e_power['tx_energy_uj'] / b_power['tx_energy_uj']:.2f}x"
        ])
        
        writer.writerow([
            'Total Energy per Packet (μJ)',
            f"{b_power['total_energy_uj']:.2f}",
            f"{e_power['total_energy_uj']:.2f}",
            f"{e_power['total_energy_uj'] / b_power['total_energy_uj']:.2f}x"
        ])
        
        writer.writerow([
            'Daily Energy Consumption (J)',
            f"{b_power['daily_energy_j']:.3f}",
            f"{e_power['daily_energy_j']:.3f}",
            f"{e_power['daily_energy_j'] / b_power['daily_energy_j']:.2f}x"
        ])
        
        writer.writerow([
            'Battery Life (years)',
            f"{calculate_battery_life(b_power['daily_energy_j']):.1f}",
            f"{calculate_battery_life(e_power['daily_energy_j']):.1f}",
            f"{calculate_battery_life(e_power['daily_energy_j']) / calculate_battery_life(b_power['daily_energy_j']):.2f}x"
        ])


def export_battery_projection(baseline, encrypted):
    b_power = calculate_power(baseline['packet_size'], baseline['creation_mean'])
    e_power = calculate_power(encrypted['packet_size'], encrypted['creation_mean'])
    
    battery_j = (CR2032_CAPACITY_MAH / 1000) * CR2032_VOLTAGE * 3600
    max_months = 120
    
    with open('battery_life_projection.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['TimeMonths', 'BaselinePercent', 'ASCONPercent'])
        
        for month in range(max_months + 1):
            years = month / 12
            
            energy_b = b_power['daily_energy_j'] * (years * 365.25)
            percent_b = max(0, (1 - energy_b / battery_j) * 100)
            
            energy_e = e_power['daily_energy_j'] * (years * 365.25)
            percent_e = max(0, (1 - energy_e / battery_j) * 100)
            
            writer.writerow([month, f"{percent_b:.2f}", f"{percent_e:.2f}"])


def main():
    print("TPMS Performance Benchmark\n")
    
    baseline = benchmark_baseline()
    encrypted = benchmark_encrypted()
    
    print_results(baseline, encrypted)
    
    print("\nExporting results...")
    export_timing_table(baseline, encrypted)
    export_battery_projection(baseline, encrypted)
    print("Done.")


if __name__ == "__main__":
    main()