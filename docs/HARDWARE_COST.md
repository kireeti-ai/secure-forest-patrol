# Hardware cost — components actually used in this project

Filtered from two supplier chat quotes (2026-07-16 and 2026-09-04) down to only the parts
confirmed as part of this build.

## Node (RFID + fingerprint + acoustic + LoRa)

| Component | Role in this project | Unit price |
|---|---|---|
| AS608 (R307 fingerprint) | Second factor for checkpoint verification | ₹875 |
| MFRC522 + 3 cards | RFID first factor | ₹160 |
| VM3011 (MAX4466) | Always-on analog trigger mic for the acoustic pipeline | ₹130 |
| INMP441 | Digital I2S mic, captures the 1.0s/16kHz window fed to the ML classifier | ₹190 |
| ESP32-S3 | Node MCU | ₹690 |

**Node subtotal:** ₹875 + 160 + 130 + 190 + 690 = **₹2,045**

## Gateway (LoRa receiver + Wi-Fi/MQTT bridge)

| Component | Role in this project | Unit price |
|---|---|---|
| SX1278 | LoRa receiver, forwards node packets to the backend over MQTT | ₹390 |
| ESP32-S3 | Gateway MCU (2nd unit — same part as the node's) | ₹690 |

**Gateway subtotal:** ₹390 + 690 = **₹1,080**

> The 2026-07-16 quote labeled this part "SX1262" — confirmed that was just a wrong name in the
> chat; the actual module is the SX1278.

## Totals

| | Base (ex-GST) | +18% GST |
|---|---|---|
| Node (1x) | ₹2,045 | ₹2,413 |
| Gateway (1x) | ₹1,080 | ₹1,274 |
| **Combined (1 node + 1 gateway)** | **₹3,125** | **₹3,688** |

ESP32-S3 appears once in each subtotal above since one is needed per board. If more than one
field node is deployed, each additional node costs ₹2,045 (+18% GST = ₹2,413) on top of the
single shared gateway.


