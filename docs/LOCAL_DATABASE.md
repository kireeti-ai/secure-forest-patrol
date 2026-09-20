# Local event store (`ForestStorage`)

## Requirement
*Local database working: data logging in Flash / EEPROM / SD, with a persistence demo (5 marks).*

The node keeps its own persistent event log on the **ESP32-S3 internal flash** (LittleFS). The backend
PostgreSQL database is separate and does not count for this requirement. No SD card is needed.

## Design
- Code: `node-firmware/lib/ForestStorage/` (`LocalEventStore`, `EventRecord`, `LittleFsBackend`).
- Storage technology: **LittleFS** (Arduino-ESP32 framework) on the `spiffs` data partition, 1536 KB with the current
  partition table. Two files: `/events.log` (append-only records) and `/meta.bin` (boot counter, overflow counter).
- Only the record being handled is in RAM. There is no in-memory copy of the log.
- Only discrete events are written (a card scan, an acoustic detection, a status change), never a stream.

### Flow
```
RFID scan / acoustic detection
   -> append()              record written to flash, status PENDING_SYNC
   -> LoRa transmit, then wait up to 1.5 s for the gateway's Acknowledgement packet for that sequence number
   -> ACK received          markSynced() -> SYNCED
   -> no ACK / radio fails / reset   stays PENDING_SYNC; retryPendingEvent() resends the oldest one every 15 s
```
**"SYNCED" means the gateway acknowledged the LoRa packet** (the gateway sends a type-3 Acknowledgement carrying
the acknowledged sequence number, `gateway/src/Gateway/GatewayAckHandler.cpp`; the node checks type,
destination and sequence in `waitForGatewayAck()`). It proves the gateway radio received the packet. The gateway
publishes to MQTT right after; a failure between the gateway and the backend is not visible to the node.
Delivery is at-least-once: if only the ACK is lost, the retry sends a second copy.

### Record (fixed 48 bytes, little endian)
`magic 0xE7 | version | type (1 RFID, 2 ACOUSTIC, 3 TEST) | status (1 PENDING_SYNC, 2 SYNCED) | local id u32 |
node id | payload length | attempts | reserved | boot counter u32 | uptime ms u32 | payload[24] | reserved | CRC-16`.
The payload is exactly what goes into the LoRa packet (`'R' 01 len UID...` or `'A' 01 class conf rms`), so no
raw audio and no invented fields are stored. The CRC is `forest::utils::Crc16` (CCITT-FALSE), the same routine as the
LoRa protocol. Event ids are derived, e.g. `N01-RFID-000004`, `N01-ACOUSTIC-000005`, `TEST-001`.

**No wall-clock time is stored**: the node has no RTC connected, so a record carries `boot counter + uptime`. The
backend still stamps events on arrival. The existing signature / hash-chain fields are not part of the
unsigned RFID and acoustic events, so they are not stored.

### Integrity and recovery (`begin()` after every reset)
- Records failing magic / CRC / field checks are skipped and removed (`corruptSkipped`).
- Local ids only increase, so a repeated or lower id (left by an interrupted compaction) is dropped (`duplicatesSkipped`).
- A partial record left by a power loss during an append is cut off (`tornTailBytes`).
- LittleFS commits a file on close, so a status update rewrites one record atomically.

### Capacity and wear
- 48 bytes per record; default limit 512 records = 24,576 bytes (1.6 % of the 1536 KB partition).
- When full: first `compact()` drops SYNCED records; if the log is full of PENDING records the **oldest pending
  record is overwritten** and counted in `overflowDropped` (persisted). Nothing is lost silently.
- Each event costs about two small writes (append + status update), and LittleFS wear-levels across the partition.

## Serial demo (115200 baud)
| Key | Action |
|---|---|
| `w` | write a TEST event (`TEST-001`, PENDING_SYNC) |
| `l` | list stored events |
| `m` | mark the oldest pending event SYNCED |
| `r` | reboot the ESP32 (software reset) |
| `x` | erase the log |

Demo: `w` -> `l` -> `r` -> the boot log shows `Recovered N events` and the record again. For the **power-cycle**
demo: `w`, unplug the USB power, plug it back in, and read the boot log.

## Test evidence
| Item | Status | Evidence |
|---|---|---|
| Record codec, CRC, corrupt / duplicate / torn-tail recovery, sync state, restart simulation, compaction, overflow | **TESTED** (host) | `bash node-firmware/test/run_local_store_tests.sh` -> `LOCAL STORE TESTS PASS` |
| Write to flash | **PHYSICALLY VERIFIED** | `Event written`, `Event ID = TEST-001`, `Status = PENDING_SYNC` |
| Persistence across software reset | **PHYSICALLY VERIFIED** | after `r`: `Initialized ... boot #2`, `Recovered 1 events`, `TEST-001 ... boot=1 uptime=9646ms` (original boot and uptime preserved) |
| Persistence across firmware re-flash | **PHYSICALLY VERIFIED** | 6 records recovered after re-flashing the application |
| Persistence across power cycle | **PHYSICALLY VERIFIED** | `TEST-043` was written (`boot=7`, `uptime=25611ms`), the operator unplugged and re-plugged the board's USB power, and the record was read back unchanged (`PENDING_SYNC`, same boot/uptime) among 44 records; the boot counter advanced by one. The unplugging itself was done by the operator and not observed by the test script; note that opening the serial port also resets this board, so the boot counter alone does not prove a power cycle, the surviving unique record does |
| Real RFID events stored and synced by gateway ACK | **PHYSICALLY VERIFIED** | `N01-RFID-000026..35, 38`: `Gateway ACK received for sequence N` then `SYNCED (gateway acknowledged)`; payloads carry the real UIDs |
| Real acoustic events stored and synced by gateway ACK | **PHYSICALLY VERIFIED** | e.g. `N01-ACOUSTIC-000037`; the classification itself is unvalidated model output |
| Pending event kept and retried until acknowledged | **PHYSICALLY VERIFIED** (uncontrolled) | events `000027`, `000032`, `000033`, `000036` got no ACK on the first send (the gateway radio missed the packet), stayed `PENDING_SYNC` (`attempts=1`), were resent by `RETRY TX` and became SYNCED. A deliberate gateway-off test was **not** achieved |
| Events reach the backend | **END-TO-END VERIFIED** for RFID scans (backend held seq 6-13 with the right officers after the gateway reset); not re-checked for the ACK build |

## Limitations
- SYNCED = gateway acknowledged the LoRa packet; it does not prove the backend stored it.
- Before the ACK was added, SYNCED meant only "radio TX complete", and ~12 RFID and 5 acoustic events sent while the gateway radio was deaf were marked SYNCED and lost. With ACKs they would have stayed pending.
- Events resent from the store reach the backend with the backend's arrival time, so a late retry shows a late
  timestamp; there is no RTC on the node to carry the original time.
- Compaction rewrites the log in place (write index never passes the read index); a power loss in the middle can
  leave duplicates, which recovery removes.

## Gateway receiver (why acknowledgements matter)
The gateway used the LoRa library's `parsePacket()` polling, which puts the SX1278 into single-shot receive on
every call; that mode times out into standby, so the receiver is deaf between polls and packets were missed
(one gateway stopped hearing the node entirely after ~37 minutes). The driver now keeps the chip in continuous
receive, reads `RegIrqFlags` and calls `parsePacket()` only when RxDone is set, and a 1 s watchdog re-arms
receive if `RegOpMode` is not LoRa-RX-continuous (0x85) and re-initialises the radio after 10 minutes of silence
(`gateway/lib/LoRaDriver/Sx1278LoRaDriver.cpp`). Not yet shown: a multi-hour soak test of the new receiver.
