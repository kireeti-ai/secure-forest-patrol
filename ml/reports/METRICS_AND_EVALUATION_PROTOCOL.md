# Metrics and Evaluation Protocol

## Overview

This document defines the comprehensive evaluation metrics and protocols for the SECURE FOREST PATROL acoustic classification system. The protocol ensures rigorous, defensible evaluation that supports research-grade conclusions and reliable edge deployment claims.

---

## Evaluation Philosophy

### Core Principles

1. **Multi-Metric Evaluation:** No single metric tells the complete story
2. **Class-Specific Analysis:** Per-class metrics reveal model behavior
3. **Robustness Focus:** Evaluate under realistic, challenging conditions
4. **Deployment Relevance:** Metrics must reflect operational requirements
5. **Statistical Rigor:** Use appropriate statistical methods and confidence intervals

### Evaluation Goals

- **Accuracy Assessment:** Measure overall classification performance
- **Class Balance:** Evaluate performance across all classes
- **Robustness:** Assess performance under varied conditions
- **Generalization:** Test cross-dataset and cross-environment performance
- **Deployment Readiness:** Validate edge deployment feasibility

---

## Primary Classification Metrics

### Macro F1-Score

**Definition:** Harmonic mean of precision and recall, computed per-class then averaged

**Formula:**
```
Macro-F1 = (1/C) * Σ(F1_c) for c in classes
F1_c = 2 * (Precision_c * Recall_c) / (Precision_c + Recall_c)
```

**Rationale:**
- Balances precision and recall
- Treats all classes equally (important for imbalanced datasets)
- Standard metric in environmental sound classification literature
- Reflects real-world operational needs (detecting rare threats)

**Target:**
- Minimum Viable Dataset: Macro-F1 ≥ 0.70
- Target Research Dataset: Macro-F1 ≥ 0.80
- Ideal Dataset: Macro-F1 ≥ 0.85

### Per-Class Precision

**Definition:** Proportion of positive predictions that are truly positive for each class

**Formula:**
```
Precision_c = TP_c / (TP_c + FP_c)
```

**Per-Class Targets:**
- **Gunshot:** Precision ≥ 0.85 (high cost of false alarms)
- **Chainsaw:** Precision ≥ 0.80 (high cost of false alarms)
- **Background:** Precision ≥ 0.70 (acceptable higher false positive rate)

**Rationale:**
- False alarms for threats (gunshot/chainsaw) have high operational cost
- False positives for background are less critical but still impact efficiency
- Different thresholds reflect operational priorities

### Per-Class Recall

**Definition:** Proportion of actual positives that are correctly identified for each class

**Formula:**
```
Recall_c = TP_c / (TP_c + FN_c)
```

**Per-Class Targets:**
- **Gunshot:** Recall ≥ 0.90 (critical to detect threats)
- **Chainsaw:** Recall ≥ 0.85 (critical to detect threats)
- **Background:** Recall ≥ 0.60 (some background misclassification acceptable)

**Rationale:**
- Missing threats (false negatives) has high safety cost
- Background detection is less critical but still important for efficiency
- Different thresholds reflect safety priorities

### Per-Class F1-Score

**Definition:** Harmonic mean of precision and recall for each class

**Formula:**
```
F1_c = 2 * (Precision_c * Recall_c) / (Precision_c + Recall_c)
```

**Per-Class Targets:**
- **Gunshot:** F1 ≥ 0.87
- **Chainsaw:** F1 ≥ 0.82
- **Background:** F1 ≥ 0.65

**Rationale:**
- Single metric balancing precision and recall per class
- Allows comparison of class-specific performance
- Identifies classes needing improvement

### Balanced Accuracy

**Definition:** Average of recall rates across all classes

**Formula:**
```
Balanced Accuracy = (1/C) * Σ(Recall_c) for c in classes
```

**Target:**
- Minimum Viable Dataset: Balanced Accuracy ≥ 0.75
- Target Research Dataset: Balanced Accuracy ≥ 0.82
- Ideal Dataset: Balanced Accuracy ≥ 0.88

**Rationale:**
- Accounts for class imbalance
- Treats all classes equally
- Complements Macro-F1 for different perspective

### Confusion Matrix

**Definition:** Matrix showing actual vs predicted class distribution

**Format:**
```
              Predicted
              Gunshot  Chainsaw  Background
Actual Gunshot   TP_G    FP_GC     FP_GB
Actual Chainsaw  FP_CG    TP_C     FP_CB
Actual Background FP_BG   FP_BC     TP_B
```

**Analysis:**
- **Diagonal:** Correct classifications (TP for each class)
- **Off-diagonal:** Confusion between classes
- **Row sums:** Actual class distribution
- **Column sums:** Predicted class distribution

**Rationale:**
- Reveals specific confusion patterns
- Identifies which classes are most confused
- Guides targeted improvements

---

## Secondary Classification Metrics

### Precision-Recall AUC (PR-AUC)

**Definition:** Area under the precision-recall curve

**Formula:**
```
PR-AUC = ∫(Precision(Recall)) dRecall
```

**Per-Class Targets:**
- **Gunshot:** PR-AUC ≥ 0.90
- **Chainsaw:** PR-AUC ≥ 0.85
- **Background:** PR-AUC ≥ 0.75

**Rationale:**
- More informative than ROC-AUC for imbalanced datasets
- Focuses on positive class performance
- Threshold-independent performance measure

### Receiver Operating Characteristic AUC (ROC-AUC)

**Definition:** Area under the ROC curve (TPR vs FPR)

**Formula:**
```
ROC-AUC = ∫(TPR(FPR)) dFPR
```

**Per-Class Targets:**
- **Gunshot:** ROC-AUC ≥ 0.92
- **Chainsaw:** ROC-AUC ≥ 0.88
- **Background:** ROC-AUC ≥ 0.80

**Rationale:**
- Threshold-independent performance measure
- Standard metric in classification literature
- Complements PR-AUC for different perspective

### Overall Accuracy

**Definition:** Proportion of correct predictions across all classes

**Formula:**
```
Accuracy = (TP_G + TP_C + TP_B) / Total Samples
```

**Target:**
- Minimum Viable Dataset: Accuracy ≥ 0.75
- Target Research Dataset: Accuracy ≥ 0.82
- Ideal Dataset: Accuracy ≥ 0.88

**Rationale:**
- Simple, intuitive metric
- Commonly reported in literature
- Should be interpreted with caution for imbalanced datasets

**Note:** Report accuracy but do not rely on it as primary metric due to potential class imbalance.

---

## False Alarm Metrics

### False Positive Rate (FPR)

**Definition:** Proportion of actual negatives incorrectly classified as positive

**Formula:**
```
FPR_c = FP_c / (FP_c + TN_c)
```

**Per-Class Targets:**
- **Gunshot FPR:** ≤ 0.05 (5% false alarm rate)
- **Chainsaw FPR:** ≤ 0.08 (8% false alarm rate)
- **Background FPR:** ≤ 0.15 (15% false alarm rate)

**Rationale:**
- Critical for safety-oriented systems
- High false alarms reduce operator trust
- Different thresholds reflect operational impact

### False Discovery Rate (FDR)

**Definition:** Proportion of positive predictions that are false positives

**Formula:**
```
FDR_c = FP_c / (TP_c + FP_c) = 1 - Precision_c
```

**Per-Class Targets:**
- **Gunshot FDR:** ≤ 0.15 (15% of gunshot alarms are false)
- **Chainsaw FDR:** ≤ 0.20 (20% of chainsaw alarms are false)
- **Background FDR:** ≤ 0.30 (30% of background alarms are false)

**Rationale:**
- Reflects operational cost of false alarms
- Directly relates to operator workload
- Helps set operational thresholds

### False Alarms Per Hour

**Definition:** Expected number of false alarms per hour of operation

**Formula:**
```
False Alarms/Hour = FPR * Evaluation Samples / Total Evaluation Duration
```

**Target:**
- **Gunshot:** ≤ 1 false alarm per 24 hours
- **Chainsaw:** ≤ 2 false alarms per 24 hours
- **Background:** ≤ 5 false alarms per 24 hours

**Rationale:**
- Direct operational metric
- Reflects real-world deployment impact
- Guides threshold tuning for deployment

---

## Confusion-Specific Metrics

### Gunshot Confusion Analysis

**Key Confusions to Monitor:**
- **Gunshot → Chainsaw:** How often gunshots misclassified as chainsaws
- **Gunshot → Background:** How often gunshots missed entirely
- **Chainsaw → Gunshot:** How often chainsaws misclassified as gunshots
- **Background → Gunshot:** How often background triggers false gunshot alarms

**Analysis:**
- **Gunshot → Chainsaw Confusion Rate:** FP_GC / (TP_G + FP_GC)
- **Gunshot Miss Rate:** FN_GB / (TP_G + FN_GB)
- **Chainsaw → Gunshot Confusion Rate:** FP_CG / (TP_C + FP_CG)
- **Background → Gunshot False Alarm Rate:** FP_BG / (TP_B + FP_BG)

**Targets:**
- **Gunshot → Chainsaw:** ≤ 10%
- **Gunshot Miss Rate:** ≤ 10%
- **Chainsaw → Gunshot:** ≤ 15%
- **Background → Gunshot:** ≤ 5%

### Chainsaw Confusion Analysis

**Key Confusions to Monitor:**
- **Chainsaw → Gunshot:** How often chainsaws misclassified as gunshots
- **Chainsaw → Background:** How often chainsaws missed entirely
- **Gunshot → Chainsaw:** How often gunshots misclassified as chainsaws
- **Background → Chainsaw:** How often background triggers false chainsaw alarms

**Analysis:**
- **Chainsaw → Gunshot Confusion Rate:** FP_CG / (TP_C + FP_CG)
- **Chainsaw Miss Rate:** FN_CB / (TP_C + FN_CB)
- **Gunshot → Chainsaw Confusion Rate:** FP_GC / (TP_G + FP_GC)
- **Background → Chainsaw False Alarm Rate:** FP_BC / (TP_B + FP_BC)

**Targets:**
- **Chainsaw → Gunshot:** ≤ 15%
- **Chainsaw Miss Rate:** ≤ 15%
- **Gunshot → Chainsaw:** ≤ 10%
- **Background → Chainsaw:** ≤ 8%

---

## Robustness Evaluation Metrics

### Signal-to-Noise Ratio (SNR) Robustness

**Evaluation Protocol:**
1. Create test subsets at different SNR levels: +20 dB, +10 dB, 0 dB, -10 dB
2. Evaluate model performance on each SNR subset
3. Measure performance degradation as SNR decreases

**Metrics:**
- **SNR Degradation Rate:** Performance loss per dB SNR decrease
- **Minimum Operating SNR:** SNR at which performance drops below threshold
- **Robustness Score:** Average performance across SNR levels

**Targets:**
- **SNR Degradation Rate:** ≤ 1% performance loss per dB
- **Minimum Operating SNR:** ≥ 0 dB (Macro-F1 ≥ 0.65)
- **Robustness Score:** Macro-F1 ≥ 0.70 across SNR levels

### Environmental Condition Robustness

**Evaluation Protocol:**
1. Create test subsets for different environmental conditions:
   - Weather: Clear, cloudy, rain, wind, snow
   - Time of Day: Dawn, day, dusk, night
   - Season: Spring, summer, fall, winter
2. Evaluate model performance on each condition subset
3. Measure performance variation across conditions

**Metrics:**
- **Condition Variance:** Standard deviation of performance across conditions
- **Worst-Condition Performance:** Performance on most challenging condition
- **Condition Robustness Score:** Average performance across conditions

**Targets:**
- **Condition Variance:** ≤ 0.10 (10% performance variation)
- **Worst-Condition Performance:** Macro-F1 ≥ 0.65
- **Condition Robustness Score:** Macro-F1 ≥ 0.75

### Distance Robustness

**Evaluation Protocol:**
1. Create test subsets at different distances: 10m, 25m, 50m, 100m, 200m
2. Evaluate model performance on each distance subset
3. Measure performance degradation as distance increases

**Metrics:**
- **Distance Degradation Rate:** Performance loss per distance doubling
- **Maximum Detection Range:** Distance at which performance drops below threshold
- **Distance Robustness Score:** Average performance across distances

**Targets:**
- **Distance Degradation Rate:** ≤ 15% performance loss per distance doubling
- **Maximum Detection Range:** ≥ 100m (Macro-F1 ≥ 0.65)
- **Distance Robustness Score:** Macro-F1 ≥ 0.70 across distances

### Microphone Variation Robustness

**Evaluation Protocol:**
1. Create test subsets using different microphones:
   - Deployment microphone (INMP441)
   - Alternative microphones (USB, professional)
   - Different microphone orientations
2. Evaluate model performance on each microphone subset
3. Measure performance variation across microphones

**Metrics:**
- **Microphone Variance:** Standard deviation of performance across microphones
- **Deployment Microphone Performance:** Performance on target microphone
- **Microphone Robustness Score:** Average performance across microphones

**Targets:**
- **Microphone Variance:** ≤ 0.08 (8% performance variation)
- **Deployment Microphone Performance:** Macro-F1 ≥ 0.80
- **Microphone Robustness Score:** Macro-F1 ≥ 0.75

---

## Cross-Dataset Generalization Metrics

### Cross-Dataset Evaluation Protocol

**Experiment Design:**
1. **Train on Dataset A, Test on Dataset B**
2. **Train on Datasets A+B, Test on Dataset C**
3. **Train on Public Datasets, Test on Field Data**
4. **Train on Field Data, Test on Public Datasets**

**Metrics:**
- **Cross-Dataset Performance:** Macro-F1 on held-out dataset
- **Performance Drop:** Performance difference between same-dataset and cross-dataset
- **Generalization Ratio:** Cross-dataset performance / same-dataset performance

**Targets:**
- **Cross-Dataset Performance:** Macro-F1 ≥ 0.65
- **Performance Drop:** ≤ 20% performance loss
- **Generalization Ratio:** ≥ 0.80

### Leave-One-Dataset-Out Evaluation

**Protocol:**
1. For each dataset D in {D1, D2, ..., Dn}:
   - Train on all datasets except D
   - Test on dataset D
2. Report average performance across all leave-one-out experiments

**Metrics:**
- **LODO Performance:** Average Macro-F1 across leave-one-out experiments
- **LODO Variance:** Variance of performance across datasets
- **LODO Worst-Case:** Worst performance across all leave-one-out experiments

**Targets:**
- **LODO Performance:** Macro-F1 ≥ 0.70
- **LODO Variance:** ≤ 0.12
- **LODO Worst-Case:** Macro-F1 ≥ 0.60

### Field Validation Metrics

**Protocol:**
1. Train model on public datasets only
2. Evaluate on held-out field validation dataset
3. Compare with public dataset test performance

**Metrics:**
- **Field Performance:** Macro-F1 on field validation set
- **Field Performance Drop:** Difference between public and field performance
- **Field-Deployment Ratio:** Field performance / public performance

**Targets:**
- **Field Performance:** Macro-F1 ≥ 0.65
- **Field Performance Drop:** ≤ 25%
- **Field-Deployment Ratio:** ≥ 0.75

---

## Statistical Rigor

### Confidence Intervals

**Method:** Bootstrap confidence intervals (95% confidence)

**Protocol:**
1. Resample test set with replacement (1,000 iterations)
2. Compute metrics on each resample
3. Report 95% confidence intervals

**Rationale:**
- Quantifies uncertainty in performance estimates
- Enables statistical comparison between models
- Standard practice in research literature

### Statistical Significance Testing

**Method:** Paired bootstrap test or McNemar's test for classification

**Protocol:**
1. Compare model A vs model B on same test set
2. Compute p-value for performance difference
3. Report statistical significance (p < 0.05)

**Rationale:**
- Determines if performance differences are statistically significant
- Supports defensible research claims
- Standard practice in model comparison

### Multiple Comparison Correction

**Method:** Bonferroni correction or False Discovery Rate (FDR)

**Protocol:**
1. When making multiple comparisons, apply correction
2. Adjust significance threshold based on number of comparisons
3. Report corrected p-values

**Rationale:**
- Controls false positive rate in multiple testing
- Ensures statistical rigor
- Supports reproducible research

---

## Edge Deployment Metrics

### Model Size Metrics

**Metrics:**
- **Parameter Count:** Total number of model parameters
- **Model File Size:** TFLite model file size (bytes)
- **Quantized Model Size:** INT8 quantized model file size (bytes)
- **Weight Size:** Size of model weights only
- **Activation Memory:** Peak activation memory during inference

**Targets:**
- **Parameter Count:** ≤ 100,000 parameters
- **Model File Size:** ≤ 500 KB (FP32), ≤ 250 KB (INT8)
- **Weight Size:** ≤ 400 KB (FP32), ≤ 200 KB (INT8)
- **Activation Memory:** ≤ 100 KB

### Inference Latency Metrics

**Metrics:**
- **Feature Extraction Latency:** Time to extract features from audio
- **Inference Latency:** Time for model inference only
- **End-to-End Latency:** Total time from audio input to classification output
- **Preprocessing Latency:** Audio preprocessing time (resampling, normalization)
- **Post-processing Latency:** Output processing time

**Targets (ESP32-S3 @ 240MHz):**
- **Feature Extraction Latency:** ≤ 50 ms
- **Inference Latency:** ≤ 100 ms
- **End-to-End Latency:** ≤ 200 ms
- **Preprocessing Latency:** ≤ 30 ms
- **Post-processing Latency:** ≤ 20 ms

### Memory Metrics

**Metrics:**
- **Static Memory:** Memory for model weights and constants
- **Peak Runtime Memory:** Peak memory during inference
- **Tensor Arena Size:** TFLite Micro tensor arena size
- **Free Heap Before:** Free heap memory before model allocation
- **Free Heap After:** Free heap memory after model allocation

**Targets (ESP32-S3 with 512KB SRAM):**
- **Static Memory:** ≤ 200 KB
- **Peak Runtime Memory:** ≤ 300 KB
- **Tensor Arena Size:** ≤ 250 KB
- **Free Heap Before:** ≥ 400 KB
- **Free Heap After:** ≥ 100 KB

### Quantization Impact Metrics

**Metrics:**
- **FP32 Macro-F1:** Macro-F1 with FP32 model
- **INT8 Macro-F1:** Macro-F1 with INT8 quantized model
- **Accuracy Drop:** FP32 Macro-F1 - INT8 Macro-F1
- **Model Size Reduction:** (FP32 Size - INT8 Size) / FP32 Size
- **Latency Improvement:** (FP32 Latency - INT8 Latency) / FP32 Latency

**Targets:**
- **FP32 Macro-F1:** ≥ 0.80
- **INT8 Macro-F1:** ≥ 0.78 (≤ 2.5% accuracy drop)
- **Accuracy Drop:** ≤ 2.5%
- **Model Size Reduction:** ≥ 50%
- **Latency Improvement:** ≥ 30%

---

## Evaluation Protocol

### Test Set Composition

**Requirements:**
- **Size:** Minimum 120 independent recordings per class
- **Source Diversity:** Multiple independent sources per class
- **Environmental Diversity:** Various environmental conditions
- **Geographic Diversity:** Multiple geographic regions
- **Temporal Diversity:** Different times of day and seasons

**Splitting Strategy:**
- **Source-Level Splitting:** No source leakage across splits
- **Stratified Sampling:** Balanced class representation
- **Cross-Dataset Representation:** Multiple datasets in test set
- **Field Validation:** Separate field validation set

### Evaluation Procedure

**Standard Evaluation:**
1. Load trained model and test set
2. Compute predictions on test set
3. Calculate primary metrics (Macro-F1, per-class precision/recall/F1)
4. Generate confusion matrix
5. Calculate secondary metrics (PR-AUC, ROC-AUC, accuracy)
6. Compute confidence intervals via bootstrap
7. Report results with statistical significance

**Robustness Evaluation:**
1. Create robustness test subsets (SNR, environmental, distance)
2. Evaluate model on each subset
3. Calculate robustness metrics
4. Compare with standard evaluation
5. Identify failure conditions

**Cross-Dataset Evaluation:**
1. Perform leave-one-dataset-out evaluation
2. Evaluate on field validation set
3. Calculate generalization metrics
4. Analyze performance drops
5. Identify domain gaps

### Reporting Standards

**Required Reports:**
1. **Primary Metrics Table:** Macro-F1, per-class precision/recall/F1, balanced accuracy
2. **Confusion Matrix:** Actual vs predicted class distribution
3. **Secondary Metrics Table:** PR-AUC, ROC-AUC, accuracy
4. **False Alarm Metrics:** FPR, FDR, false alarms per hour
5. **Robustness Analysis:** Performance across conditions
6. **Cross-Dataset Analysis:** Generalization performance
7. **Edge Deployment Metrics:** Model size, latency, memory
8. **Statistical Analysis:** Confidence intervals, significance tests

**Visualization Requirements:**
1. **Confusion Matrix Heatmap:** Visual confusion patterns
2. **Precision-Recall Curves:** Per-class PR curves
3. **ROC Curves:** Per-class ROC curves
4. **Robustness Plots:** Performance vs SNR/distance/conditions
5. **Cross-Dataset Plots:** Performance across datasets
6. **Error Analysis:** Examples of misclassifications

---

## Success Criteria

### Minimum Viable Dataset Success
- [ ] Macro-F1 ≥ 0.70 on test set
- [ ] Per-class F1 meets minimum targets
- [ ] False alarm rates within acceptable range
- [ ] Robustness evaluation completed
- [ ] Cross-dataset evaluation attempted

### Target Research Dataset Success
- [ ] Macro-F1 ≥ 0.80 on test set
- [ ] Per-class F1 meets target values
- [ ] False alarm rates within target range
- [ ] Robustness metrics meet targets
- [ ] Cross-dataset generalization demonstrated
- [ ] Field validation performance ≥ 0.65 Macro-F1

### Ideal Dataset Success
- [ ] Macro-F1 ≥ 0.85 on test set
- [ ] Per-class F1 meets ideal targets
- [ ] False alarm rates within ideal range
- [ ] Comprehensive robustness demonstrated
- [ ] Strong cross-dataset generalization
- [ ] Field validation performance ≥ 0.75 Macro-F1
- [ ] Edge deployment metrics within targets
- [ ] Quantization impact ≤ 2.5% accuracy drop

---

**Document Version:** 1.0
**Last Updated:** 2026-09-19
**Status:** Research Phase - Evaluation Protocol Definition
**Next Step:** Implement evaluation pipeline and baseline measurements