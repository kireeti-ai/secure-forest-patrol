# Acoustic node: MAX4466 trigger + INMP441 + TinyML

**Status: IMPLEMENTED and host/build-TESTED. Only part of it is PHYSICALLY VERIFIED. No microphone has been
connected yet, so nothing about real-audio behaviour is verified.** See [Validation status](#validation-status)
for exactly what was measured and what was not.

```
MAX4466 -> acoustic energy threshold -> ML wake-up -> INMP441 -> preprocessing -> mel/dB
        -> INT8 TinyML -> Gunshot / Chainsaw / Background -> acoustic event -> LoRa -> gateway -> MQTT -> backend
```

The point of the two microphones is to **never run the classifier continuously**. The MAX4466 is a cheap
energy detector; the INMP441 (digital, clean) is the audio the model actually sees.

## Wiring and pins

| Function | ESP32-S3 GPIO | Notes |
|---|---|---|
| MAX4466 OUT | **1** (ADC1_CH0) | VCC 3.3 V, GND. ADC1 is used (ADC2 conflicts with radios/USB) |
| INMP441 SCK / BCLK | **6** | |
| INMP441 WS / LRCLK | **7** | |
| INMP441 SD | **8** | L/R tied to GND -> left channel; VDD 3.3 V |

Existing pins are unchanged: RC522 SCK 35 / MISO 37 / MOSI 36 / SS 4 / RST 5 (build-flag overridable),
SX1278 SCK 12 / MISO 13 / MOSI 11 / CS 10 / RST 9 / DIO0 14, RGB LED 48. No conflicts were found: GPIO 35-37
are free because this board has *quad* PSRAM, and 1/6/7/8 are unused. (Latent, unrelated: `Config.h` declares
I2C SCL = GPIO 20, which is the USB D+ pin. I2C is not used by the running firmware; it must move before an
RTC is wired.)

All pins and parameters are compile-time configurable: `node-firmware/lib/Acoustic/src/AcousticConfig.h`
(`-D FOREST_MAX4466_PIN=1`, `-D FOREST_I2S_BCLK_PIN=6`, ...).

## Integrated firmware (default build)

`pio run -t upload` in `node-firmware/` now builds `esp32-s3-acoustic`: **one firmware** with RFID + LoRa + LED
(loop, core 1) and the acoustic pipeline (tasks, core 0). It is set to `FOREST_ACOUSTIC_TEST_MODE=4`, the **bench
demo**: every 2 s the newest 1 s of live INMP441 audio is classified and logged with the MAX4466 readings
(`[DEMO #n] INMP441 rms/min/max | MAX4466 rms/dc/range | class conf [probs] features invoke`). Log only: set
`-D ACOUSTIC_DEMO_SEND_EVENTS=1` to also send Gunshot/Chainsaw predictions over LoRa. Predictions on real
microphone audio are **unvalidated**. Set the mode to 0 for the MAX4466-gated field pipeline. The RFID-only env
`esp32-s3-devkitm-1` remains as a fallback. Observed on the board: two card scans (`[CARD] VALID`, LoRa
`endPacket=SUCCESS`) were handled immediately while the demo kept classifying; gateway receipt was not checked.

## Building and running

The acoustic pipeline lives in its own PlatformIO env so the working RFID firmware is untouched:

```bash
cd node-firmware
pio run -e esp32-s3-acoustic -t upload          # full pipeline
# test modes (see below), e.g. ML self-test with NO microphones connected:
PLATFORMIO_BUILD_FLAGS="-D FOREST_ACOUSTIC_TEST_MODE=3" pio run -e esp32-s3-acoustic -t upload
pio run -e esp32-s3-devkitm-1 -t upload         # back to the RFID-only firmware
```

## MAX4466 trigger

Raw ADC values are never compared with a threshold (the MAX4466 output rides on a ~VCC/2 bias). Per block:

```
mean = average(samples);  rms = sqrt(average((samples[i] - mean)^2));  trigger when rms >= HIGH
```

- Sampled by the ESP32-S3 ADC1 **DMA** at `MAX4466_SAMPLE_RATE` = 8 kHz; the task wakes once per
  `MAX4466_BLOCK_SIZE` = 128 samples (16 ms; short enough not to average a gunshot impulse away).
- **Relative-dB trigger (default, `ACOUSTIC_RELATIVE_TRIGGER=1`).** Thresholds are decibels above a noise floor the
  node measures itself, so they do not depend on trimmer gain or board:
  - *Warm-up:* the median block RMS over `ACOUSTIC_NOISE_WARMUP_MS` (4 s) is the floor. **Keep the room quiet
    for the first 4 s after every reset.** Nothing can trigger during warm-up.
  - *Trigger:* one block `>= +10 dB` (`ACOUSTIC_TRIGGER_HIGH_DB`, transient / gunshot) **or** `>= +6 dB`
    (`ACOUSTIC_TRIGGER_LOW_DB`) for `ACOUSTIC_SUSTAIN_BLOCKS` = 4 consecutive blocks (~64 ms, chainsaw).
  - *Release / re-arm:* below `+6 dB`. Between +6 and +10 dB the state is held (hysteresis).
  - *Floor tracking:* after warm-up the floor follows the background slowly, but only while the level is below
    +6 dB, so an event cannot raise its own threshold.
  - *Example:* floor 14 RMS -> HIGH about 44, LOW about 28.
- **Sensor-health guard (`ACOUSTIC_MAX_NOISE_FLOOR_RMS` = 40, EXPERIMENTAL bench value).** If the warm-up floor is
  above 40 RMS (noisy/faulty input) or below 1 RMS (flat/stuck input), the node prints `SENSOR FAULT`, keeps the
  ML trigger **disabled until reset**, and hints at the cause from the DC mean (`~4095` = OUT tied to 3V3,
  `~0` = grounded/unpowered). The DC mean is only logged, never used for decisions.
- **Startup report (serial):** `DC mean`, `Noise floor`, `Sensor status = OK|FAULT`, `HIGH`, `LOW`.
- **Debug line** (`-D ACOUSTIC_DEBUG_LOG=1`): `RMS`, `peak`, `crest` (peak/RMS, logged only), `floor`, `dB` above floor.
- **Cooldown:** `ACOUSTIC_COOLDOWN_MS` = 5000 ms after each inference; the trigger re-arms only after the level
  has fallen below LOW and risen again, so a continuing sound cannot retrigger.
- **Fallback modes:** `-D ACOUSTIC_RELATIVE_TRIGGER=0` uses fixed `MAX4466_TRIGGER_HIGH/LOW`
  (**50 / 30, EXPERIMENTAL bench values, not calibrated**); `-D ACOUSTIC_ADAPTIVE=1` (with relative off) is the older
  linear `floor * factor + delta` rule.
- **Every value above is a starting engineering parameter, not a field calibration.** Sustained +6 dB over only
  4 blocks is a loose test and may false-trigger on a noisy input; raise `ACOUSTIC_SUSTAIN_BLOCKS` first if so.

## INMP441 capture

Legacy I2S driver (the only one in this framework version), I2S0 RX, 16 kHz, 32-bit slot, left channel,
6 x 256-sample DMA buffers. Samples are `>> ACOUSTIC_I2S_SHIFT` (16) to PCM16 and written continuously into a
**2 s ring buffer** (`ACOUSTIC_RING_SAMPLES` = 32000, allocated once in PSRAM). On a trigger the pipeline keeps
`ACOUSTIC_PRE_MS` = 250 ms of audio from before the trigger and captures `ACOUSTIC_POST_MS` = 750 ms after it,
forming the 1.000 s window the model was trained on. The shift and slot format are the parts most likely to need
adjusting on real hardware (test mode 2 prints min/max/mean/RMS and warns on all-zero or clipping).

## The model (used exactly as trained)

| | |
|---|---|
| File | `ml/models/final/forest_acoustic_int8.tflite`, 13,072 bytes, 1,315 parameters (embedded by `tools/embed_model.py`) |
| Input | `[1, 40, 101, 1]` INT8, scale 0.014805045910179615, zero point 11 |
| Output | `[1, 3]` INT8 softmax, scale 1/256, zero point -128 (prob = (q+128)/256) |
| Classes | **0 = background, 1 = chainsaw, 2 = gunshot** (`ml/models/final/labels.txt`). The class mapping in `ml/configs/preprocessing.yaml` and `MODEL_HANDOFF.md` is stale and must not be used |
| Ops | CONV_2D, DEPTHWISE_CONV_2D, FULLY_CONNECTED, MAX_POOL_2D, MEAN, SOFTMAX |

The classifier refuses to run unless the loaded model's tensor shapes, types and quantisation match these
constants (`AcousticClassifier::begin`).

### Preprocessing (reproduces `ml/preprocessing/feature_extraction.py`)

1 s PCM16 @ 16 kHz mono -> [optional 80 Hz high-pass] -> peak normalisation -> 512-point STFT (Hann periodic,
hop 160, zero-padded centre) -> power -> 40 Slaney mel bands (0-8 kHz) -> `power_to_db(ref = max of this clip,
top_db = 80)` -> `(dB + 36.3185) / 21.1904` -> INT8. All tables (Hann window, sparse mel filterbank,
normalisation and quantisation constants) are **generated from `ml/`** by `tools/gen_acoustic_tables.py`, which
asserts the `ml/` configuration still matches.

- **High-pass filter: OFF** (`ACOUSTIC_FILTER_ENABLED=0`). The shipped model was trained without it and the A/B
  experiment showed no consistent benefit (`ml/reports/FILTER_REPORT.md`). The biquad is implemented and tested
  against scipy for the case the model is ever retrained with it.
- **Deliberate deviation:** training peak-normalised each *recording* to -3 dBFS; a device has no whole
  recording, so each 1 s *window* is peak-normalised to the same level. Because the dB step is relative to the
  clip's own maximum this is nearly gain-invariant: on 443 real test windows, **0 predictions changed**
  (`tools/gen_acoustic_testvectors.py --sensitivity 200`). Not verified on real microphone audio.

### Kernel fix for TFLite Micro (important)

The model's dense layers use *per-channel* weight quantisation. The stock TFLite Micro `FULLY_CONNECTED` kernel
(both `tanakamasayuki/TensorFlowLite_ESP32` 1.0.0 and `nickjgniklu/ESP_TF` 2.1.1) applies only the first
channel's scale to every output. Measured against Python TFLite on 343 real test-set windows:

| | exact | worst error | class agrees with Python |
|---|---|---|---|
| stock TFLite Micro | 1.2% | 61/256 | 93.6% |
| `AcousticKernels.cpp` (per-channel) | 63.6% | 8/256 | **99.7%** |

The firmware therefore registers `lib/Acoustic/src/AcousticKernels.cpp` in place of the stock op. The model is
unchanged. Reproduce with `tools/tflm_host_parity/run.sh`. The remaining <= 8/256 difference comes from
rounding in the conv/softmax kernels. On the same windows accuracy was 79.0% (Python TFLite), 78.7% (fixed) and
76.1% (stock).

## State machine and tasks

```
MONITORING --RMS >= HIGH--> TRIGGERED --> CAPTURE --> INFERENCE --> RESULT --> COOLDOWN --> MONITORING
```

All acoustic work runs in FreeRTOS tasks on core 0 (`ac-capture`, `ac-trigger`, `ac-infer`, 16 KB stack); the
Arduino `loop()` (RC522 + LoRa) stays on core 1 and is never blocked by DSP or inference. **Only `loop()` touches
SPI/LoRa** (the RC522 and SX1278 share one re-pinned SPI bus), so the pipeline hands finished events to `loop()`
through a queue. Background predictions create no event. Nothing is allocated per event.

## LoRa event and backend path

Compact 6-byte payload inside the existing DATA packet (existing header, sequence and CRC; no raw audio):
`'A'(0x41), version 0x01, class (1 chainsaw / 2 gunshot), confidence u8 (p*255), trigger RMS u16 LE`.

Gateway -> MQTT topic `forest/events/acoustic` (JSON: node_id, sequence, classification, confidence,
model_version, trigger_rms, gateway meta) -> backend `POST /api/ingest/gateway/acoustic-node-event`.

**These events are UNSIGNED.** The node has no RTC, signing key or hash chain (the "existing signature
mechanism" is not implemented on the node; see `GATEWAY_BACKEND_CONTRACT.md`). The backend stamps the receive
time, stores `signature_status = chain_status = PENDING`, and the event enters the normal human-review queue
(`PENDING_REVIEW`); the dashboard labels it "UNSIGNED (pending review)". Retries are recognised by
(node, node-sequence, class) within 120 s; the node's sequence restarts at 0 on reboot, so the backend assigns its
own per-node sequence and the existing unique (node_id, sequence) constraint of the signed path is untouched.
The node must be registered (`NODE_01`, ACTIVE). Because the backend runs on Vercel (no persistent MQTT
subscriber), add an EMQX rule: `forest/events/acoustic` -> POST
`https://<backend>/api/ingest/gateway/acoustic-node-event` (body `${payload}`).

## Test modes (`-D FOREST_ACOUSTIC_TEST_MODE=n`)

| n | What it does | Needs |
|---|---|---|
| 0 | Full pipeline (default) | both mics |
| 1 | Prints MAX4466 RMS / DC / min / max and TRIGGER/release edges every 0.5 s | MAX4466 |
| 2 | Prints INMP441 min / max / mean / RMS every 0.5 s; warns on all-zero or clipping | INMP441 |
| 3 | Runs 3 known INT8 tensors through TFLite Micro and compares with the Python reference, then runs the on-device preprocessing on a real gunshot PCM window and compares with the `ml/` tensor | **nothing** |

Enable verbose per-block logging with `-D ACOUSTIC_DEBUG_LOG=1`.

## Resources

| | |
|---|---|
| Model in flash | 13,072 bytes |
| Firmware flash | 416,693 B (acoustic env) vs 292,097 B (RFID env) of a 3,342,336 B app partition |
| Static RAM | 19,324 B vs 19,024 B |
| TFLM tensor arena | 65,536 B allocated; **26,804 B used** (measured on the device before the custom kernel was added) |
| Ring buffer / window / preprocessor | 64,000 B + 32,000 B + ~23 KB, allocated once in PSRAM |
| Feature extraction latency | **69.7 ms** for 1 s of audio (measured on the device) |
| TFLM `Invoke()` latency | **~268 ms** (measured on the device with the stock reference kernels; not re-measured with the custom FC kernel) |

## Host tests (no hardware)

```bash
node-firmware/test/run_acoustic_tests.sh        # trigger/hysteresis/ring + device-vs-librosa parity
node-firmware/tools/tflm_host_parity/run.sh     # TFLite Micro (stock vs fixed) vs Python TFLite
```

The parity test compares the device preprocessing with librosa on real windows: dB features within 5e-5 dB and
**identical INT8 tensors** (negative controls with deliberately broken code fail as they should).

## Validation status

| Item | Status |
|---|---|
| RC522 + SX1278 still initialise with the acoustic firmware | **PHYSICALLY VERIFIED** (boot log; not a card read / LoRa transmission) |
| TFLite Micro loads the model and passes the tensor checks | **PHYSICALLY VERIFIED** |
| On-device preprocessing vs `ml/` features on a real gunshot window | **PHYSICALLY VERIFIED** (4040/4040 elements identical) |
| Stock TFLM output vs Python reference | **PHYSICALLY VERIFIED as WRONG** (class agreed, probabilities not) -> fixed |
| Per-channel FC kernel vs Python (host) | **TESTED on host** (343 windows) |
| Per-channel FC kernel on the ESP32 (test mode 3, 3 known windows) | **PHYSICALLY VERIFIED**: max output diff 3/256 vs Python, all classes agree; `Invoke()` ~268 ms, features ~70 ms |
| MAX4466 ADC + trigger | **UNDER VALIDATION**: hardware problem, see "Bench findings" below. Thresholds NOT calibrated |
| INMP441 I2S capture | **PARTIALLY VERIFIED**: I2S delivers varying, non-clipping, non-zero samples; speech-vs-quiet separation, sample rate and I2S shift **NOT verified** |
| One full trigger -> capture -> inference -> cooldown cycle on the board | **PHYSICALLY VERIFIED** as a state machine only (fired on noise; result background 0.47); not a detection test |
| Relative-dB trigger + sensor-health guard | IMPLEMENTED, host-tested. **Guard physically verified once**: it flagged a stuck-at-rail input (DC 4095, floor 0) and disabled ML. Good-signal behaviour on hardware **NOT verified** |
| Trigger/ring logic | TESTED (host unit tests) |
| Backend unsigned ingest, gateway 'A' branch, MQTT dispatch | TESTED (backend tests, real Postgres concurrency); gateway BUILT only |
| Acoustic event over real LoRa -> gateway -> backend | NOT verified end-to-end |
| Classification accuracy on real microphone / forest audio | **UNVERIFIED.** The model has never seen INMP441 audio |

**Model quality caveat (from `ml/reports`):** test macro-F1 is about 0.57 and chainsaw/gunshot precision only
0.35 / 0.27, so expect many false alarms; the domain gap to real forests is rated significant. Raise
`ACOUSTIC_MIN_CONFIDENCE` (default 0.0 = every gunshot/chainsaw prediction becomes an event) once field data exists.

## Bench findings (MAX4466 wiring/power) - open issue

Measured on the node board, 8 kHz, 128-sample blocks, gain trimmer turned down:

| State | RMS avg | RMS peak/block | DC mean (ADC counts) |
|---|---|---|---|
| First run, trimmer at default | ~148 (steady) | ~172-177 | ~400 |
| Clap, same run | 155-190 | 300-420 | ~400 |
| After gain + supply change, quiet (good state) | **~14** | ~20-34 | ~135 |
| Same session, intermittent noisy state (no sound) | ~105-160 | 175-400 | 200-760 |
| Latest run (after re-wiring) | 0.0 | 0 | **4095 (stuck at ADC top)** |

Conclusions: an independent `analogRead(GPIO1)` sketch showed the same fault, so it is not the DMA sampler. A
healthy MAX4466 idles near VCC/2 (~1.65 V, ~2000 counts); this one idled near 135 counts, toggled between a
~14 and a ~110-150 RMS state, and finally stuck at the rail. Both mics share 3V3/GND and the INMP441 baseline was
also noisy, so a shared supply/ground or a bad contact is the prime suspect. **Fix the hardware before
calibrating.** Checklist: fresh short jumpers (off the breadboard), OUT -> GPIO1 only, VCC -> 3V3, GND -> GND,
10 uF + 100 nF across the mic supply, mic wiring away from the SX1278/antenna, trimmer counter-clockwise then
~1/4 turn. The firmware now reports the outcome itself at boot (`Sensor status` / `SENSOR FAULT`).

## Hardware acceptance procedure

1. Flash the RFID env: RC522 reads a card, LoRa transmits, LED works.
2. Flash the acoustic env with test mode 3: expect `[TEST3] RESULT: PASS`.
3. Wire the MAX4466, reset in a quiet room: expect `Sensor status = OK` and a small stable floor; clap and
   confirm a trigger (debug build: `-D ACOUSTIC_DEBUG_LOG=1`). Test mode 1 prints raw RMS.
4. Wire the INMP441, test mode 2: sensible min/max/mean/RMS; not all-zero; not clipping (tune `ACOUSTIC_I2S_SHIFT`).
5. Full pipeline (mode 0): clap or play a recording; expect the log sequence `Trigger detected -> Capturing audio
   -> Running inference -> [ML] class=... -> Event generated -> Cooldown -> Monitoring`.
6. Confirm `ACOUSTIC EVENT RECEIVED` on the gateway and the event on the dashboard (needs the EMQX rule).
7. Re-check RFID scans still work with the acoustic tasks running.
8. Record known chainsaw / gunshot / background sounds through the INMP441 and measure the classification.
