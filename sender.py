import numpy as np
import pyaudio
from time import sleep, time
import math
from config import Config
import random

class Sender:
    """
    A class used to represent a Sender that sends a bit-string with the possibility of error and attaches a checksum using CRC that makes it possible to correctly transcribe the received bitstrings


    Attributes
    ----------
    Sample_rate : int
        Sample rate in Hz (Number of measurements in a second)
    Bit_duration : float
        Duration of each bit in seconds
    Preamble_duration : float
        the duration of preamble
    Preamble_frequency : int
        Frequency of preamble tone
    Amplitude : float
        Amplitude of the signal
    Preamble_length : int
        Length of the preamble 
    Bit_flips : list[float]
        List of the 1-indexed positions where the bits are flipped
    Input_bitstring : str
        The data to be sent
    CRC_polynomial : str
        The polynomial CRC to be used (The default one is used by us to ensure that it can correct upto 2 bit errors for input strings of max length 20 bits)
    """

    def __init__(self) -> None:
        """Initialises the member variables of the class"""
        self.config = Config()  
        self.Sample_rate : int = 16000
        self.Bit_duration : float = 0.6
        self.Preamble_duration : float = 0.01
        self.Preamble_frequency : int = 5000
        self.Amplitude : float = 4.0
        self.Preamble_length : int = 6
        self.num_collisions : int = 1

        # The sine wave generating function requires the below values to be multiplied by 4
        self.Bit_duration *= 4
        self.Preamble_duration *= 4
        self.initial_wait_time = 2

    
    def map_freq(self, bit_string : str) -> int:
        """
        This functions maps a 4-bit bitstring to a frequency.
        Frequency ranges from 4300 to 7300.
        """
        index = int(bit_string, 2)
        return self.config.bit_start_freq + index * self.config.bit_freq_gap

    def generate_sine_wave(self, frequency : int, duration : float, amplitude : float, sample_rate : int) -> np.float32:
        """
        This function generates a sine wave according to the arguments
        """
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        sine_wave = amplitude * np.sin(2 * np.pi * frequency * t)
        return sine_wave.astype(np.float32)
    
    def convert_to_binary(self, n : int) -> str:
        """
        Conversion of a decimal number of binary (used to encode length)
        """
        return bin(n)[2:].zfill(4)

    def send_message(self, stream, input_string : str):
        """
        Sends the message, along with the errors 
        """
        # This dictionary contains mapping from frequency to array of sound data to be sent
        tones = {}
        for freq in range(self.config.bit_start_freq, 8000, self.config.bit_freq_gap):
            tones[freq] = self.generate_sine_wave(freq, self.Bit_duration, self.Amplitude, self.Sample_rate)
        stream.write(tones[self.map_freq(input_string[:4])])
        input_string = input_string[4:]
        
        length = len(input_string)
        length_preamble = self.convert_to_binary(length)
        
        length_mod_4 = length % 4
        binary_data = input_string
        if length_mod_4 == 0:
            length_mod_4 = 4
        binary_data += "0" * (4 - length_mod_4)
        # print(f"Length of binary data to be sent is {len(binary_data)} bits.")

        # print("To be sent:", binary_data)
        # print("Starting transmission...")
        stream.write(tones[self.map_freq(length_preamble[:4])])
        for i in range(0, len(binary_data), 4):
            stream.write(tones[self.map_freq(binary_data[i:i+4])])
        # print("Binary data sent.")

    def send_cts(self, stream, cts_message):
        """
        Sends the CTS message
        """
        tones = {}

        # Calculating the "tones" dictionary
        for freq in range(self.config.bit_start_freq, 8000, self.config.bit_freq_gap):
            tones[freq] = self.generate_sine_wave(freq, self.Bit_duration, self.Amplitude, self.Sample_rate)

        stream.write(tones[self.map_freq(cts_message[:4])])


    def send_preamble(self, stream, preamble_frequency):
        """
        Sends the preamble
        """
        # print("Sending preamble...")
        PREAMBLE = self.generate_sine_wave(preamble_frequency, self.Preamble_duration, self.Amplitude, self.Sample_rate)
        for _ in range(self.Preamble_length):
            stream.write(PREAMBLE)
        # print("Preamble sent.")

    def send_rts(self, stream, rts_message):
        """
        Sends the CTS message
        """
        tones = {}

        # Calculating the "tones" dictionary
        for freq in range(self.config.bit_start_freq, 8000, self.config.bit_freq_gap):
            tones[freq] = self.generate_sine_wave(freq, self.Bit_duration, self.Amplitude, self.Sample_rate)

        stream.write(tones[self.map_freq(rts_message[:4])])

    def send_ending_signal(self, stream, freq = None):
        """
        Sends the ending signal
        """
        if freq is None:
            freq = self.config.ending_freq
        tone = self.generate_sine_wave(freq, 2*self.config.Bit_duration, self.config.Amplitude, self.config.Sample_rate)
        stream.write(tone)
