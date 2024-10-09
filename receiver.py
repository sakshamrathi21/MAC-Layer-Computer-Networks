import numpy as np
import pyaudio
from scipy.fft import fft
import time
from config import Config
import signal

timeout_flag = False

def timeout_handler(signum, frame):
    global timeout_flag
    timeout_flag = True
    # print("Timeout!")

def call_with_timeout(func, args=(), kwargs=None, timeout_duration=5):
    global timeout_flag
    if kwargs is None:
        kwargs = {}
    timeout_flag = False
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_duration)
    result = func(*args, **kwargs)
    signal.alarm(0)
    return result, timeout_flag

class Receiver:
    """
    A class used to represent the Receiver that receives a bit-string with the possibility of error and corrects it (for upto 2 bit errors) using the CRC


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
        self.config = Config()
        self.Sample_rate : int = 16000
        self.Bit_duration : int = 0.1
        self.Preamble_duration : float = 0.01
        self.Preamble_frequency : int = 5000
        self.Threshold : int = 100
        self.Preamble_length : int = 6
        self.Frequency_1 = 8200
        self.Frequency_0 = 7900
        self.Ratio_of_Sender_Receiver = 6
        self.Ratio_Threshold = 3
        self.freq_bin_string = {
            self.Frequency_0 : "0",
            self.Frequency_1 : "1"
        }
        self.Frequency_filter = 1000
        for i in range(0,16):
            self.freq_bin_string[self.config.bit_start_freq+ i*self.config.bit_freq_gap] = bin(i)[2:].zfill(4)

    def map_freq(self, bit_string : str) -> int:
        """
        This functions maps a 4-bit bitstring to a frequency.
        Frequency ranges from 4300 to 7300.
        """
        index = int(bit_string, 2)
        return 4300 + index * 200
    
    def return_freq(self, receieve_stream) -> int:
        data = receieve_stream.read(int(self.Sample_rate * self.Preamble_duration))
        frame = np.frombuffer(data, dtype=np.int16)
        frame = frame / np.max(np.abs(frame))
        
        spectrum = np.abs(fft(frame))
        freqs = np.fft.fftfreq(len(spectrum), 1 / self.Sample_rate)
        
        peak_freq = freqs[np.argmax(spectrum)]
        return peak_freq
    
    def detect_preamble(self, Preamble_frequency, Sample_rate, Threshold, preamble_stream, start_time):
        """
        Detect the preamble signal in the audio stream.

        Args:
        Preamble_frequency : int
            Frequency of the preamble signal in Hz
        Sample_rate : int 
            Sample rate in Hz
        Threshold : int 
            Threshold for frequency detection
        """
        preamble_found = False
        while time.time() - start_time < self.config.preamble_wait_time:
            # Read preamble as input
            data = preamble_stream.read(int(Sample_rate * self.Preamble_duration))
            frame = np.frombuffer(data, dtype=np.int16)
            frame = frame / np.max(np.abs(frame))
            
            spectrum = np.abs(fft(frame))
            freqs = np.fft.fftfreq(len(spectrum), 1 / Sample_rate)
            
            # Detect the peak frequency
            peak_freq = freqs[np.argmax(spectrum)]

            if abs(peak_freq - Preamble_frequency) <  Threshold:
                preamble_found = True
                break
        return preamble_found

    def Receive_bitstring(self)->None:
        """
        Start listening for the audio and also do error correction to print the correct output
        """
        p = pyaudio.PyAudio()

        preamble_stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=self.Sample_rate,
                        input=True,
                        frames_per_buffer=int(self.Sample_rate * self.Preamble_duration))

        
        # Detect preamble before starting the main signal detection
        # print("Listening for preamble...")
        for _ in range(self.Preamble_length):
            self.detect_preamble(self.Preamble_frequency, self.Sample_rate, self.Threshold)
        # print("Preamble detected")
        preamble_stream.stop_stream()
        preamble_stream.close()

        # Start main signal detection after preamble
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=self.Sample_rate,
                        input=True,
                        frames_per_buffer=int(self.Sample_rate * self.Bit_duration),
                        )
        # print("Listening for audio signal...")

        binary_data = ""
        previous_bit = "?"
        current_bit = "0"
        current_bit_length = 0
        data_length = -1

        # Main loop to recieve the main signal
        while True:
            data = stream.read(int(self.Sample_rate * self.Bit_duration))
            frame = np.frombuffer(data, dtype=np.int16)
            frame = frame / np.max(np.abs(frame))
            spectrum = np.abs(fft(frame))
            freqs = np.fft.fftfreq(len(spectrum), 1 / self.Sample_rate)

            # Filter the spectrum and frequencies to consider only those > Frequency_filter
            valid_indices = freqs > self.Frequency_filter
            filtered_spectrum = spectrum[valid_indices]
            filtered_freqs = freqs[valid_indices]

            # Find the peak frequency among the filtered frequencies
            peak_freq = filtered_freqs[np.argmax(filtered_spectrum)]
            freq_found = peak_freq

            # Determine the current bit based on detected frequency
            found = False
            for freq in self.freq_bin_string:
                if abs(freq_found - freq) <= self.Threshold:
                    current_bit = self.freq_bin_string[freq]
                    found = True
                    break
            if not found:
                current_bit = "?"

            # Process the detected bit
            if current_bit == previous_bit:
                current_bit_length += 1
                if current_bit_length >= self.Ratio_of_Sender_Receiver:
                    current_bit_length = 0
                    binary_data += previous_bit
            else:
                if abs(current_bit_length - self.Ratio_of_Sender_Receiver) <= self.Ratio_Threshold:
                    binary_data += previous_bit
                current_bit_length = 1
                previous_bit = current_bit

            # Determine the data length from the first 8 bits
            if data_length == -1 and len(binary_data) > 8:
                data_length = int(binary_data[:8], 2)
                binary_data = binary_data[8:]

            # Terminate the loop when full message is recieved
            if data_length != -1 and len(binary_data) >= data_length:
                break
        
        # Print the received bitsting, along with zero padding
        # print("The received bitstring along with zero padding: ", binary_data) 
        # Extract the relevant bits of detected data
        binary_data = binary_data[:data_length]
        # print("Received data from sender after removing zero padding:", binary_data)

        stream.stop_stream()
        stream.close()
        p.terminate()

    def receive_preamble(self, num_preamble_bits, stream, preamble_freq):
        """
        Receive the preamble signal from the sender.

        Args:
        num_preamble_bits : int
            Number of preamble bits to receive
        stream : pyaudio stream
            Stream to receive the audio signal
        """
        for _ in range(num_preamble_bits):
            preamble_found = self.detect_preamble(preamble_freq, self.Sample_rate, self.Threshold, stream, time.time())
            if not preamble_found:
                return True
            # print(_)
        return False

    def receive_rts(self, node_id, stream):
        """
        Start listening for the audio and also do error correction to print the correct output
        """
        # print("Listening for audio signal...")

        binary_data = ""
        previous_bit = "?"
        current_bit = "0"
        current_bit_length = 0
        data_length = -1

        # Main loop to recieve the main signal
        while True:
            data = stream.read(int(self.Sample_rate * self.Bit_duration))
            frame = np.frombuffer(data, dtype=np.int16)
            frame = frame / np.max(np.abs(frame))
            spectrum = np.abs(fft(frame))
            freqs = np.fft.fftfreq(len(spectrum), 1 / self.Sample_rate)

            # Filter the spectrum and frequencies to consider only those > Frequency_filter
            valid_indices = freqs > self.Frequency_filter
            filtered_spectrum = spectrum[valid_indices]
            filtered_freqs = freqs[valid_indices]

            # Find the peak frequency among the filtered frequencies
            peak_freq = filtered_freqs[np.argmax(filtered_spectrum)]
            freq_found = peak_freq

            # Determine the current bit based on detected frequency
            found = False
            for freq in self.freq_bin_string:
                if abs(freq_found - freq) <= self.Threshold:
                    current_bit = self.freq_bin_string[freq]
                    found = True
                    break
            if not found:
                current_bit = "?"

            # Process the detected bit
            if current_bit == previous_bit:
                current_bit_length += 1
                if current_bit_length >= self.Ratio_of_Sender_Receiver:
                    current_bit_length = 0
                    binary_data += previous_bit
            else:
                if abs(current_bit_length - self.Ratio_of_Sender_Receiver) <= self.Ratio_Threshold:
                    binary_data += previous_bit
                current_bit_length = 1
                previous_bit = current_bit
            if len(binary_data) >= self.config.rts_cts_length:
                break
            # print(binary_data)
        
        # Print the received bitsting, along with zero padding
        # print("The received RTS:", binary_data) 
        # Extract the relevant bits of detected data
        sender = binary_data[:2]
        receiver = binary_data[2:4]
        if receiver == node_id or receiver == "00":
            return True, sender
        return False, ""

    def receive_message(self, stream)->None:
        binary_data = ""
        previous_bit = "?"
        current_bit = "0"
        current_bit_length = 0
        data_length = -1

        # Main loop to recieve the main signal
        while True:
            data = stream.read(int(self.Sample_rate * self.Bit_duration))
            frame = np.frombuffer(data, dtype=np.int16)
            frame = frame / np.max(np.abs(frame))
            spectrum = np.abs(fft(frame))
            freqs = np.fft.fftfreq(len(spectrum), 1 / self.Sample_rate)

            # Filter the spectrum and frequencies to consider only those > Frequency_filter
            valid_indices = freqs > self.Frequency_filter
            filtered_spectrum = spectrum[valid_indices]
            filtered_freqs = freqs[valid_indices]

            # Find the peak frequency among the filtered frequencies
            peak_freq = filtered_freqs[np.argmax(filtered_spectrum)]
            freq_found = peak_freq

            # Determine the current bit based on detected frequency
            found = False
            for freq in self.freq_bin_string:
                if abs(freq_found - freq) <= self.Threshold:
                    current_bit = self.freq_bin_string[freq]
                    found = True
                    break
            if not found:
                current_bit = "?"

            # Process the detected bit
            if current_bit == previous_bit:
                current_bit_length += 1
                if current_bit_length >= self.Ratio_of_Sender_Receiver:
                    current_bit_length = 0
                    binary_data += previous_bit
            else:
                if abs(current_bit_length - self.Ratio_of_Sender_Receiver) <= self.Ratio_Threshold:
                    binary_data += previous_bit
                current_bit_length = 1
                previous_bit = current_bit

            # Determine the data length from the first 8 bits
            if data_length == -1 and len(binary_data) > 8:
                data_length = int(binary_data[4:8], 2)
                sender = int(binary_data[0:2], 2)
                message_id = int(binary_data[2:4], 2)
                binary_data = binary_data[8:]

            # Terminate the loop when full message is recieved
            if data_length != -1 and len(binary_data) >= data_length:
                break
        
        # Print the received bitsting, along with zero padding
        # print("The received bitstring along with zero padding: ", binary_data) 
        # Extract the relevant bits of detected data
        binary_data = binary_data[:data_length]
        # print("Received data from sender after removing zero padding:", binary_data)
        return binary_data, sender, message_id
    
    def receive_cts(self, stream, node_id):
        """
        Start listening for the audio and also do error correction to print the correct output
        """
        # print("Listening for audio signal...")

        binary_data = ""
        previous_bit = "?"
        current_bit = "0"
        current_bit_length = 0
        data_length = -1

        # Main loop to recieve the main signal
        while True:
            data = stream.read(int(self.Sample_rate * self.Bit_duration))
            frame = np.frombuffer(data, dtype=np.int16)
            frame = frame / np.max(np.abs(frame))
            spectrum = np.abs(fft(frame))
            freqs = np.fft.fftfreq(len(spectrum), 1 / self.Sample_rate)

            # Filter the spectrum and frequencies to consider only those > Frequency_filter
            valid_indices = freqs > self.Frequency_filter
            filtered_spectrum = spectrum[valid_indices]
            filtered_freqs = freqs[valid_indices]

            # Find the peak frequency among the filtered frequencies
            peak_freq = filtered_freqs[np.argmax(filtered_spectrum)]
            freq_found = peak_freq
        
            # Determine the current bit based on detected frequency
            found = False
            for freq in self.freq_bin_string:
                if abs(freq_found - freq) <= self.Threshold:
                    current_bit = self.freq_bin_string[freq]
                    found = True
                    break
            if not found:
                current_bit = "?"

            # Process the detected bit
            if current_bit == previous_bit:
                current_bit_length += 1
                if current_bit_length >= self.Ratio_of_Sender_Receiver:
                    current_bit_length = 0
                    binary_data += previous_bit
            else:
                if abs(current_bit_length - self.Ratio_of_Sender_Receiver) <= self.Ratio_Threshold:
                    binary_data += previous_bit
                current_bit_length = 1
                previous_bit = current_bit
            if len(binary_data) >= self.config.rts_cts_length:
                break
        
        # Print the received bitsting, along with zero padding
        # print("Received CTS", binary_data)
        sender = binary_data[:2]
        receiver = binary_data[2:4]
        if receiver == node_id or receiver == "00":
            return True, sender
        return False, ""
    
    def wait_for_ending_signal(self, stream, freq = None):
        if freq is None:
            freq = self.config.ending_freq
        start_time = time.time() 
        while time.time() - start_time < self.config.end_wait_time:
            # Read preamble as input
            data = stream.read(int(self.config.Sample_rate * self.Bit_duration))
            frame = np.frombuffer(data, dtype=np.int16)
            frame = frame / np.max(np.abs(frame))
            
            spectrum = np.abs(fft(frame))
            freqs = np.fft.fftfreq(len(spectrum), 1 / self.config.Sample_rate)
            
            # Detect the peak frequency
            peak_freq = freqs[np.argmax(spectrum)]
            # print("Ending Signal Frequency:", peak_freq, freq)
            if abs(peak_freq - freq) <  self.config.Threshold:
                return False
        return True