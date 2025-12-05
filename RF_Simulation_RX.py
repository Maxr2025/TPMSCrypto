import socket
import time
import sys
import os
from SDR import RFModem
import functions

# Configuration
UDP_IP = "127.0.0.1"
UDP_PORT = 10000

def main():
    print("Starting TPMS Receiver Simulation...")
    print("-" * 50)

    print("Initializing Radio Flowgraph...")
    tb = RFModem.receive_data(blocking=False)
    time.sleep(2)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        sock.bind((UDP_IP, UDP_PORT))
    except OSError as e:
        print(f"Error binding to port {UDP_PORT}: {e}")
        tb.stop()
        tb.wait()
        return

    print(f"Listening on UDP {UDP_IP}:{UDP_PORT}...")
    print("Waiting for packets (Press Ctrl+C to stop)...")

    last_packet_signature = None
    last_packet_time = 0
    DUPLICATE_WINDOW = 2.0  # Seconds to ignore repeats

    try:
        while True:
            data, addr = sock.recvfrom(4096)

            if data:
                PAYLOAD_LEN = 37
                found_in_buffer = False

                for i in range(len(data) - PAYLOAD_LEN + 1):
                    candidate_payload = data[i: i + PAYLOAD_LEN]
                    reconstructed_packet = functions.SYNC_WORD + candidate_payload

                    try:
                        result = functions.decrypt_tpms_packet(reconstructed_packet)

                        if result:
                            # Create a unique signature for this packet contents
                            current_signature = (result['sensor_id'], result['pressure_psi'], result['flags'])
                            current_time = time.time()

                            # Check if this is a duplicate of the last packet
                            is_duplicate = (current_signature == last_packet_signature) and \
                                           (current_time - last_packet_time < DUPLICATE_WINDOW)

                            if not is_duplicate:
                                print(f"\n[+] DECRYPTION SUCCESS (Offset {i}):")
                                print(f"    Sensor ID: {result['sensor_id']}")
                                print(f"    Pressure : {result['pressure_psi']:.3f} PSI")

                                # Update last seen packet
                                last_packet_signature = current_signature
                                last_packet_time = current_time
                            else:
                                pass

                            found_in_buffer = True
                            break  # Stop processing this buffer

                    except Exception:
                        pass


    except KeyboardInterrupt:
        print("\nStopping simulation...")
    finally:
        print("Shutting down receiver...")
        sock.close()
        tb.stop()
        tb.wait()


if __name__ == "__main__":
    main()