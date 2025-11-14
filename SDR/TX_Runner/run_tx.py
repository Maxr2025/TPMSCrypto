#!/usr/bin/env python3

import sys
from PyQt5 import Qt
from TX_GFSK_FUN import TX_GFSK
import time

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
    
    # Create some arbitrary data to send
    my_packet = b'\xDE\xAD\xBE\xEF' * 100  # 400 bytes
    
    # Transmit the data
    transmit_data(my_packet)
