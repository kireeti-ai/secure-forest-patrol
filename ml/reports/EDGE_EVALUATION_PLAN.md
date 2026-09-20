# Edge Evaluation Plan

## Overview

This document outlines the comprehensive edge deployment evaluation strategy for the SECURE FOREST PATROL acoustic classification system on ESP32-S3 hardware. Edge evaluation is critical for validating that models can actually run on target hardware within real-world constraints.

---

## Target Hardware Specifications

### ESP32-S3 Specifications
- **CPU:** Dual-core Xtensa LX7 microprocessor
- **Clock Speed:** Up to 240 MHz
- **Memory:** 512 KB SRAM, 8 MB PSRAM (optional)
- **Storage:** Flash memory (varies by board)
- **Architecture:** 32-bit RISC
- **Power:** Typically 150-300 mW active power

### Deployment Constraints
- **Memory Limit:** ~400 KB available for model and inference (leaving ~100 KB for system)
- **Power Budget:** Battery-powered operation (days to months)
- **Latency Requirement:** Real-time classification (< 500 ms end-to-end)
- **Connectivity:** Limited/intermittent (LoRa, WiFi, cellular)
- **Environment:** Outdoor, variable temperature, weather exposure

### Target Microphone
- **Model:** INMP441 I2S MEMS microphone
- **Sample Rate:** 16 kHz
- **Bit Depth:** 16-bit
- **Channels:** Mono
- **Interface:** I2S digital interface
- **Power:** Low power operation

---

## Model Quality Evaluation

### Primary Model Quality Metrics

**Macro-F1 Score:**
- **FP32 Model:** Macro-F1 ≥ 0.80
- **INT8 Model:** Macro-F1 ≥ 0.78 (≤ 2.5% drop)
- **Target:** Maintain high accuracy while meeting edge constraints

**Per-Class F1 Score:**
- **Gunshot FP32:** F1 ≥ 0.87
- **Gunshot INT8:** F1 ≥ 0.85 (≤ 2.3% drop)
- **Chainsaw FP32:** F1 ≥ 0.82
- **Chainsaw INT8:** F1 ≥ 0.80 (≤ 2.4% drop)
- **Background FP32:** F1 ≥ 0.65
- **Background INT8:** F1 ≥ 0.63 (≤ 3.1% drop)

**Precision and Recall:**
- **Gunshot Precision:** ≥ 0.85 (FP32), ≥ 0.83 (INT8)
- **Gunshot Recall:** ≥ 0.90 (FP32), ≥ 0.88 (INT8)
- **Chainsaw Precision:** ≥ 0.80 (FP32), ≥ 0.78 (INT8)
- **Chainsaw Recall:** ≥ 0.85 (FP32), ≥ 0.83 (INT8)

### Edge-Specific Quality Metrics

**Real-Time Performance:**
- **Classification Latency:** ≤ 200 ms end-to-end
- **Throughput:** ≥ 5 classifications per second
- **Jitter:** ≤ 50 ms latency variation

**Robustness Metrics:**
- **Temperature Range:** -20°C to +60°C operation
- **Power Variation:** Stable performance across voltage range
- **Memory Stability:** No memory leaks over extended operation

---

## Model Size Evaluation

### Parameter Count Analysis

**Metrics:**
- **Total Parameters:** Count of all model parameters
- **Trainable Parameters:** Parameters that are trained
- **Fixed Parameters:** Parameters that are fixed (e.g., batch norm)
- **Parameter Distribution:** Parameters per layer

**Targets:**
- **Total Parameters:** ≤ 100,000 parameters
- **Trainable Parameters:** ≤ 80,000 parameters
- **Parameter Distribution:** Balanced across layers

**Measurement:**
```python
import tensorflow as tf

model = tf.keras.models.load_model('model.h5')
total_params = model.count_params()
trainable_params = sum([tf.size(w).numpy() for w in model.trainable_weights])
```

### Model File Size Analysis

**FP32 Model Size:**
- **TFLite File Size:** Size of .tflite file
- **FlatBuffer Size:** Size of FlatBuffer representation
- **Metadata Size:** Size of model metadata
- **Total Size:** Complete model size

**INT8 Model Size:**
- **TFLite File Size:** Size of quantized .tflite file
- **Compression Ratio:** FP32 size / INT8 size
- **Size Reduction:** (FP32 - INT8) / FP32

**Targets:**
- **FP32 TFLite Size:** ≤ 500 KB
- **INT8 TFLite Size:** ≤ 250 KB
- **Compression Ratio:** ≥ 2.0x
- **Size Reduction:** ≥ 50%

**Measurement:**
```python
import os

fp32_size = os.path.getsize('model_fp32.tflite')
int8_size = os.path.getsize('model_int8.tflite')
compression_ratio = fp32_size / int8_size
size_reduction = (fp32_size - int8_size) / fp32_size
```

### Weight Size Analysis

**Metrics:**
- **Weight Size:** Size of model weights only
- **Bias Size:** Size of bias terms
- **Activation Size:** Size of activation functions
- **Total Storage:** Complete storage requirements

**Targets:**
- **Weight Size:** ≤ 400 KB (FP32), ≤ 200 KB (INT8)
- **Bias Size:** ≤ 50 KB (FP32), ≤ 25 KB (INT8)
- **Activation Size:** ≤ 50 KB (FP32), ≤ 25 KB (INT8)

---

## Memory Evaluation

### Static Memory Analysis

**Metrics:**
- **Model Code Size:** Size of inference code
- **Model Data Size:** Size of model weights and constants
- **Interpreter Overhead:** TFLite Micro interpreter overhead
- **Total Static Memory:** Complete static memory footprint

**Targets:**
- **Model Code Size:** ≤ 50 KB
- **Model Data Size:** ≤ 200 KB (FP32), ≤ 100 KB (INT8)
- **Interpreter Overhead:** ≤ 20 KB
- **Total Static Memory:** ≤ 270 KB (FP32), ≤ 170 KB (INT8)

**Measurement:**
```cpp
// ESP32-S3 memory measurement
#include "esp_heap_caps.h"

size_t free_heap = heap_caps_get_free_size(MALLOC_CAP_DEFAULT);
size_t total_heap = heap_caps_get_total_size(MALLOC_CAP_DEFAULT);
```

### Runtime Memory Analysis

**Metrics:**
- **Tensor Arena Size:** Size of tensor arena for intermediate activations
- **Peak Runtime Memory:** Peak memory during inference
- **Activation Memory:** Memory for intermediate activations
- **Temporary Memory:** Temporary memory during operations

**Targets:**
- **Tensor Arena Size:** ≤ 250 KB
- **Peak Runtime Memory:** ≤ 300 KB
- **Activation Memory:** ≤ 100 KB
- **Temporary Memory:** ≤ 50 KB

**Measurement:**
```cpp
// Measure peak memory during inference
size_t heap_before = heap_caps_get_free_size(MALLOC_CAP_DEFAULT);
// Run inference
size_t heap_after = heap_caps_get_free_size(MALLOC_CAP_DEFAULT);
size_t peak_memory = heap_before - heap_after;
```

### Memory Profile Analysis

**Memory Usage Pattern:**
- **Initialization Memory:** Memory during model loading
- **Inference Memory:** Memory during inference
- **Post-Inference Memory:** Memory after inference completion
- **Memory Leak Detection:** Monitor memory over extended operation

**Measurement Protocol:**
1. Measure free heap before model loading
2. Measure free heap after model loading
3. Measure free heap before inference
4. Measure free heap during inference (peak)
5. Measure free heap after inference
6. Repeat for 100+ inferences to detect leaks

**Targets:**
- **Initialization Memory:** ≤ 300 KB
- **Inference Memory:** ≤ 350 KB
- **Memory Leak:** ≤ 1 KB per 1000 inferences

---

## Latency Evaluation

### Component Latency Breakdown

**End-to-End Pipeline:**
1. **Audio Capture:** 62.5 ms (1 second @ 16 kHz)
2. **Preprocessing:** Resampling, normalization, windowing
3. **Feature Extraction:** MFCC or Mel-spectrogram computation
4. **Model Inference:** Neural network forward pass
5. **Post-Processing:** Output processing, thresholding
6. **Total Latency:** Sum of all components

**Targets:**
- **Audio Capture:** 62.5 ms (fixed by sample rate)
- **Preprocessing:** ≤ 30 ms
- **Feature Extraction:** ≤ 50 ms
- **Model Inference:** ≤ 100 ms
- **Post-Processing:** ≤ 20 ms
- **Total Latency:** ≤ 262.5 ms

### Inference Latency Measurement

**Metrics:**
- **Cold Start Latency:** First inference after model loading
- **Warm Inference Latency:** Average inference after warm-up
- **Worst-Case Latency:** Maximum observed latency
- **Latency Jitter:** Standard deviation of latency

**Targets:**
- **Cold Start Latency:** ≤ 150 ms
- **Warm Inference Latency:** ≤ 100 ms
- **Worst-Case Latency:** ≤ 200 ms
- **Latency Jitter:** ≤ 20 ms

**Measurement Protocol:**
```cpp
#include "esp_timer.h"

// Measure inference latency
uint64_t start = esp_timer_get_time();
// Run inference
uint64_t end = esp_timer_get_time();
uint64_t latency_us = end - start;
float latency_ms = latency_us / 1000.0;
```

### Latency Profiling

**Per-Layer Latency:**
- **Convolutional Layers:** Latency per conv layer
- **Pooling Layers:** Latency per pooling layer
- **Fully Connected Layers:** Latency per FC layer
- **Activation Functions:** Latency per activation

**Measurement:**
- Add timing instrumentation to each layer
- Profile 100+ inferences
- Calculate average and variance per layer
- Identify bottleneck layers

**Targets:**
- **No Single Layer:** > 20 ms latency
- **Balanced Distribution:** Latency distributed across layers
- **Optimization Targets:** Layers > 15 ms marked for optimization

---

## Quantization Evaluation

### Quantization Accuracy Impact

**Metrics:**
- **FP32 Macro-F1:** Macro-F1 with FP32 model
- **INT8 Macro-F1:** Macro-F1 with INT8 quantized model
- **Accuracy Drop:** FP32 Macro-F1 - INT8 Macro-F1
- **Per-Class Accuracy Drop:** Per-class accuracy differences

**Targets:**
- **FP32 Macro-F1:** ≥ 0.80
- **INT8 Macro-F1:** ≥ 0.78
- **Accuracy Drop:** ≤ 2.5%
- **Per-Class Drop:** ≤ 3% for any class

**Measurement Protocol:**
1. Train FP32 model and evaluate on test set
2. Quantize to INT8 using representative dataset
3. Evaluate INT8 model on same test set
4. Compare metrics and identify degradation patterns

### Quantization Performance Impact

**Metrics:**
- **FP32 Latency:** Inference latency with FP32 model
- **INT8 Latency:** Inference latency with INT8 model
- **Latency Improvement:** (FP32 Latency - INT8 Latency) / FP32 Latency
- **FP32 Memory:** Memory usage with FP32 model
- **INT8 Memory:** Memory usage with INT8 model
- **Memory Improvement:** (FP32 Memory - INT8 Memory) / FP32 Memory

**Targets:**
- **FP32 Latency:** ≤ 150 ms
- **INT8 Latency:** ≤ 100 ms
- **Latency Improvement:** ≥ 30%
- **FP32 Memory:** ≤ 350 KB
- **INT8 Memory:** ≤ 250 KB
- **Memory Improvement:** ≥ 25%

### Quantization Calibration

**Representative Dataset:**
- **Size:** 100-500 representative samples
- **Diversity:** Cover all classes and conditions
- **Calibration Method:** Min-max calibration or entropy calibration
- **Validation:** Validate calibration on held-out set

**Calibration Protocol:**
1. Select representative dataset from training data
2. Run calibration process
3. Validate on separate calibration validation set
4. Iterate if calibration quality insufficient

**Targets:**
- **Calibration Dataset:** 200+ representative samples
- **Calibration Validation:** ≤ 1% accuracy drop on validation set
- **Final Accuracy:** Meet INT8 accuracy targets

---

## Power Evaluation

### Power Consumption Measurement

**Metrics:**
- **Idle Power:** Power consumption when idle
- **Inference Power:** Power consumption during inference
- **Peak Power:** Peak power consumption
- **Average Power:** Average power over operation

**Targets:**
- **Idle Power:** ≤ 50 mW
- **Inference Power:** ≤ 300 mW
- **Peak Power:** ≤ 350 mW
- **Average Power:** ≤ 100 mW (assuming 10% duty cycle)

**Measurement Protocol:**
- Use power meter or current measurement
- Measure power during different operation modes
- Calculate average power over realistic duty cycle
- Validate against battery life requirements

### Energy per Inference

**Metrics:**
- **Energy per Inference:** Energy consumed per inference
- **Inferences per Battery:** Number of inferences per battery charge
- **Battery Life:** Expected battery life at given duty cycle

**Targets:**
- **Energy per Inference:** ≤ 30 mJ
- **Inferences per Battery:** ≥ 100,000 (assuming 3Wh battery)
- **Battery Life:** ≥ 30 days (assuming 10% duty cycle)

**Calculation:**
```
Energy per Inference = Power × Latency
Battery Life = Battery Capacity / (Power × Duty Cycle)
```

---

## Temperature Evaluation

### Operating Temperature Range

**Metrics:**
- **Cold Start Performance:** Performance at -20°C
- **Room Temperature Performance:** Performance at 25°C
- **Hot Operation Performance:** Performance at 60°C
- **Performance Variation:** Performance change across temperature range

**Targets:**
- **Cold Start Performance:** Macro-F1 ≥ 0.75
- **Room Temperature Performance:** Macro-F1 ≥ 0.80
- **Hot Operation Performance:** Macro-F1 ≥ 0.75
- **Performance Variation:** ≤ 10% across temperature range

**Measurement Protocol:**
- Test in environmental chamber or equivalent
- Measure performance at -20°C, 0°C, 25°C, 40°C, 60°C
- Monitor for thermal throttling or shutdown
- Validate performance across full range

### Thermal Management

**Metrics:**
- **Temperature Rise:** Temperature increase during operation
- **Cooling Time:** Time to return to ambient temperature
- **Thermal Throttling:** Occurrence and impact of thermal throttling
- **Heat Dissipation:** Effectiveness of heat dissipation

**Targets:**
- **Temperature Rise:** ≤ 15°C during continuous operation
- **Cooling Time:** ≤ 5 minutes to return to ambient
- **Thermal Throttling:** No thermal throttling in normal operation
- **Heat Dissipation:** Adequate for target environment

---

## Reliability Evaluation

### Long-Term Stability

**Metrics:**
- **Stability Duration:** Continuous operation duration
- **Performance Degradation:** Performance change over time
- **Memory Stability:** Memory usage stability over time
- **Error Rate:** Error rate over extended operation

**Targets:**
- **Stability Duration:** ≥ 7 days continuous operation
- **Performance Degradation:** ≤ 5% over 7 days
- **Memory Stability:** No memory leaks over 7 days
- **Error Rate:** ≤ 0.1% error rate over 7 days

**Measurement Protocol:**
- Run continuous operation for 7+ days
- Monitor performance metrics continuously
- Check for memory leaks and degradation
- Log any errors or failures

### Fault Tolerance

**Metrics:**
- **Recovery from Errors:** Ability to recover from errors
- **Graceful Degradation:** Performance under fault conditions
- **Error Detection:** Ability to detect errors
- **Error Reporting:** Ability to report errors

**Targets:**
- **Recovery from Errors:** 100% recovery from non-fatal errors
- **Graceful Degradation:** Macro-F1 ≥ 0.60 under fault conditions
- **Error Detection:** 95% error detection rate
- **Error Reporting:** 100% error reporting for detected errors

---

## Deployment Readiness Checklist

### Model Readiness
- [ ] Model accuracy meets targets (Macro-F1 ≥ 0.80)
- [ ] Quantization accuracy drop ≤ 2.5%
- [ ] Model size ≤ 500 KB (FP32), ≤ 250 KB (INT8)
- [ ] Parameter count ≤ 100,000

### Memory Readiness
- [ ] Static memory ≤ 270 KB (FP32), ≤ 170 KB (INT8)
- [ ] Peak runtime memory ≤ 300 KB
- [ ] Tensor arena size ≤ 250 KB
- [ ] Free heap after allocation ≥ 100 KB

### Latency Readiness
- [ ] End-to-end latency ≤ 262.5 ms
- [ ] Inference latency ≤ 100 ms
- [ ] Latency jitter ≤ 20 ms
- [ ] Cold start latency ≤ 150 ms

### Power Readiness
- [ ] Idle power ≤ 50 mW
- [ ] Inference power ≤ 300 mW
- [ ] Energy per inference ≤ 30 mJ
- [ ] Battery life ≥ 30 days

### Reliability Readiness
- [ ] 7-day continuous operation stable
- [ ] No memory leaks over extended operation
- [ ] Performance degradation ≤ 5% over 7 days
- [ ] Error rate ≤ 0.1% over extended operation

### Environmental Readiness
- [ ] Operating temperature range -20°C to +60°C
- [ ] Performance variation ≤ 10% across temperature range
- [ ] No thermal throttling in normal operation
- [ ] Weatherproof enclosure validated

---

## Evaluation Protocol

### Benchmark Suite

**Standard Benchmark:**
1. Load model onto ESP32-S3
2. Run 1000 inference cycles
3. Measure latency, memory, power for each cycle
4. Calculate statistics (mean, std, min, max)
5. Validate against targets

**Stress Benchmark:**
1. Run continuous operation for 24 hours
2. Monitor for degradation, memory leaks, errors
3. Measure performance over time
4. Validate stability and reliability

**Environmental Benchmark:**
1. Test at -20°C, 0°C, 25°C, 40°C, 60°C
2. Measure performance at each temperature
3. Validate thermal management
4. Check for thermal throttling

### Reporting Standards

**Required Reports:**
1. **Model Quality Report:** Accuracy, precision, recall, F1
2. **Model Size Report:** Parameter count, file size, weight size
3. **Memory Report:** Static memory, runtime memory, memory profile
4. **Latency Report:** Component latency, inference latency, jitter
5. **Quantization Report:** Accuracy impact, performance impact, calibration
6. **Power Report:** Power consumption, energy per inference, battery life
7. **Temperature Report:** Temperature range, performance variation, thermal management
8. **Reliability Report:** Long-term stability, fault tolerance, error rate

**Visualization Requirements:**
1. **Memory Profile:** Memory usage over time
2. **Latency Distribution:** Latency histogram and box plot
3. **Power Profile:** Power consumption over time
4. **Temperature Profile:** Temperature vs performance
5. **Stability Plot:** Performance over extended operation

---

## Success Criteria

### Minimum Viable Dataset Success
- [ ] Model loads successfully on ESP32-S3
- [ ] Basic inference functional
- [ ] Memory usage within ESP32-S3 limits
- [ ] Latency < 500 ms
- [ ] No memory leaks over 1 hour operation

### Target Research Dataset Success
- [ ] Model accuracy ≥ 0.75 Macro-F1 on device
- [ ] Quantization accuracy drop ≤ 5%
- [ ] Model size ≤ 500 KB
- [ ] Memory usage ≤ 350 KB peak
- [ ] Latency ≤ 300 ms
- [ ] Power consumption ≤ 350 mW
- [ ] 24-hour stable operation

### Ideal Dataset Success
- [ ] Model accuracy ≥ 0.80 Macro-F1 on device
- [ ] Quantization accuracy drop ≤ 2.5%
- [ ] Model size ≤ 250 KB (INT8)
- [ ] Memory usage ≤ 300 KB peak
- [ ] Latency ≤ 200 ms
- [ ] Power consumption ≤ 300 mW
- [ ] Battery life ≥ 30 days
- [ ] 7-day stable operation
- [ ] Full temperature range validated

---

## Next Steps

### Immediate Actions (Week 1)
1. **Set up ESP32-S3 development environment**
2. **Implement basic TFLite Micro inference**
3. **Create memory and latency measurement framework**
4. **Load initial model and test basic functionality**

### Short-term Actions (Weeks 2-4)
1. **Implement comprehensive benchmark suite**
2. **Measure baseline model performance**
3. **Test quantization pipeline**
4. **Optimize model for edge deployment**

### Medium-term Actions (Months 2-3)
1. **Complete full edge evaluation**
2. **Validate against all targets**
3. **Test environmental robustness**
4. **Validate long-term reliability**

---

**Document Version:** 1.0
**Last Updated:** 2026-09-19
**Status:** Research Phase - Edge Evaluation Planning
**Next Step:** Set up ESP32-S3 development environment and implement basic inference