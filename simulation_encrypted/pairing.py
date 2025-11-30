#!/usr/bin/env python3

import secrets
import json
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from datetime import datetime

SENSOR_KEY_FILE = "sensor_key.json"
ECU_KEY_FILE = "ecu_key.json"


def simulate_pairing():

    
    print("TPMS SECURE PAIRING SIMULATION")
    print()
    print("This simulates the ONE-TIME key establishment process")
    print("In production, this happens:")
    print("  - At factory (sensors pre-paired with vehicle)")
    print("  - OR during tire replacement (mechanic uses diagnostic tool)")
    print()
    print("Key points:")
    print("  *  Pairing requires physical proximity or wired connection")
    print("  *  Happens ONCE during setup")
    print("  *  Key is stored permanently in both devices")
    print("  *  Key NEVER transmitted over the air after pairing")
    print()
    
    # Generate DH parameters (would be standardized in production)
    print("Key sharing using Diffie-Hellman")
    parameters = dh.generate_parameters(generator=2, key_size=2048)

    
    # ECU generates key pair
    ecu_private_key = parameters.generate_private_key()
    ecu_public_key = ecu_private_key.public_key()
    print("ECU public/private keys generated")
    print()
    
    # Sensor generates key pair
    sensor_private_key = parameters.generate_private_key()
    sensor_public_key = sensor_private_key.public_key()
    print("Sensor public/private keys generated")
    print()
    
    # Exchange public keys (simulating short-range/wired exchange)
    print("Exchanging public keys...")
    print()
    
    # Both sides compute shared secret
    print("Computing shared secret (Diffie-Hellman)...")
    ecu_shared_secret = ecu_private_key.exchange(sensor_public_key)
    sensor_shared_secret = sensor_private_key.exchange(ecu_public_key)
    
    # Verify they match
    assert ecu_shared_secret == sensor_shared_secret
    print("YAY! Both sides computed identical shared secret")
    print()
    
    # Derive TPMS encryption key
    print(" Deriving TPMS encryption key from shared secret...")
    kdf = HKDF(
        algorithm=hashes.SHA256(),
        length=16,  # 128 bits for ASCON-128
        salt=None,
        info=b'TPMS-ASCON-128'
    )
    tpms_key = kdf.derive(ecu_shared_secret)
    print(f"128-bit TPMS key derived: {tpms_key.hex()}")
    print()
    
    # store the keys 
    sensor_data = {
        "sensor_id": "0xA0A6F9",
        "key": tpms_key.hex(),
        "paired_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "key_version": 1
    }
    
    ecu_data = {
        "sensors": {
            "0xA0A6F9": {
                "key": tpms_key.hex(),
                "paired_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tire_position": "front_left"
            }
        },
        "key_version": 1
    }
    
    with open(SENSOR_KEY_FILE, 'w') as f:
        json.dump(sensor_data, f, indent=2)
    print(f"  ✓ Sensor key saved to: {SENSOR_KEY_FILE}")
    
    with open(ECU_KEY_FILE, 'w') as f:
        json.dump(ecu_data, f, indent=2)
    print(f"  ✓ ECU key saved to: {ECU_KEY_FILE}")
    print()
    
    # Step 8: Verification
    print("Step 8: Verifying pairing...")
    print("  ✓ Sensor can now encrypt with key")
    print("  ✓ ECU can now decrypt with key")
    print("  ✓ Keys stored permanently - never need to transmit again")
    print()
    
    print("=" * 70)
    print("✅ PAIRING COMPLETE!")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  - Shared key: {tpms_key.hex()}")
    print(f"  - Sensor file: {SENSOR_KEY_FILE}")
    print(f"  - ECU file: {ECU_KEY_FILE}")
    print()
    print("Important notes:")
    print("  🔒 This pairing happened WITHOUT transmitting the key over RF")
    print("  🔒 Key was derived from DH exchange (only public keys transmitted)")
    print("  🔒 Private keys never left their respective devices")
    print("  🔒 Key is now stored - never needs to be transmitted again")
    print()
    print("Your sensor and ECU can now communicate securely!")
    print("Run sensor_encrypted.py and ecu_encrypted.py to use the paired key.")
    print()


if __name__ == "__main__":
    simulate_pairing()