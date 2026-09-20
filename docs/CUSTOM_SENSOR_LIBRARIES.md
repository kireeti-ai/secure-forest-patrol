# Custom sensor driver library (`ForestSensors`)

## Requirement
*Custom library implementation: sensor driver via SPI / I2C / UART without external sensor libraries (5 marks).*

The Forest node talks to its sensors through our own driver layer, `node-firmware/lib/ForestSensors/`. The
sensor-specific protocol (register maps, framing, initialisation, command sequences) is our code. The only
things used from outside are the ESP32 hardware-abstraction calls of the Arduino-ESP32 / ESP-IDF framework
(`SPIClass`, `Wire`, `driver/adc.h`, `driver/i2s.h`), which are the peripheral drivers, not sensor libraries.

## Architecture

```
main.cpp / AcousticPipeline            application
        |
ForestSensors library                  our drivers: RFID_RC522, DS3231, MAX4466, INMP441
        |
SPI / I2C / ADC(DMA) / I2S             ESP32-S3 peripheral HAL (framework)
        |
RC522 / DS3231 / MAX4466 / INMP441     sensors
```

## Drivers

| Driver | Interface | Files (`lib/ForestSensors/src/`) | Own protocol code |
|---|---|---|---|
| `ForestSensors::RFID_RC522` | **SPI** | `RFID_RC522.h/.cpp` | MFRC522 register read/write framing (incl. the repeated-address multi-byte read), soft/hard reset, timer + modulation setup, antenna control, REQA, anti-collision + select (cascade levels 1-2, 4- and 7-byte UIDs), BCC and CRC_A checks, HLTA |
| `ForestSensors::DS3231` | **I2C** (0x68) | `DS3231.h/.cpp` | BCD time registers 0x00-0x06, status/OSF flag, temperature, set date/time, Unix time |
| `ForestSensors::MAX4466` | **ADC** (ADC1 + DMA) | `MAX4466.h/.cpp` | ADC digital-controller/DMA setup, block acquisition, DC removal, RMS, min/max, hysteresis trigger state |
| `ForestSensors::INMP441` | **I2S** (RX, DMA) | `INMP441.h/.cpp` | I2S master/Philips config for the 24-bit-in-32 slot, left channel, 32-to-16-bit PCM conversion |
| helpers | none | `SensorMath.h/.cpp` | CRC_A, BCD, block RMS (portable, host-tested) |

**Not implemented: R307 fingerprint (UART).** No fingerprint sensor is connected to the node, so there is no
driver and nothing to test. The project therefore has no UART sensor driver today.

### Third-party sensor libraries that are NOT used
`MFRC522` (miguelbalboa), any DS3231 library, any R307 library, any MAX4466 or INMP441 library. The
`MFRC522` dependency was removed from `platformio.ini`; the PlatformIO dependency graph of the main firmware
lists `LoRa` (radio, out of scope for this requirement), `TensorFlowLite_ESP32` (ML runtime), the project's own
libraries and the framework `SPI`. The project still uses the normal Arduino-ESP32 / PlatformIO framework, so
this is *no sensor-specific external library*, not zero dependencies. (The SX1278 LoRa radio still uses
the `LoRa` library; it is a radio, not one of the assessed sensors.)

## Pin mapping (unchanged)

| Sensor | Pins |
|---|---|
| RC522 | SCK 35, MISO 37, MOSI 36, SS 4, RST 5 |
| SX1278 (LoRa) | SCK 12, MISO 13, MOSI 11, CS 10, RST 9, DIO0 14 |
| DS3231 | SDA 21, SCL 20 |
| MAX4466 | OUT to GPIO 1 |
| INMP441 | BCLK 6, WS 7, SD 8 |
| RGB LED | GPIO 48 |

The RC522 and SX1278 share one SPI peripheral that `main.cpp` re-pins before each use; the driver is given the
`SPI` object and only asserts its own chip select, so it works with that scheme.

## Example use

```cpp
#include "RFID_RC522.h"
ForestSensors::RFID_RC522 rfid(/*SS*/ 4, /*RST*/ 5);
ForestSensors::RfidUid uid;

SPI.begin(35, 37, 36, 4);          // SCK, MISO, MOSI, SS
rfid.begin(SPI);                    // reset, configure, antenna on; false if the chip is absent
if (rfid.isCardPresent() && rfid.readUid(uid)) { /* uid.size, uid.bytes[] */ rfid.halt(); }
```

```cpp
ForestSensors::DS3231 rtc; ForestSensors::DateTime t;
rtc.begin(21, 20); rtc.readDateTime(t);
ForestSensors::MAX4466 mic; mic.begin(1, 8000, 128); float rms; mic.readRms(rms, 100);
ForestSensors::INMP441 i2s; i2s.begin(6, 7, 8, 16000, 16); int16_t pcm[128]; i2s.readSamples(pcm, 128, 100);
```

`main.cpp` uses `ForestSensors::RFID_RC522` for every card scan. `AcousticPipeline` uses `ForestSensors::MAX4466`
and `ForestSensors::INMP441` (through the aliases in `AcousticTrigger.h` / `AudioCapture.h`).

## How the RC522 driver talks to the chip
1. SPI mode 0, 4 MHz, MSB first. First byte of a transaction = `(register << 1)` with bit 7 set for a read.
   A multi-byte read repeats the address byte before every data byte and ends with `0x00`.
2. `begin()`: hardware reset pulse, soft-reset command, timer (25 ms), 100 % ASK, CRC preset 0x6363, antenna on;
   `VersionReg` must be neither 0x00 nor 0xFF.
3. `isCardPresent()`: 7-bit REQA (0x26) through the Transceive command; a 2-byte ATQA means a card answered.
4. `readUid()`: SEL(0x93/0x95) + NVB(0x20) returns 4 UID bytes + BCC; the BCC is checked; a select frame with
   our software CRC_A returns SAK; SAK bit 2 (cascade) continues at the next level for 7-byte UIDs.
5. `halt()`: HLTA (0x50 0x00 + CRC_A).

## Test procedure and evidence
Serial monitor at 115200 baud on the node (`pio run -t upload`, `pio device monitor`):

| # | Action | Expected |
|---|---|---|
| 1 | Boot | `RC522 Firmware: 0x82`, `RC522 READY (ForestSensors custom SPI driver)` |
| 2 | Tap a card | `>>> CARD DETECTED <<<`, `UID: ...`, then the LoRa transmission |
| 3 | Type `t` | `[DRIVER] RC522 ... VersionReg=0x82`, and the DS3231 time (or "not connected") |
| 4 | Acoustic test modes: `-D FOREST_ACOUSTIC_TEST_MODE=1` (MAX4466 RMS / DC / min / max) and `=2` (INMP441 min / max / mean / RMS) | Both print through the ForestSensors drivers |

Host tests: `bash node-firmware/test/run_local_store_tests.sh` checks CRC_A (the known HLTA value 57 CD), BCD
conversion and block RMS.

### Results (measured on the node board)
| Item | Status | Evidence |
|---|---|---|
| RC522 custom SPI driver: init, version, UID read, halt | **PHYSICALLY VERIFIED** | Boot: `RC522 Firmware: 0x82`, `READY (ForestSensors custom SPI driver)`; UIDs `CD:4E:32:40`, `30:BD:57:58`, `BD:8C:6D:19` read and transmitted; the LoRa frame for `CD:4E:32:40` was byte-identical to the one produced with the old library (`... 0D 4E`) |
| RC522 driver bug found by hardware | fixed | multi-byte FIFO reads returned garbage until the address byte was repeated per byte; UID reads failed before, succeeded after |
| DS3231 I2C driver | **IMPLEMENTED**, compiled; **NOT VERIFIED** on hardware | `t` command reports "no device answered at 0x68": no RTC is connected |
| MAX4466 ADC/DMA driver | **PHYSICALLY VERIFIED** as a driver (blocks, RMS, DC reported); the sensor signal itself is **UNDER VALIDATION** (see ACOUSTIC_NODE.md "Bench findings") |
| INMP441 I2S driver | **PHYSICALLY VERIFIED** as a driver (non-zero varying PCM, model runs on it); speech-vs-quiet separation and sample rate not measured |
| R307 UART fingerprint driver | **NOT IMPLEMENTED** (no hardware) |
