# Utils

Purpose: hold small platform-neutral utilities such as CRC and logging policy.

Public API: `Crc16` (CRC-16/CCITT-FALSE, also used by the local event store) and buffer helpers.

Roadmap: keep only shared utilities with no domain ownership here.

Decision: this library is portable C++ with no Arduino dependency so it can be host-tested.
