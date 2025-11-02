# Networking Technologies and Management Systems II  
### Programming Project (WS 2025/26)

---

## 🧩 Project Overview

In order to put the concepts learned in the course into practice, the programming project aims at implementing **a simple messaging protocol for chat applications built on top of UDP**.

This protocol — called **Simple IMC Messaging Protocol (SIMP)** — could in theory be used by a third-party to implement a chat program at the application layer level.

---

## 📜 SIMP Specification

### 1. Protocol Concept

SIMP is a **lightweight protocol** implemented over UDP.  
While UDP does not provide reliable delivery, SIMP adds minimal mechanisms to ensure message delivery, using connection setup and acknowledgment logic.

Users are identified by **IP address and port number**.  
Each user must run a SIMP daemon to participate in chats.

- A user can **start or receive** a chat request.  
- If a user is already chatting, new invitations will be **automatically rejected** with an error message (`ERR: user busy`).

Once a chat is accepted, both users can exchange messages until one side closes the connection.

---

### 2. Datagram Types

| Datagram Type | Description | Type Value |
|----------------|--------------|-------------|
| **Control datagram** | Used to establish, terminate, or retransmit data after timeout | `0x01` |
| **Chat datagram** | Used for the actual chat content between users | `0x02` |

---

### 3. Header Format

Each SIMP datagram consists of a **header** and a **payload**.  
All text is encoded using **plain ASCII**.

| Field | Size | Description |
|--------|------|-------------|
| **Type** | 1 byte | `0x01` = control datagram; `0x02` = chat datagram |
| **Operation** | 1 byte | Depends on Type |
| **Sequence** | 1 byte | Sequence number (`0x00` or `0x01`) |
| **User** | 32 bytes | Username (ASCII string) |
| **Length** | 4 bytes | Payload length in bytes |
| **Payload** | Variable | Content depending on the type and operation |

#### Operation Values

If `Type == 0x01` (Control):
- `0x01` → `ERR` (error)
- `0x02` → `SYN` (start connection)
- `0x04` → `ACK` (acknowledge)
- `0x08` → `FIN` (close connection)

If `Type == 0x02` (Chat):
- `Operation = 0x01`

---

### 4. Protocol Operation

#### Connection Establishment (Three-way Handshake)

1. **Sender → Receiver:** send `SYN`
2. **Receiver → Sender:** reply `SYN + ACK` (bitwise OR)
3. **Sender → Receiver:** reply `ACK`

If the receiver declines, step 2 is replaced by a `FIN` message.

#### Message Exchange (Stop-and-Wait)

After connection setup:
- The sender transmits a **chat datagram**.
- Waits for **ACK** before sending the next datagram.
- If no ACK is received within 5 seconds → retransmit same datagram (same sequence number).
- Next message toggles sequence number (`0` ↔ `1`).

If a user is already chatting and receives a new `SYN`:
- Send an `ERR` (“User already in another chat”) and a `FIN`.

To end a chat:
- Send `FIN`; peer replies with `ACK
