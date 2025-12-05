from SDR.RFModem import *
from functions import *

# Test encoding
print("Test 1: Encrypt TPMS packet")
print("-" * 50)
sensor_id = 0xA0A6F9
pressure = 37.5
flags = 5


packet = encrypt_tpms_packet(sensor_id, pressure, flags)
print(f"Sensor ID: 0x{sensor_id:06X}")
print(f"Pressure: {pressure} PSI")
print(f"Flags: {flags}")
print(f"Packet length: {len(packet)} bytes")
print(f"Packet hex: {packet.hex()}")
print()

# Transmit Packet
for i in range (0, 15):
    print(f"Transmitting packet {i}")
    print(f"Packet: {packet.hex()}")
    transmit_data(packet)
    print("Sleeping.....")
    print("")
    time.sleep(2)
