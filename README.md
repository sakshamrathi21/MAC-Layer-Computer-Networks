## MAC Layer - Audio Network

### Introduction
In this implementation, we use **CSMA-CA** (Carrier Sense Multiple Access with Collision Avoidance), similar to WiFi, with some modifications tailored for our protocol.
### Frame Structure
Each node is assigned a unique 2-bit address:

- **"00"**: Broadcast address (used for sending messages to all nodes)
- **"01"**: Node 1
- **"10"**: Node 2
- **"11"**: Node 3

The frame structures are as follows:

1. **RTS (Request to Send) Frame**:
   - Preamble (6 bits)
   - Sender's Address (2 bits)
   - Receiver's Address (2 bits)

2. **CTS (Clear to Send) Frame**:
   - Similar structure as RTS with preamble, sender, and receiver address.

3. **Data Frame**:
   - Preamble (6 bits)
   - Sender's Address (2 bits)
   - Message ID (2 bits)
   - Length of Message (4 bits)
   - Data (1-15 bits)

After a message is successfully received, the receiver sends a **2-bit acknowledgment** to confirm proper reception.

### Implementation Details
- **Two Threads**: 
  - One thread listens for incoming messages and adds them to a buffer.
  - The other thread handles communication (RTS, CTS, data frames, acknowledgment) based on messages in the buffer.
  
- **Exponential Backoff**: 
  - If a collision is detected, nodes use an exponential backoff strategy, doubling the waiting range with each collision.
  
- **Clock Synchronization**:
  - The clocks are synchronized using the **NTP (Network Time Protocol)**.
  
- **Multiple Frequencies**:
  - RTS, CTS, and preambles are transmitted at different frequencies to aid in detection.

### Algorithm Overview
1. **Message Handling**: 
   - If a node has a message to send, it adds the message to a buffer and waits for the correct transmission window.
   
2. **Broadcast Handling**: 
   - For broadcast messages, the node sends the message to all nodes and waits for acknowledgments. 
   - If any acknowledgment is missing, the broadcast is retransmitted.
   
3. **RTS/CTS Handling**: 
   - Nodes send RTS before sending data and wait for a CTS response.
   - If CTS is not received, nodes assume a collision and apply exponential backoff.
   
4. **Error Handling**: 
   - If no acknowledgment is received after data transmission, nodes assume a collision and enter the exponential backoff stage again.

### Testing
The implementation is designed to scale with any number of nodes, though the demo will involve three. Testing includes ensuring successful message delivery and appropriate handling of collisions.

### Instructions for Running
1. Run `python3 input.py` to input messages (this acts as the trigger).
2. Run `python3 main.py` to initiate message sending and receiving. Provide the node ID (1, 2, or 3) at the start.
