#!/usr/bin/env python3

import sys
from PyQt5 import Qt
from TX_GFSK_FUN import TX_GFSK
import time
import struct

def transmit_data(data_bytes):
    """
    Instantiates, runs, and waits for the GNU Radio flowgraph
    to transmit the provided data.

    Args:
        data_bytes (bytes): The raw bytes to transmit.
    """
    print(f"Initializing flowgraph to transmit {len(data_bytes)} bytes...")
    
    # Instantiate the flowgraph
    tb = TX_GFSK(data_to_tx=data_bytes)
    
    # Start the flowgraph
    tb.start()
    
    # Wait for the flowgraph to finish
    tb.wait()
    
    print("Transmission complete.")
    
    # Clean up the flowgraph and its Qt windows
    tb.stop()
    tb = None 


if __name__ == '__main__':
    qapp = Qt.QApplication.instance()
    if qapp is None:
        qapp = Qt.QApplication(sys.argv)
    # ----------------
    
    # Create 100 byte preamble for clock sync
    preamble = b'\x55' * 1000
    
    # Create sync word
    sync_word = b'\x2D\xD4'
    
    # Create some arbitrary data to send
    payload = b'\xDE\xAD\xBE\xEF' * 100  # 400 bytes
    
    # Create header
    payload_len = len(payload)
    len_bytes = struct.pack('!H', payload_len)
    header = len_bytes + len_bytes
    
    data_to_send = preamble + sync_word + header + payload
    
    print(f"Total packet length: {len(data_to_send)} bytes")
    print(f"Payload length: {payload_len} bytes")
    print(f"Header: {header.hex()}")
    
    # Transmit the data
    transmit_data(data_to_send)
