"""CS378 - MAC Layer Code using pyaudio for audio transmission and reception"""
"""Authors: Saksham Rathi, Kavya Gupta, Dion Reji, Geet Singhi"""
"""Clear variable names and comments have been used to make the code more readable"""
from config import Config
from sender import Sender
from receiver import Receiver
from queue import Queue
import os
import time
import pyaudio
import random
import ntplib
import socket
import datetime
import warnings
warnings.filterwarnings("ignore")


def get_ntp_timestamp():
    """Get the timestamp."""
    try:
        socket.setdefaulttimeout(0.5)
        current_time = datetime.datetime.now()  # Returns current system time
        return (current_time.strftime('%H:%M:%S'))
        # client = ntplib.NTPClient()
        # response = client.request('pool.ntp.org')
        # time_string = time.strftime('%H:%M:%S', time.localtime(response.tx_time))
        return time_string
    except:
        current_time = datetime.datetime.now()  # Returns current system time
        return (current_time.strftime('%H:%M:%S'))


class Main:
    """
    A class used to represent the main class that sends and receives the message

    Attributes
    ----------
    config : Config
        The configuration object that contains the parameters for the sender and receiver
    sender : Sender
        The sender object that sends the message
    receiver : Receiver
        The receiver object that receives the message
    """
    def __init__(self) -> None:
        """Initialises the member variables of the class"""
        self.config = Config()
        self.sender = Sender()
        self.receiver = Receiver()
        self.all_messages_received = set()
        self.has_msg_to_send = False
        self.is_channel_busy = False
        self.current_wait_time = 0
        self.buffer_file = ".buffer"
        self.last_modified_time = os.path.getmtime(self.buffer_file)
        self.current_message_queue = Queue()
        self.p = pyaudio.PyAudio() 
        self.last_line_number = 0
        self.current_message_id = 0
        if os.path.exists(self.buffer_file):
            with open(self.buffer_file, 'r') as file:
                self.last_line_number = len(file.readlines())
    def return_stream_pre(self, stream):
        """Returns the stream to the preamble state"""
        stream.stop_stream()
        stream.close()
        stream = self.p.open(format=pyaudio.paInt16,
            channels=1,
            rate=self.config.Sample_rate,
            input=True,
            frames_per_buffer=int(self.config.Sample_rate * self.config.Preamble_duration))
        return stream
    def freq_is_preamble(self, freq: int) -> bool:
        """Checks if the frequency is a preamble frequency"""
        return abs(freq - self.config.rts_preamble_freq) < self.config.Threshold

    def freq_is_broadcast(self, freq: int) -> bool:
        """Checks if the frequency is a broadcast frequency"""
        return abs(freq - self.config.broadcast_preamble_freq) < self.config.Threshold
    
    def has_new_message(self) -> bool:
        """
        Checks if the .buffer file has a new message by comparing
        its last modified time.
        """
        if os.path.exists(self.buffer_file):
            modified_time = os.path.getmtime(self.buffer_file)
            if modified_time > self.last_modified_time:
                self.last_modified_time = modified_time
                return True
        return False
    
    def wait_random(self):
        """Returns a random wait time following exponential backoff"""
        return (random.randint(1,2**self.config.num_collisions))*self.config.collision_wait_time*int(self.config.node_id, 2)
    
    def read_message(self) -> str:
        """Reads the latest message from the .buffer file"""
        with open(self.buffer_file, 'r') as file:
            lines = file.readlines()
            for i in range(self.last_line_number, len(lines)):
                our_line = lines[i].split(" ")
                if our_line[1] != "-1\n":
                    our_line[0] = self.config.node_id + str(bin(self.current_message_id)[2:].zfill(2)) + our_line[0]
                    self.current_message_queue.put((our_line[0], our_line[1]))
                    self.current_message_id += 1
            self.last_line_number = len(lines)
    
    def is_message_broadcast(self, message) -> bool:
        """Checks if the message is a broadcast message"""
        if message[1] == "0\n":
            return True
        return False
    
    def __call__(self) -> None:
        """The main function that sends and receives messages"""
        # Take node id as input
        self.config.node_id = str(bin(int(input("Enter the node id: ")))[2:].zfill(2))
        stream = self.p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=self.config.Sample_rate,
                    input=True,
                    frames_per_buffer=int(self.config.Sample_rate * self.config.Preamble_duration))
        while True:
            # Run in an infinite loop to keep sending and receiving messages
            if not self.current_message_queue.empty():
                self.has_msg_to_send = True
            if self.has_new_message():
                # print("New message detected!")
                self.read_message()
                if not self.current_message_queue.empty():
                    self.has_msg_to_send = True
                else:
                    self.has_msg_to_send = False
            current_freq = self.receiver.return_freq(receieve_stream=stream)
            self.current_wait_time -= self.config.Preamble_duration
            # If broadcast preamble received:
            if self.freq_is_broadcast(current_freq):
                # print("Preamble Started.")
                timed_out = self.receiver.receive_preamble(self.config.Preamble_length-1, stream, self.config.broadcast_preamble_freq)
                # print("timed out", timed_out)
                if timed_out:
                    continue
                stream.stop_stream()
                stream.close()
                stream = self.p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=self.config.Sample_rate,
                    input=True,
                    frames_per_buffer=int(self.config.Sample_rate * self.config.Bit_duration))
                # print("Starting Broadcast Message")
                message, sender_id, message_id = self.receiver.receive_message(stream)
                if "?" in message:
                    # If the message is not received properly, then ignore it
                    stream = self.return_stream_pre(stream)
                    continue
                if (sender_id, message_id) not in self.all_messages_received:
                    self.all_messages_received.add((sender_id, message_id))
                    print("[RECVD]: ", message, " ", sender_id, " ", get_ntp_timestamp())
                stream.stop_stream()
                stream.close()
                stream = self.p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=self.config.Sample_rate,
                    output=True)
                time.sleep(0.3)
                # Send acknowledgement
                if self.config.num_nodes == 2:
                    self.sender.send_ending_signal(stream, freq=self.config.ending_signals_map[self.config.node_id])
                    stream = self.return_stream_pre(stream)
                    continue
                if sender_id == 1:
                    if self.config.node_id == "10":
                        self.sender.send_ending_signal(stream, freq=self.config.ending_signals_map[self.config.node_id])
                    else:
                        time.sleep(self.config.Bit_duration)
                        self.sender.send_ending_signal(stream, freq=self.config.ending_signals_map[self.config.node_id])
                else:
                    if self.config.node_id == "01":
                        self.sender.send_ending_signal(stream, freq=self.config.ending_signals_map[self.config.node_id])
                    else:
                        time.sleep(self.config.Bit_duration)
                        self.sender.send_ending_signal(stream, freq=self.config.ending_signals_map[self.config.node_id])
                stream = self.return_stream_pre(stream)
            elif self.freq_is_preamble(current_freq):
                # Preamble frequency detected
                # print("Preamble Started.")
                timed_out = self.receiver.receive_preamble(self.config.Preamble_length-1, stream, self.config.rts_preamble_freq)
                # print("timed out", timed_out)
                if timed_out:
                    continue
                if not timed_out:
                    # print("Preamble Detected.")
                    stream.stop_stream()
                    stream.close()
                    stream = self.p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=self.config.Sample_rate,
                        input=True,
                        frames_per_buffer=int(self.config.Sample_rate * self.config.Bit_duration))
                    # print("Starting RTS Detection...")
                    is_message_for_us, sender_id = self.receiver.receive_rts(self.config.node_id, stream)
                    # print("RTS Found!")
                    stream.stop_stream()
                    stream.close()
                    if is_message_for_us:
                        stream = self.p.open(format=pyaudio.paFloat32,
                            channels=1,
                            rate=self.config.Sample_rate,
                            output=True)
                        # print("CTS Preamble")
                        time.sleep(0.3)
                        # Send CTS
                        self.sender.send_preamble(stream, self.config.cts_preamble_freq)
                        # print("CTS")
                        self.sender.send_cts(stream, cts_message=self.config.node_id+sender_id)
                        stream.stop_stream()
                        stream.close()
                        stream = self.p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=self.config.Sample_rate,
                            input=True,
                            frames_per_buffer=int(self.config.Sample_rate * self.config.Preamble_duration))
                        # print("Start Receiving Message")
                        timed_out = self.receiver.receive_preamble(self.config.Preamble_length, stream, self.config.message_preamble_freq)
                        stream.stop_stream()
                        stream.close()
                        if timed_out:
                            stream = self.return_stream_pre(stream)
                            continue
                        # print("timed out", timed_out)
                        if not timed_out:
                            stream = self.p.open(format=pyaudio.paInt16,
                                                channels=1,
                                                rate=self.config.Sample_rate,
                                                input=True,
                                                frames_per_buffer=int(self.config.Sample_rate * self.config.Bit_duration))
                            # print("Starting Message")
                            message, sender_id, message_id = self.receiver.receive_message(stream)
                            if "?" in message:
                                # Message not received properly
                                stream = self.return_stream_pre(stream)
                                continue
                            if (sender_id, message_id) not in self.all_messages_received:
                                self.all_messages_received.add((sender_id, message_id))
                                print("[RECVD]: ", message, " ", sender_id, " ", get_ntp_timestamp())
                            stream.stop_stream()
                            stream.close()
                            stream = self.p.open(format=pyaudio.paFloat32,
                                channels=1,
                                rate=self.config.Sample_rate,
                                output=True)
                            time.sleep(0.3)
                            self.sender.send_ending_signal(stream)
                            stream.stop_stream()
                            stream.close()
                            stream = self.p.open(format=pyaudio.paInt16,
                                channels=1,
                                rate=self.config.Sample_rate,
                                input=True,
                                frames_per_buffer=int(self.config.Sample_rate * self.config.Preamble_duration))
                    else:
                        stream.stop_stream()
                        stream.close()
                        stream = self.p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=self.config.Sample_rate,
                            input=True,
                            frames_per_buffer=int(self.config.Sample_rate * self.config.Bit_duration))
                        timed_out = self.receiver.wait_for_ending_signal(stream)
                        stream.stop_stream()
                        stream.close()
                        stream = self.p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=self.config.Sample_rate,
                            input=True,
                            frames_per_buffer=int(self.config.Sample_rate * self.config.Preamble_duration))
            else:
                if self.has_msg_to_send and self.current_wait_time <= 0 and not self.is_channel_busy:
                    stream.stop_stream()
                    stream.close()
                    stream = self.p.open(format=pyaudio.paFloat32,
                        channels=1,
                        rate=self.config.Sample_rate,
                        output=True)
                    self.current_message = self.current_message_queue.get()
                    if self.is_message_broadcast(self.current_message):
                        # print("Sending Broadcast Preamble")
                        self.sender.send_preamble(stream, self.config.broadcast_preamble_freq)
                        # print("Sending Broadcast Message")
                        self.sender.send_message(stream, self.current_message[0])
                        print("[SENT]: ", self.current_message[0][4:], " ", self.current_message[1].replace("\n", ""), " ", get_ntp_timestamp())
                        stream.stop_stream()
                        stream.close()
                        stream = self.p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=self.config.Sample_rate,
                            input=True,
                            frames_per_buffer=int(self.config.Sample_rate * self.config.Bit_duration))
                        # If we do not receive ackonwledgement, then we will resend the message after waiting for a random time following exponential backoff
                        if self.config.num_nodes == 2:
                            if self.config.node_id == "10":
                                timed_out = self.receiver.wait_for_ending_signal(stream, self.config.ending_signals_map["01"]) 
                                # print("timed out", timed_out)   
                                if timed_out:
                                    self.config.num_collisions += 1
                                    # print("Num collisions: ", self.config.num_collisions)
                                    self.current_wait_time = self.wait_random()
                                    self.current_message_queue.put(self.current_message)
                                    stream = self.return_stream_pre(stream)
                                    continue
                                self.has_msg_to_send = False
                                self.num_collisions = 0
                            elif self.config.node_id == "01":
                                timed_out = self.receiver.wait_for_ending_signal(stream, self.config.ending_signals_map["10"]) 
                                # print("timed out", timed_out)   
                                if timed_out:
                                    self.config.num_collisions += 1
                                    # print("Num collisions: ", self.config.num_collisions)
                                    self.current_wait_time = self.wait_random()
                                    self.current_message_queue.put(self.current_message)
                                    stream = self.return_stream_pre(stream)
                                    continue
                                self.has_msg_to_send = False
                                self.num_collisions = 0
                            stream = self.return_stream_pre(stream)
                            continue
                        if self.config.node_id == "01":
                            timed_out = self.receiver.wait_for_ending_signal(stream, self.config.ending_signals_map["10"]) 
                            if timed_out:
                                self.current_message_queue.put(self.current_message)
                                stream = self.return_stream_pre(stream)
                                self.config.num_collisions += 1
                                # print("Num collisions: ", self.config.num_collisions)
                                self.current_wait_time = self.wait_random()
                                continue
                            timed_out = self.receiver.wait_for_ending_signal(stream, self.config.ending_signals_map["11"]) 
                            if timed_out:
                                self.current_message_queue.put(self.current_message)
                                stream = self.return_stream_pre(stream)
                                self.config.num_collisions += 1
                                # print("Num collisions: ", self.config.num_collisions)
                                self.current_wait_time = self.wait_random()
                                continue
                            self.has_msg_to_send = False
                            self.num_collisions = 0
                        elif self.config.node_id == "10":
                            timed_out = self.receiver.wait_for_ending_signal(stream, self.config.ending_signals_map["01"]) 
                            if timed_out:
                                self.config.num_collisions += 1
                                # print("Num collisions: ", self.config.num_collisions)
                                self.current_wait_time = self.wait_random()
                                self.current_message_queue.put(self.current_message)
                                stream = self.return_stream_pre(stream)
                                continue
                            timed_out = self.receiver.wait_for_ending_signal(stream, self.config.ending_signals_map["11"]) 
                            if timed_out:
                                self.current_message_queue.put(self.current_message)
                                stream = self.return_stream_pre(stream)
                                self.config.num_collisions += 1
                                # print("Num collisions: ", self.config.num_collisions)
                                self.current_wait_time = self.wait_random()
                                continue
                            self.has_msg_to_send = False
                            self.num_collisions = 0
                        else:
                            timed_out = self.receiver.wait_for_ending_signal(stream, self.config.ending_signals_map["01"]) 
                            if timed_out:
                                self.current_message_queue.put(self.current_message)
                                stream = self.return_stream_pre(stream)
                                self.config.num_collisions += 1
                                # print("Num collisions: ", self.config.num_collisions)
                                self.current_wait_time = self.wait_random()
                                continue
                            timed_out = self.receiver.wait_for_ending_signal(stream, self.config.ending_signals_map["10"]) 
                            if timed_out:
                                self.current_message_queue.put(self.current_message)
                                stream = self.return_stream_pre(stream)
                                self.config.num_collisions += 1
                                # print("Num collisions: ", self.config.num_collisions)
                                self.current_wait_time = self.wait_random()
                                continue
                            self.has_msg_to_send = False
                            self.num_collisions = 0
                        stream = self.return_stream_pre(stream)
                        continue
                    # print("Sending Preamble")
                    # UNICAST message
                    self.sender.send_preamble(stream, self.config.rts_preamble_freq)
                    # print("Sending RTS")
                    self.sender.send_rts(stream, rts_message=self.config.node_id+str(bin(int(self.current_message[1]))[2:].zfill(2)))
                    stream.stop_stream()
                    stream.close()
                    # print("RTS SENT")
                    stream = self.p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=self.config.Sample_rate,
                        input=True,
                        frames_per_buffer=int(self.config.Sample_rate * self.config.Preamble_duration))
                    # print("Waiting for CTS Preamble")
                    timed_out = self.receiver.receive_preamble(self.config.Preamble_length, stream, self.config.cts_preamble_freq)
                    if timed_out:
                        self.config.num_collisions += 1
                        # print("Num collisions: ", self.config.num_collisions)
                        self.current_wait_time = self.wait_random()
                        # print("Random Wait Time: ", self.current_wait_time)
                        self.current_message_queue.put(self.current_message)
                        continue
                    # print("timed_out", timed_out)
                    if not timed_out:
                        self.config.num_collisions = 0
                        stream.stop_stream()
                        stream.close()
                        stream = self.p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=self.config.Sample_rate,
                            input=True,
                            frames_per_buffer=int(self.config.Sample_rate * self.config.Bit_duration))
                        # print("Waiting for CTS")
                        is_cts_for_us, sender_id = self.receiver.receive_cts(stream, self.config.node_id) 
                        if not is_cts_for_us:
                            self.current_message_queue.put(self.current_message) 
                        if is_cts_for_us:
                            stream.stop_stream()
                            stream.close()
                            stream = self.p.open(format=pyaudio.paFloat32,
                                channels=1,
                                rate=self.config.Sample_rate,
                                output=True)
                            time.sleep(0.3) # Processing Time
                            # print("Sending Preamble Message")
                            self.sender.send_preamble(stream, self.config.message_preamble_freq)
                            # print("Sending Message")
                            self.sender.send_message(stream, self.current_message[0])
                            print("[SENT]: ", self.current_message[0][4:], " ", self.current_message[1].replace("\n", ""), " ", get_ntp_timestamp())
                            stream.stop_stream()   
                            stream.close()  
                            stream = self.p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=self.config.Sample_rate,
                            input=True,
                            frames_per_buffer=int(self.config.Sample_rate * self.config.Bit_duration))
                            timed_out = self.receiver.wait_for_ending_signal(stream)
                            if not timed_out:
                                if self.current_message_queue.empty():
                                    self.has_msg_to_send = False
                                    self.num_collisions = 0
                                # print("Ending Signal Received Successfully!")
                            if timed_out:
                                self.current_message_queue.put(self.current_message)
                            stream.stop_stream()   
                            stream.close()
                            stream = self.p.open(format=pyaudio.paInt16,
                                channels=1,
                                rate=self.config.Sample_rate,
                                input=True,
                                frames_per_buffer=int(self.config.Sample_rate * self.config.Preamble_duration))

        stream.stop_stream()
        stream.close()


if __name__ == "__main__":
    main_instance = Main()
    main_instance()