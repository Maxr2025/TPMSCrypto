#!/usr/bin/env python3

import sys
import secrets
import json
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from datetime import datetime

ECU_KEY_FILE = "keys/ecu_key.json"


def simulate_pairing(sensor_id_hex, tire_position="unknown"):
    try:
        sensor_id = int(sensor_id_hex, 16) if isinstance(sensor_id_hex, str) else sensor_id_hex
        sensor_id_str = f"0x{sensor_id:06X}"
    except ValueError:
        print(f"Error: Invalid sensor ID '{sensor_id_hex}'. Must be hex format (e.g., A0A6F9)")
        return False
    
    # Create individual sensor key file name
    sensor_key_file = f"keys/sensor_{sensor_id:06X}_key.json"
    
    print("TPMS SECURE PAIRING SIMULATION")
    print()
    print(f"Pairing sensor: {sensor_id_str}")
    print(f"Tire position: {tire_position}")
    print()
    print("This simulates the ONE-TIME key establishment process")
    print("In production, this happens:")
    print("  - At factory (sensors pre-paired with vehicle)")
    print("  - OR during tire replacement (mechanic uses diagnostic tool)")
    print()
    print("Key points:")
    print("  * Pairing requires physical proximity or wired connection")
    print("  * Happens ONCE during setup")
    print("  * Key is stored permanently in both devices")
    print("  * Key NEVER transmitted over the air after pairing")
    print()
    
    print("Key sharing using Diffie-Hellman")
    parameters = dh.generate_parameters(generator=2, key_size=2048)
    
    ecu_private_key = parameters.generate_private_key()
    ecu_public_key = ecu_private_key.public_key()
    print("ECU public/private keys generated")
    
    sensor_private_key = parameters.generate_private_key()
    sensor_public_key = sensor_private_key.public_key()
    print("Sensor public/private keys generated")
    print()
    
    print("Exchanging public keys...")
    ecu_shared_secret = ecu_private_key.exchange(sensor_public_key)
    sensor_shared_secret = sensor_private_key.exchange(ecu_public_key)
    
    assert ecu_shared_secret == sensor_shared_secret
    print("Both sides computed identical shared secret")
    print()
    
    print("Deriving TPMS encryption key from shared secret...")
    kdf = HKDF(
        algorithm=hashes.SHA256(),
        length=16,
        salt=None,
        info=b'TPMS-ASCON-128'
    )
    tpms_key = kdf.derive(ecu_shared_secret)
    print(f"128-bit TPMS key derived: {tpms_key.hex()}")
    print()
    
    # Create individual sensor key file
    sensor_data = {
        "sensor_id": sensor_id_str,
        "key": tpms_key.hex(),
        "paired_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tire_position": tire_position,
        "key_version": 1
    }
    
    # Save individual sensor key file
    with open(sensor_key_file, 'w') as f:
        json.dump(sensor_data, f, indent=2)
    print(f"Sensor key saved to: {sensor_key_file}")
    
    # Load existing ECU data or create new
    try:
        with open(ECU_KEY_FILE, 'r') as f:
            ecu_data = json.load(f)
    except FileNotFoundError:
        ecu_data = {"sensors": {}, "key_version": 1}
    
    # Add or update this sensor in ECU database
    ecu_data["sensors"][sensor_id_str] = {
        "key": tpms_key.hex(),
        "paired_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tire_position": tire_position
    }
    
    with open(ECU_KEY_FILE, 'w') as f:
        json.dump(ecu_data, f, indent=2)
    print(f"ECU key saved to: {ECU_KEY_FILE}")
    print()
    
    print()
    print("Summary:")
    print(f"  - Sensor ID: {sensor_id_str}")
    print(f"  - Shared key: {tpms_key.hex()}")
    print(f"  - Sensor file: {sensor_key_file}")
    print(f"  - ECU file: {ECU_KEY_FILE}")
    print()

    
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 pairing.py <sensor_id> [tire_position]")
        print()
        print("Example: python3 pairing.py A0A6F9 front_left")

        return
    
    sensor_id = sys.argv[1].replace('0x', '').replace('0X', '')
    tire_position = sys.argv[2] if len(sys.argv) > 2 else "unknown"
    
    simulate_pairing(sensor_id, tire_position)


if __name__ == "__main__":
    main()