# Networking Technologies and Management Systems II  
### Programming Project (WS 2025/26)

---

## 🧩 Project Overview

In order to put the concepts learned in the course into practice, the programming project aims at implementing **a simple messaging protocol for chat applications built on top of UDP**.  

This protocol — called **Simple IMC Messaging Protocol (SIMP)** — could in theory be used by a third-party to implement a chat program at the application layer level.

---

## 📜 SIMP Specification

### 1. Overview

SIMP represents a **lightweight protocol**.  
It does not require all the connection-oriented functionalities of TCP. Instead, it runs on top of **UDP** while still ensuring **message delivery**.

The protocol works as follows:

- Any user may contact another user to start a chat.  
- Users are identified by their **IP address and port number**.  
- Each user must have a running **SIMP implementation** (daemon).  
- A user may **accept or decline** an invitation.  
- Once accepted, both users can exchange messages until one ends the chat.  
- If a user is already in a chat, new invitations are automatically **rejected** with an error message:  
  > “User is busy in another chat”

---

### 2. Types of Datagrams

| Type | Description | Value |
|------|--------------|--------|
| **Control datagram** | Used to establish/terminate connections or resend after timeout | `0x01` |
| **Chat datagram** | Used for actual chat messages | `0x02` |

---

### 3. Header Format

Each SIMP datagram consists of a **header** and a **payload**.

All text (strings) must be encoded in **plain ASCII**.

| Field | Size | Description |
|--------|------|-------------|
| **Type** | 1 byte | Type of datagram: `0x01` = control, `0x02` = chat |
| **Operation** | 1 byte | Operation type (see below) |
| **Sequence** | 1 byte | Sequence number: `0x00` or `0x01` |
| **User** | 32 bytes | Username (ASCII string) |
| **Length** | 4 bytes | Payload length in bytes |
| **Payload** | Variable | Message content or error text |

#### Operation Values

If `Type == 0x01` (Control datagram):

| Operation | Meaning |
|------------|----------|
| `0x01` | `ERR` — Error condition occurred |
| `0x02` | `SYN` — Used to initiate connection |
| `0x04` | `ACK` — Used as acknowledgement |
| `0x08` | `FIN` — Used to close connection |

If `Type == 0x02` (Chat datagram):

| Operation | Meaning |
|------------|----------|
| `0x01` | Chat message |

---

### 4. Operation

#### Connection Establishment (Three-way Handshake)

1. **Sender → Receiver:** Send `SYN` control datagram  
2. **Receiver → Sender:** Reply with `SYN + ACK` (bitwise OR)  
3. **Sender → Receiver:** Reply with `ACK`

If the receiver declines, Step 2 is replaced with a `FIN` datagram.

#### Message Transmission (Stop-and-Wait)

After connection setup:
- Sender transmits a datagram and **waits for ACK**
- If **no ACK** received within **5 seconds**, resend same datagram (same sequence number)
- Once ACK arrives, send next message (toggle sequence: 0 ↔ 1)

If a user already in chat receives another `SYN`:
- Respond with `ERR: "User already in another chat"` and `FIN`

To close chat:
- Send `FIN`
- Peer responds with `ACK` before disconnecting

---

## ⚙️ Implementation

The SIMP system has **two components**:

### 1. Daemon (`simp_daemon.py`)
- Runs in the background, listening for incoming connections  
- Must be started before chat  
- Communication between daemons uses **UDP port 7777**  
- Communication between **client and daemon** uses **UDP port 7778**  
- All SIMP communication happens **daemon-to-daemon**

### 2. Client (`simp_client.py`)
- Text-based program for end users  
- Connects to local daemon using its IP as parameter  
- Prompts for username  
- Depending on state:

#### Client Logic

1. **If a chat request is pending:**  
   - Show inviter’s IP and username  
   - Ask user to **accept or decline**

2. **If no chat request pending:**  
   - Ask whether to **start a new chat** or **wait for requests**
   - If starting: prompt for remote user’s IP  
   - If waiting: enter idle mode until an invitation arrives

3. **Quit option:**  
   - User may disconnect anytime by pressing **`q`**

---

### Remarks

**Remark 1:**  
Client and daemon are **separate programs** running independently.  
You must implement your own internal protocol between them supporting:
- `connect` — establish client-daemon connection  
- `chat` — send chat messages  
- `quit` — disconnect client  

**Remark 2:**  
The chat is **synchronous** — the sender waits indefinitely for a reply.

---

## 📦 Submission Details

### Deadline
📅 **15 Jan 2025, 23:59**

#### 1. Python Implementation
- `simp_daemon.py` — Daemon implementation  
- `simp_client.py` — Client implementation  
- `requirements.txt` — List of dependencies (for `pip install -r`)  
- Any auxiliary modules (e.g. `simp_common.py`)

#### 2. Technical Documentation
Include concise documentation describing your implementation and design.

---

## 🧮 Assessment (Total: 40 Points)

| Criteria | Points |
|-----------|--------|
| Correct message implementation (header + payload) | 5 |
| Correct three-way handshake | 10 |
| Correct stop-and-wait | 5 |
| Correct daemon–client communication | 10 |
| A clear and well-structured report (show running results)| 10 |
| **Total** | **40 Points** |

---

## ⚠️ Notes

- UDP ports are fixed:
  - `7777`: daemon-to-daemon  
  - `7778`: client-to-daemon  
- Use **ASCII encoding** for all strings  
- Ensure modular code organization  
- Chat operation must strictly follow **stop-and-wait** and **3-way handshake**

---

*Networking Technologies and Management Systems II — WS 2025/26*  
*Industrial Management and Computing Department*
