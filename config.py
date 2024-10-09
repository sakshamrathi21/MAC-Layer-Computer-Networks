"""All the configurations for the sender and receiver are stored in this file"""
import numpy as np


class Config:
    """
    A class used to representthe Receiver that receives a bit-string with the possibility of error and corrects it (for upto 2 bit errors) using the CRC


    Attributes
    ----------
    Sample_rate : int
        Sample rate in Hz (Number of measurements in a second)
    Bit_duration : float
        Duration of each bit in seconds
    Preamble_duration : float
        the sound that the animal makes
    Preamble_frequency : int
        Frequency of preamble tone
    Threshold : int
        Threshold for frequency detection
    Ratio_of_Sender_Receiver : int
        Ratio of bit duration to receiver's check interval
    Preamble_length : int
        Length of the preamble 
    Frequency_filter : int
        Frequency filter to ignore low frequencies
    Ratio_Threshold : int
        Tolerance for bit length ratio
    CRC_polynomial : str
        The polynomial CRC to be used (The default one is used by us to ensure that it can correct upto 2 bit errors for input strings of max length 20 bits)
    Frequency_1 : int
        Frequency for '1' bit in Hz
    Frequency_0 : int
        Frequency for '0' bit in Hz
    Freq_bin_string : dict[int -> str]
        Mapping frequencies to their respective binary strings
    """

    def __init__(self) -> None:
        """Initialises the member variables of the class"""
        self.num_nodes = 3
        self.node_id = "00"
        self.end_wait_time = 5
        self.collision_wait_time = 3
        self.num_collisions = 0
        self.Sample_rate : int = 16000
        self.Amplitude : float = 4.0
        self.Bit_duration : float = 0.7
        self.Preamble_duration : float = 0.05
        self.preamble_wait_time : int = 5
        self.message_preamble_freq : int = 3000
        self.broadcast_preamble_freq = 5000
        self.cts_preamble_freq : int = 3500
        self.rts_preamble_freq : int = 4000
        self.Threshold : int = 100
        self.Preamble_length : int = 6
        self.CRC_polynomial : str = "010111010111"
        self.Frequency_1 = 8200
        self.Frequency_0 = 7900
        self.Ratio_of_Sender_Receiver = 6
        self.Ratio_Threshold = 3
        self.freq_bin_string = {
            self.Frequency_0 : "0",
            self.Frequency_1 : "1"
        }
        self.Frequency_filter = 1000
        self.starting_freq = 6000
        self.rts_cts_length = 4
        self.ending_freq = 7000
        self.bit_start_freq = 4300
        self.bit_freq_gap = 200
        self.ending_signals_map = {
            "01" : 3300,
            "10" : 3400,
            "11" : 3600
        }
        for i in range(0,16):
            self.freq_bin_string[4300+ i*200] = bin(i)[2:].zfill(4)