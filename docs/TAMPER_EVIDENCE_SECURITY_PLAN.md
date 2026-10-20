# Tamper-Evidence & Security Plan

## Problem statement

Forest departments face significant operational gaps in forest monitoring and
management, particularly in remote regions where reliable communication
infrastructure, real-time field data collection, and integration of ground
observations with geospatial information systems remain limited. In many
forest areas, the absence of cellular connectivity hinders effective
verification of patrol activities and real-time reporting from the field. As
a result, patrol records are often maintained manually, leading to limited
transparency, accountability, and traceability of forest protection
activities. Hence, it is required to have a secure offline verification
framework.

## Objective

Establish a Secure Offline Patrol Verification Framework for Forest Areas
with Limited Connectivity. Address the operational gap in patrol monitoring
within remote forest regions where cellular connectivity is unavailable,
resulting in limited accountability and difficulty in verifying field patrol
activities. Develop and deploy a low-power IoT-enabled patrol verification
framework capable of generating independently verifiable proof of patrol
presence in offline environments. The novelty of the proposed approach lies
in its ability to maintain tamper-resistant digital patrol records, support
automatic synchronization upon restoration of connectivity, and provide
reliable evidence of field activities without dependence on continuous
network access.

## Methodology

**Ground IoT Mesh (offline-first, no-network zones)**

- **RFID Patrol Logging:** forest guards carry RFID cards. The system records
  guard movement at checkpoints (watchtowers, encroachment-prone regions,
  other monitoring points). Each crossing is logged with timestamp and
  location. The system works without mobile network signal and maintains a
  tamper-evident digital register of patrol activity.
- **LoRa Sensor Mesh:** solar-powered LoRa nodes carry camera traps and
  acoustic sensors deployed across high-risk zones. Acoustic sensors identify
  gunshot and chainsaw signatures to catch illegal logging in real time.
  Nodes relay to gateways and store-and-forward locally when the gateway is
  unreachable. The design assumes no GSM or satellite backhaul.

**Project outcome:** a secure offline patrol verification system.

This document is the plan for the "tamper-resistant digital patrol records"
half of that claim — proving a record wasn't forged or altered, and proving
that *before* it ever reaches a network.

## Current state (audited against this repo)

The backend already has a complete, tested signing + hash-chain scheme — but
it has zero producers today, and the live pipeline has none of this at all.

| Path | Signed? | Hash-chained? | Notes |
|---|---|---|---|
| `PatrolEvent` (`forest_patrol.py`, `crypto.py`, `forest_chain.py`) | Yes — ECDSA P-256 + SHA-256, fully implemented and tested | Yes — per-node sequential chain (`previous_hash`/`record_hash`) | **Dormant.** No node or gateway code ever sends a signed event. Even when exercised, an unregistered node's signature falls through as `PENDING`, which is still accepted (HTTP 202), not rejected. |
| RFID scan (`rfid.py`) | No | No | Trusts the gateway-forwarded UID as-is. |
| Fingerprint verification (`verification.py`) | No | No | Trusts `claimed_uid`/`actual_page_id`/`status`/`score` as-is. |
| Acoustic event, unsigned path (`forest_acoustic.py::ingest_unsigned_acoustic_event`) | Explicitly `UNSIGNED`/`PENDING` by design | No | Used because nodes without an RTC/signing key can't produce a trustworthy timestamp or signature yet. |

`backend/app/api/routes/forest_ingest.py` states outright: "There is NO
authentication on these routes." This matches the README's "Known limits"
(no auth, no LoRa encryption). The crypto scheme that exists
(`crypto.py:41` `CURVE = ec.SECP256R1()`, SHA-256 digest, DER signature,
`crypto.py:84-108` canonical signing bytes, `forest_chain.py:13-26` chain
verification, `ForestNode.public_key` as the per-node key registry) is
correct and ready to use — the gap is entirely on the node-firmware side,
plus one backend enforcement bug (PENDING should not equal ACCEPTED once a
node has a registered key).

## Plan — four phases, each independently shippable

### Phase 1 — Local tamper-evidence (node, offline, no asymmetric crypto yet) — IMPLEMENTED

Extended the existing flash event store (`node-firmware/lib/ForestStorage`)
into a real hash chain: each stored record's hash covers
`(previous_record_hash, event_bytes)`. Anyone with physical access to the
flash can no longer delete or reorder an entry without breaking the chain —
detectable the moment the record is read back by the gateway or backend.

- Cheap: SHA-256 only, no keys to manage.
- Works entirely offline, with no network and no backend involved.
- Directly satisfies "independently verifiable proof of patrol presence in
  offline environments" — the proof lives on the device itself.

**What shipped:**
- `lib/Utils/src/Sha256.{h,cpp}` — minimal portable SHA-256 (no mbedtls
  dependency, host-testable), verified against the standard empty-string and
  `"abc"` test vectors.
- `EventRecord` format bumped to version 2 / 80 bytes (was 48): adds a
  32-byte `chainHash` field. `chainHash = SHA256(prevChainHash || localId ||
  type || nodeId || payloadLen || bootCount || uptimeMs || payload)` —
  deliberately excludes `status`/`attempts`, the two fields `markSynced()`/
  `markAttempt()` legitimately rewrite in place after append; including them
  would make the hash stop matching the instant a record syncs, which isn't
  tampering. Flash cost: +1.4 KB firmware flash for ~512 records' worth of
  extra 32-byte fields vs. the old 48-byte record — negligible against the
  3.3 MB partition.
- `LocalEventStore::verifyChain()` walks the currently-stored log and
  recomputes/compares each hash, reporting the first break (slot + local
  id). New serial command `v` (alongside the existing `w/l/m/r/x`) runs it
  on-device.
- Host-tested (`node-firmware/test/local_event_store_test.cpp`, run via
  `test/run_local_store_tests.sh`): clean chain verifies; a payload edit is
  still caught by the pre-existing CRC-16 (unchanged); reordering two
  CRC-valid records (something CRC-16 alone cannot catch) is caught by
  `verifyChain()`; legitimate `compact()` (which removes old SYNCED records)
  is correctly *not* flagged as tampering.

**Known, documented limitations** (inherent to hash chains, not bugs):
- Cannot detect truncation of the newest record(s) — nothing comes after
  them to break. Closing this needs an external anchor (the gateway/backend
  remembering the last hash it accepted from each node), which is naturally
  Phase 2/3 territory once node-side signing exists, not purely on-device.
- `verifyChain()` checks the log *as currently stored*. After a legitimate
  `compact()`/`dropOldest()`, the first surviving record's declared
  previous-hash points at history that was intentionally removed; it's
  treated as the trusted root of what's on flash now, not a break.
  Everything after it must still chain correctly.
- **Format bump breaks compatibility with any already-stored v1 (48-byte)
  log on a device's flash.** `decodeRecord()` already rejects the old
  version byte (`BadVersion`), so an upgraded node will report those old
  records as corrupt during recovery — operators should expect/perform a
  log erase (`x`) when upgrading firmware on a device with pre-existing
  records, the same step used throughout this project's bench testing.

### Phase 2 — Node-side signing (closes the README's "not implemented" gap) — IDENTITY PRIMITIVE DONE, NOT YET WIRED TO EVENTS

Each node generates its own ECDSA P-256 keypair on first boot. The private
key never leaves the device (store it in ESP32-S3 flash encryption / NVS,
not plaintext flash). Only the public key is exported during commissioning,
for an operator to register against that node's `ForestNode.public_key` row.

Every RFID scan and fingerprint-verification event gets signed before LoRa
transmission, reusing the canonicalization scheme already implemented and
tested on the backend (`patrol_signing_bytes`-style field joining). This is
the part that proves *which device* produced a record, not just that the
record is internally consistent.

**What shipped (`node-firmware/lib/ForestCrypto`):**
- `NodeIdentity`: generates an ECDSA P-256 keypair via mbedtls (hardware-
  accelerated on the ESP32-S3) on first boot, persists only the 32-byte
  private scalar in NVS (`Preferences`), re-derives the public point each
  boot rather than also storing it (one secret at rest, not two). Exposes
  `publicKeyHex()` (SEC1 uncompressed point, matches what
  `crypto.py::load_public_key` accepts directly) and `signSha256()` (DER-
  encoded ECDSA-SHA256, matching Python's `ec.ECDSA(hashes.SHA256())`).
- `PatrolSigningBytes`: builds the exact canonical string
  `backend/app/services/crypto.py::patrol_signing_bytes` reconstructs
  server-side, including an ISO-8601 formatter that matches Python's
  `datetime.isoformat()` output for a UTC, whole-second timestamp (the
  precision a DS3231 can provide) - this was the fragile part, since the
  backend re-derives and re-signs-checks this string from its own parsed
  datetime, not from whatever string the node originally sent.
- **Verified for real, not just unit-tested in isolation:** a signature
  produced by actual ESP32-S3 hardware (new serial command `k`) was checked
  against the real, unmodified `backend/app/services/crypto.py` via
  `node-firmware/tools/verify_node_signature.py` and came back `VALID`.
  Key persistence across a real reboot was also confirmed (identical
  pubkey before/after). `PatrolSigningBytes`'s string formatting is
  additionally host-tested (`test/run_patrol_signing_tests.sh`) against
  output actually captured by running the Python function.
- Flash cost: +41 KB (mbedtls ECDSA/ECP code) - negligible against the 3.3
  MB partition.

**Timestamp source resolved - there is no physical RTC on this board** (the
DS3231 driver in the firmware was written against an assumption that didn't
hold for the actual hardware; `t` bench command confirmed "no device
answered at 0x68"). Chose a software clock over adding an RTC chip:

- `node-firmware/lib/ForestTime`: `CivilTime` (pure epoch<->UTC-civil-date
  math, Howard Hinnant's algorithm, host-tested against real Python
  `datetime.fromtimestamp` output across epoch 0, leap days, negative
  epochs, etc. - `test/run_civil_time_tests.sh`) + `SoftClock` (NVS-
  persisted "last synced UTC second + millis() at that moment"; estimates
  current time as sync-point plus elapsed millis() between syncs; `nowIso8601Utc()`
  returns false rather than fabricate a timestamp when never synced).
- The gateway is the time source: it already has WiFi for the backend MQTT
  link, so `BackendIngestionClient::tickWifi()` now requests one-shot NTP
  (`configTime(...)`) the moment WiFi connects; the ESP32 SNTP client keeps
  it updated afterward.
- The existing LoRa ACK (`gateway/src/Gateway/GatewayAckHandler.cpp`) is
  extended from 2 bytes (acked sequence only) to 6 bytes (+ a uint32 UTC
  epoch), gated on `time(nullptr) > 1700000000` so a gateway that hasn't
  synced NTP yet falls back to the plain 2-byte ACK instead of handing out
  a bogus near-zero "time" - the node would otherwise mistake that for
  1970 and silently corrupt its clock. `Constants.h`/`Validator.cpp` in
  **both** `node-firmware` and `gateway` (identical copies of the same
  Protocol library) updated in lockstep to accept either ACK size.
- Node's `waitForGatewayAck()` extracts the time field when present and
  feeds `SoftClock::onSync()`. Verified on real node hardware: boots with
  "no time yet", the `k` bench command correctly refuses to claim a real
  timestamp and falls back to a labeled placeholder. The actual gateway-
  side NTP-sync-then-ACK path could not be verified on real hardware this
  session (only one physical board was available, the node; the gateway
  side is build-verified only, via `pio run -e production`).

**Still not done - this is the real remaining work, not a formality:**
- `signSha256()` is not called anywhere in the RFID/fingerprint/acoustic
  event path yet. Wiring it in for real needs, in order:
  1. `checkpoint_id` / `officer_id` added to the node's config and/or
     derived from the RFID scan (officer identity), since
     `patrol_signing_bytes` needs both and the node has neither today.
  2. A larger LoRa payload (or a multi-packet scheme): a signed
     `PatrolEvent`-equivalent needs node_id, sequence, timestamp,
     checkpoint/officer ids, rfid/fingerprint result, previous/record hash
     *and* a ~70-byte DER signature - far more than the current 6-24 byte
     binary payloads carry.
  3. Gateway firmware changes to decode that larger packet and forward it
     as the rich JSON `backend/app/schemas/forest_ingest.py::ForestPatrolIngest`
     the existing `ingest_patrol_event()` endpoint expects, instead of the
     current unsigned `rfid.py`/`forest_acoustic.py` paths.
  4. End-to-end hardware verification of the gateway NTP/ACK-time path
     above, which needs a second physical board.
  This is genuinely a multi-session protocol change across three codebases
  (node, gateway, and the already-ready backend), not something to rush
  through after the identity + clock primitives above.

### Phase 3 — Make verification a hard gate, not advisory

Today a node with no registered key yields `PENDING`, which is still treated
as `ACCEPTED`. Change this: once a node has a registered public key, a bad or
missing signature, or a broken hash chain, must reject the event (4xx), not
merely flag it. Keep a distinct, dashboard-visible "unverifiable" state for
nodes that have not yet been commissioned with a key, so operators can tell
"verified" apart from "nothing to check yet."

### Phase 4 — LoRa confidentiality: IMPLEMENTED (uplink only)

Signing gives authenticity and integrity, not secrecy. The application
payload on every uplink DATA packet (patrol, acoustic, RFID, verification)
is now wrapped in AES-128-GCM before transmission
(`ForestCrypto/src/LoRaCipher.h/.cpp`, identical copies in node-firmware and
gateway): `nonce(12) || ciphertext || tag(16)`. The outer packet header
(type/source/destination/sequence) stays in clear — the gateway needs it to
route and ACK before it can even attempt a decrypt — and is bound into the
ciphertext as AAD, so a captured ciphertext cannot be replayed under a
different header.

Key management: one pre-shared AES-128 key, shared network-wide (not yet
per-node), in `Secrets.h`/`Config.h` (`FOREST_LORA_AES_KEY`, gitignored,
never committed). A real fleet deployment should provision this per-node
instead of baking one shared key into every node's firmware image — tracked
as a known simplification, not done here.

Nonce: fresh random 96 bits from the hardware RNG on every encryption, not
derived from the sequence counter or persisted anywhere. GCM's one
unforgivable failure mode is reusing a (key, nonce) pair; a random nonce
avoids needing any counter/NVS bookkeeping that could get that wrong, at the
cost of 12 extra wire bytes per packet (`kMaxPayloadSize` bumped
180 → 224 to absorb the 28-byte nonce+tag overhead with margin).

**Scope**: uplink (node → gateway) DATA payloads only. The downlink ACK
(2 or 6 bytes, just an echoed sequence number and optional time sync) is
**not** encrypted — deliberately out of scope for now, since it carries no
operational secrets, documented here rather than left as a silent gap.

**Verification status**: `LoRaCipher`'s AES-GCM wrapper is checked against a
real reference vector captured from Python's `cryptography` library
(round-trip, tamper-detection, and AAD-binding all covered) via the node's
serial `'y'` command — no host-level C++ test exists for this one, because
ESP-IDF's bundled mbedtls isn't reliably host-compilable (same limitation
that applies to `NodeIdentity`/ECDSA, verified the same way via
`tools/verify_node_signature.py`). Both firmwares build clean with
encryption fully wired into the real transmit/receive path. End-to-end
hardware verification (flash both boards, confirm a real patrol/acoustic
event round-trips through encryption) is pending — boards were offline when
this was implemented.

## Why this order

Phase 1 has no key-management problem to solve and ships fastest — an
offline guard log that can detect its own tampering is real novelty on its
own. Phases 2–3 are what actually deliver "independently verifiable proof of
patrol presence": the backend code for this already exists and is tested,
the gap is entirely on the node-firmware side (key generation, signing
before TX) and one backend enforcement rule (stop treating `PENDING` as
`ACCEPTED`). Phase 4 is separable, optional, and addresses confidentiality
rather than tamper-evidence.

## No new hardware required

Every phase above is firmware/backend logic on hardware already in this
project:

- Phase 1 — logic changes only, in `ForestStorage`/`EventRecord` on the
  ESP32-S3 already used.
- Phase 2 — uses the ESP32-S3's built-in hardware-accelerated
  ECDSA/SHA and its flash for key storage. No new component.
- Phase 3 — backend-only logic change.
- Phase 4 — same SX1278 radio already deployed, payload encrypted before
  transmission.

The RC522 (RFID), R307S (fingerprint), and SX1278 (LoRa) already in the
project are exactly what produce the data this plan protects — nothing new
needs to be sensed.
