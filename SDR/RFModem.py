#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: TX/RX Split Flowgraph
# GNU Radio version: 3.10.9.2
#
# This script is modified from a GUI-based flowgraph.
# It's split into two classes: Transmitter and Receiver.
#
# Source flow graph is end2end.grc

from gnuradio import analog
from gnuradio import blocks
from gnuradio import digital
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio import soapy
import sys
import signal
from argparse import ArgumentParser
import time

##################################################
# Fixed Variables (from original GUI)
##################################################
TX_GAIN = 0.9
SYNC_WORD = b'\x2D\xD4'
ACCESS_CODE = '0010110111010100' # Bit version of SYNC_WORD
SQUELCH = -5
SPS = 2
SAMP_RATE = 386e3
RX_GAIN = 1.4
PREAMBLE = b'\x55' * 100
PPM = 11
#HEADER = b'\x01\x90\x01\x90'
HACKRF_SAMP_RATE = 10e6
RTLSDR_SAMP_RATE = 1.8e6
CENTER_FREQ = 464e6

##################################################
# Transmitter Class
##################################################
class Transmitter(gr.top_block):

    def __init__(self, data_to_transmit, header):
        gr.top_block.__init__(self, "Transmitter", catch_exceptions=True)

        # Build the packet using the dynamically generated header
        packet = list(PREAMBLE + SYNC_WORD + header + data_to_transmit)

        ##################################################
        # Blocks
        ##################################################

        # Soapy HackRF Sink
        self.soapy_hackrf_sink_0 = None
        dev = 'driver=hackrf'
        stream_args = ''
        tune_args = ['']
        settings = ['']
        self.soapy_hackrf_sink_0 = soapy.sink(dev, "fc32", 1, '',
                                  stream_args, tune_args, settings)
        self.soapy_hackrf_sink_0.set_sample_rate(0, HACKRF_SAMP_RATE)
        self.soapy_hackrf_sink_0.set_bandwidth(0, 0)
        self.soapy_hackrf_sink_0.set_frequency(0, CENTER_FREQ)
        self.soapy_hackrf_sink_0.set_gain(0, 'AMP', False)
        self.soapy_hackrf_sink_0.set_gain(0, 'VGA', min(max(16, 0.0), 47.0))

        # Resampler for HackRF
        self.rational_resampler_xxx_0 = filter.rational_resampler_ccc(
                interpolation=int(HACKRF_SAMP_RATE),
                decimation=int(SAMP_RATE),
                taps=[],
                fractional_bw=0)

        # Multiply (TX Gain)
        self.blocks_multiply_const_vxx_0_0 = blocks.multiply_const_cc(TX_GAIN)

        # GFSK Modulator
        self.digital_gfsk_mod_0 = digital.gfsk_mod(
            samples_per_symbol=SPS,
            sensitivity=1.0,
            bt=0.35,
            verbose=False,
            log=False,
            do_unpack=True)

        # Throttle
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_char*1, SAMP_RATE, True)

        # Vector Source (Packet)
        # Set repeat to True to keep flowgraph alive and ensure transmission
        self.blocks_vector_source_x_0 = blocks.vector_source_b(packet, True, 1, [])

        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_vector_source_x_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.digital_gfsk_mod_0, 0))
        self.connect((self.digital_gfsk_mod_0, 0), (self.blocks_multiply_const_vxx_0_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0_0, 0), (self.rational_resampler_xxx_0, 0))
        self.connect((self.rational_resampler_xxx_0, 0), (self.soapy_hackrf_sink_0, 0))

##################################################
# Receiver Class
##################################################
class Receiver(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "Receiver", catch_exceptions=True)

        ##################################################
        # Blocks
        ##################################################

        # Soapy RTL-SDR Source
        self.soapy_rtlsdr_source_0 = None
        dev = 'driver=rtlsdr'
        stream_args = 'bufflen=16384'
        tune_args = ['']
        settings = ['']
        self.soapy_rtlsdr_source_0 = soapy.source(dev, "fc32", 1, '',
                                  stream_args, tune_args, settings)
        self.soapy_rtlsdr_source_0.set_sample_rate(0, RTLSDR_SAMP_RATE)
        self.soapy_rtlsdr_source_0.set_frequency(0, CENTER_FREQ)
        self.soapy_rtlsdr_source_0.set_frequency_correction(0, PPM)
        self.soapy_rtlsdr_source_0.set_gain_mode(0, bool(False))
        self.soapy_rtlsdr_source_0.set_gain(0, 'TUNER', 20)

        # Resampler for RTL-SDR
        self.rational_resampler_xxx_0_0 = filter.rational_resampler_ccc(
                interpolation=int(SAMP_RATE),
                decimation=int(RTLSDR_SAMP_RATE),
                taps=[],
                fractional_bw=0)

        # Multiply (RX Gain)
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_cc(RX_GAIN)

        # Squelch
        self.analog_simple_squelch_cc_0 = analog.simple_squelch_cc(SQUELCH, 1)

        # GFSK Demodulator
        self.digital_gfsk_demod_0 = digital.gfsk_demod(
            samples_per_symbol=SPS,
            sensitivity=1.0,
            gain_mu=0.175,
            mu=0.5,
            omega_relative_limit=0.005,
            freq_error=0.0,
            verbose=False,
            log=False)

        # Correlate Access Code
        self.digital_correlate_access_code_xx_ts_0 = digital.correlate_access_code_bb_ts(ACCESS_CODE,
          0, '')

        # Pack K Bits
        self.blocks_pack_k_bits_bb_0 = blocks.pack_k_bits_bb(8)

        # File Descriptor Sink (prints to stdout)
        # 1 = stdout
        self.blocks_stdout_sink = blocks.file_descriptor_sink(gr.sizeof_char*1, 1)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.soapy_rtlsdr_source_0, 0), (self.rational_resampler_xxx_0_0, 0))
        self.connect((self.rational_resampler_xxx_0_0, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.analog_simple_squelch_cc_0, 0))
        self.connect((self.analog_simple_squelch_cc_0, 0), (self.digital_gfsk_demod_0, 0))
        self.connect((self.digital_gfsk_demod_0, 0), (self.digital_correlate_access_code_xx_ts_0, 0))
        self.connect((self.digital_correlate_access_code_xx_ts_0, 0), (self.blocks_pack_k_bits_bb_0, 0))
        self.connect((self.blocks_pack_k_bits_bb_0, 0), (self.blocks_stdout_sink, 0))


##################################################
# Functions
##################################################

def transmit_data(data_bytes):
    """
    Instantiates and runs the Transmitter flowgraph.
    Takes a byte vector (e.g., b'my data') as input.
    """
    payload_len = len(data_bytes)

    # Check if length exceeds 2 bytes (65535)
    if payload_len > 65535:
        print(f"Error: Payload length ({payload_len}) exceeds maximum 2-byte value (65535).")
        return

    # Convert length to a 2-byte (16-bit) big-endian value
    len_bytes = payload_len.to_bytes(2, 'big')

    # Create the header by repeating the 2-byte length
    dynamic_header = len_bytes * 2

    print(f"Initializing transmitter...")
    print(f"Transmitting {payload_len} payload bytes with header {dynamic_header.hex()} for 0.5 seconds.")

    # Pass the new dynamic_header to the Transmitter
    tb = Transmitter(data_to_transmit=data_bytes, header=dynamic_header)

    def sig_handler(sig, frame):
        print("Stopping transmitter flowgraph...")
        tb.stop()
        tb.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()

    # Keep the flowgraph alive for 0.5 seconds to ensure transmission
    try:
        time.sleep(0.5)
    except KeyboardInterrupt:
        pass # Allow Ctrl+C to interrupt the sleep
    
    print("Transmission time complete. Stopping flowgraph...")
    tb.stop()
    tb.wait()
    print("Transmitter shut down.")

def receive_data():
    """
    Instantiates and runs the Receiver flowgraph.
    Prints received data to the terminal.
    """
    print("Initializing receiver...")
    tb = Receiver()

    def sig_handler(sig, frame):
        print("Stopping receiver flowgraph...")
        tb.stop()
        tb.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    
    tb.start()
    print("Receiver started. Printing received data to terminal.")
    print("Press Ctrl+C to stop.")
    
    # Wait for sig_handler to stop the flowgraph
    tb.wait()


##################################################
# Main Execution
##################################################
if __name__ == '__main__':
    parser = ArgumentParser(description="Run the GFSK modem in TX or RX mode.")
    parser.add_argument(
        'mode', 
        choices=['tx', 'rx'], 
        help="Mode to run: 'tx' (transmit) or 'rx' (receive)"
    )
    parser.add_argument(
        '-d', '--data', 
        type=str, 
        default='This is a test payload.', 
        help="Data string to transmit (used in 'tx' mode)"
    )

    args = parser.parse_args()

    if args.mode == 'tx':
        # Convert the input string to bytes
        payload_bytes = args.data.encode('utf-8')
        transmit_data(payload_bytes)
    elif args.mode == 'rx':
        receive_data()
