#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: TX/RX Split Flowgraph
# GNU Radio version: 3.10.9.2
#

from gnuradio import analog
from gnuradio import blocks
from gnuradio import digital
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio import soapy
from gnuradio import network
import sys
import signal
from argparse import ArgumentParser
import time

##################################################
# Fixed Variables
##################################################
TX_GAIN = 0.9
SYNC_WORD = b'\x2D\xD4'
ACCESS_CODE = '0010110111010100'  # Bit version of SYNC_WORD
SQUELCH = -50
SPS = 2
SAMP_RATE = 386e3
RX_GAIN = 1.4
PREAMBLE = b'\x55' * 100
PPM = 11
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
        self.blocks_throttle2_0 = blocks.throttle(gr.sizeof_char * 1, SAMP_RATE, True)

        # Vector Source (Packet)
        self.blocks_vector_source_x_0 = blocks.vector_source_b(packet, True, 1, [])

        # Connections
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

        # UDP Sink
        self.blocks_udp_sink_0 = network.udp_sink(
            gr.sizeof_char * 1,  # itemsize
            1,  # veclen (vector length)
            '127.0.0.1',  # host
            10000,  # port
            0,  # header_type (0 = no header)
            1472,  # payloadsize
            True  # send_eof
        )

        # Connections
        self.connect((self.soapy_rtlsdr_source_0, 0), (self.rational_resampler_xxx_0_0, 0))
        self.connect((self.rational_resampler_xxx_0_0, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.analog_simple_squelch_cc_0, 0))
        self.connect((self.analog_simple_squelch_cc_0, 0), (self.digital_gfsk_demod_0, 0))
        self.connect((self.digital_gfsk_demod_0, 0), (self.digital_correlate_access_code_xx_ts_0, 0))
        self.connect((self.digital_correlate_access_code_xx_ts_0, 0), (self.blocks_pack_k_bits_bb_0, 0))
        self.connect((self.blocks_pack_k_bits_bb_0, 0), (self.blocks_udp_sink_0, 0))


##################################################
# Functions
##################################################

def transmit_data(data_bytes):
    payload_len = len(data_bytes)
    if payload_len > 65535:
        print(f"Error: Payload length ({payload_len}) exceeds maximum 2-byte value.")
        return

    len_bytes = payload_len.to_bytes(2, 'big')
    dynamic_header = len_bytes * 2

    print(f"Initializing transmitter...")
    print(f"Transmitting {payload_len} payload bytes...")

    tb = Transmitter(data_to_transmit=data_bytes, header=dynamic_header)

    def sig_handler(sig, frame):
        print("Stopping transmitter flowgraph...")
        tb.stop()
        tb.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()
    try:
        time.sleep(0.5)
    except KeyboardInterrupt:
        pass

    print("Transmission time complete. Stopping flowgraph...")
    tb.stop()
    tb.wait()
    print("Transmitter shut down.")


def receive_data(blocking=True):
    """
    Instantiates and runs the Receiver flowgraph.
    If blocking=True, it registers signals and waits indefinitely.
    If blocking=False, it starts the flowgraph and returns the top_block object (NO signals registered).
    """
    print("Initializing receiver...")
    tb = Receiver()

    if blocking:
        def sig_handler(sig, frame):
            print("Stopping receiver flowgraph...")
            tb.stop()
            tb.wait()
            sys.exit(0)

        # Only register signals in blocking mode
        signal.signal(signal.SIGINT, sig_handler)
        signal.signal(signal.SIGTERM, sig_handler)

    tb.start()

    if blocking:
        print("Receiver started. Streaming data to UDP 127.0.0.1:10000")
        print("Press Ctrl+C to stop.")
        tb.wait()
    else:
        # Non-blocking mode: return the block so caller can manage it
        return tb


##################################################
# Main Execution
##################################################
if __name__ == '__main__':
    parser = ArgumentParser(description="Run the GFSK modem in TX or RX mode.")
    parser.add_argument('mode', choices=['tx', 'rx'], help="Mode to run: 'tx' or 'rx'")
    parser.add_argument('-d', '--data', type=str, default='Test', help="Data to transmit")

    args = parser.parse_args()

    if args.mode == 'tx':
        payload_bytes = args.data.encode('utf-8')
        transmit_data(payload_bytes)
    elif args.mode == 'rx':
        receive_data()