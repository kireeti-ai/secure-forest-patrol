# Dataset Size Justification

## Overview

This document provides a literature-backed justification for the dataset scale required to support a research-grade acoustic classification model for forest patrol applications. The current dataset (15 original recordings, 40 segments) is insufficient for reliable model training, generalization analysis, and edge deployment evaluation.

---

## Current Dataset Status

**Current Dataset (Pipeline Validation Only):**
- Original recordings: 15
- Generated segments: 40
- Classes: 3 (background, chainsaw, gunshot)
- Train samples: 29
- Validation samples: 4
- Test samples: 7

**Assessment:** This dataset validates the preprocessing pipeline but is **insufficient** for:
- Reliable model training
- Generalization analysis
- Cross-dataset evaluation
- Defensible research claims
- Edge deployment evaluation

---

## Literature Review: Dataset Scale Requirements

### Environmental Sound Classification Benchmarks

#### ESC-50 (Piczak, 2015)
- **Size:** 2,000 samples across 50 classes
- **Per-class:** 40 samples per class
- **Purpose:** Benchmark dataset for environmental sound classification
- **Status:** Considered a minimum viable research dataset in the field
- **Citation:** Piczak, K. J. (2015). ESC: Dataset for Environmental Sound Classification

#### FSC22 Forest Sound Classification (2023)
- **Size:** 2,025 samples across 27 forest-specific classes
- **Per-class:** ~75 samples per class (average)
- **Purpose:** Benchmark dataset specifically for forest environmental sounds
- **Status:** Designed to address the lack of forest-specific datasets
- **Citation:** FSC22: Forest Sound Classification Dataset, Sensors, 2023

#### UrbanSound8K (Salamon et al., 2014)
- **Size:** 8,732 samples across 10 classes
- **Per-class:** ~873 samples per class
- **Purpose:** Urban sound classification benchmark
- **Status:** Well-established benchmark with strong generalization results
- **Citation:** Salamon, J., Jacoby, C., & Bello, J. P. (2014). A Dataset and Taxonomy for Urban Sound Research

### Audio Classification with Limited Data

#### Bird Sound Classification Study
- **Finding:** With transfer learning and data augmentation, satisfactory results achieved with 10-80 recordings per species
- **Context:** 12 bird species classification using EfficientNet architecture
- **Key insight:** Transfer learning + augmentation can reduce data requirements
- **Citation:** Fine-tuning for Bird Sound Classification: An Empirical Study

#### Few-Shot Audio Classification
- **Finding:** Prototypical networks and transfer learning enable training with 1-100 labeled examples per class
- **Context:** Acoustic event recognition and acoustic scene classification
- **Key insight:** Advanced techniques can work with limited data but require careful implementation
- **Citation:** Pons, J. et al. Neural-classifiers-with-few-audio

### Deep Learning Data Requirements

#### CNN Audio Classification Requirements
- **Finding:** Deep learning approaches require massive training data for sound classification
- **Context:** ESC-50 and other sound datasets are typically too small for deep learners
- **Key insight:** Data augmentation is essential when working with limited datasets
- **Citation:** An Ensemble of Convolutional Neural Networks for Audio Classification

#### TinyML Speech Recognition
- **Finding:** Google Speech Commands dataset uses 105,000+ samples for 30-word classification
- **Context:** Keyword spotting on microcontrollers
- **Key insight:** Even edge-deployed models benefit from large datasets
- **Citation:** TensorFlow Lite Micro Speech Commands Example

### Forest-Specific Acoustic Monitoring

#### Illegal Logging Detection Studies
- **Finding:** Most forest monitoring studies use small-scale datasets with limited consideration of background noise
- **Context:** Acoustic surveillance for illegal logging detection
- **Key insight:** Existing forest datasets are often insufficient for robust real-world deployment
- **Citation:** Illegal Logging Detection Based on Acoustic Surveillance of Forest, Applied Sciences, 2020

#### Chainsaw Detection Systems
- **Finding:** Limited number of different approaches evaluated based on small-scale datasets
- **Context:** Long-range chainsaw sound detection in protected environments
- **Key insight:** Robustness to noise and variation requires more diverse data
- **Citation:** An Open-Access System for Long-Range Chainsaw Detection, EUSIPCO 2022

---

## Key Findings from Literature

### Minimum Viable Research Dataset
Based on the literature review, the **minimum viable research dataset** for environmental sound classification should include:

- **Per-class minimum:** 40-100 independent recordings per class
- **Total minimum:** 120-300 independent recordings (for 3 classes)
- **Source diversity:** Multiple recording sources, environments, and conditions
- **Temporal diversity:** Different times of day, seasons, weather conditions
- **Device diversity:** Multiple microphones/recording devices where possible

### Research-Grade Dataset
For a **research-grade dataset** that supports:
- Reliable model training
- Generalization analysis
- Cross-dataset evaluation
- Defensible publication claims

The literature suggests:
- **Per-class target:** 200-500 independent recordings per class
- **Total target:** 600-1,500 independent recordings (for 3 classes)
- **Independent sources:** 10+ different sources per class
- **Environmental diversity:** 5+ different environments per class
- **Field validation:** Separate field dataset for external validation

### Domain-Specific Considerations

#### Forest Deployment Specifics
Forest deployment introduces additional requirements:
- **Background complexity:** Forest soundscapes are acoustically complex
- **Distance variation:** Sounds must be detected at various distances
- **Weather effects:** Rain, wind, temperature affect sound propagation
- **Seasonal variation:** Forest acoustics change significantly across seasons
- **Domain gap:** Public datasets may not match deployment conditions

#### Edge Deployment Constraints
ESP32-S3 deployment adds requirements:
- **Model generalization:** Must work on-device with limited compute
- **Robustness:** Must handle variable real-world conditions
- **False alarm control:** Safety-critical application requires low false positives
- **Real-time performance:** Must process audio in real-time

---

## Proposed Dataset Targets

### Minimum Viable Research Dataset (MV)

**Purpose:** Initial model development and baseline evaluation

**Per-Class Requirements:**
- **Gunshot:** 50 independent recordings
  - 10+ different firearms/calibers
  - 5+ different environments
  - 3+ different recording devices
  - Various distances (10m, 25m, 50m, 100m)

- **Chainsaw:** 50 independent recordings
  - 10+ different chainsaw models/conditions
  - 5+ different forest environments
  - 3+ different recording devices
  - Various distances (10m, 25m, 50m, 100m)
  - Different operating states (idle, cutting, revving)

- **Background:** 100 independent recordings
  - 20+ different forest locations
  - Various times of day (dawn, day, dusk, night)
  - Various weather conditions (clear, wind, rain)
  - Seasonal variation (spring, summer, fall, winter)
  - Different forest types

**Total:** 200 independent recordings
**Estimated segments:** 800-1,000 (assuming 4-5 segments per recording)
**Train/Val/Test split:** 70%/15%/15% by source

### Target Research Dataset (TR)

**Purpose:** Robust model training, generalization analysis, publication-quality results

**Per-Class Requirements:**
- **Gunshot:** 200 independent recordings
  - 20+ different firearms/calibers
  - 10+ different environments
  - 5+ different recording devices
  - Comprehensive distance coverage
  - Various atmospheric conditions

- **Chainsaw:** 200 independent recordings
  - 20+ different chainsaw models/conditions
  - 10+ different forest environments
  - 5+ different recording devices
  - Comprehensive distance and operating state coverage
  - Different tree species being cut

- **Background:** 400 independent recordings
  - 50+ different forest locations
  - Comprehensive temporal coverage (24h, seasonal)
  - Comprehensive weather coverage
  - Multiple forest types and densities
  - Anthropogenic variation (near/far from human activity)

**Total:** 800 independent recordings
**Estimated segments:** 3,200-4,000
**Train/Val/Test split:** 70%/15%/15% by source

### Ideal Dataset (ID)

**Purpose:** State-of-the-art model development, comprehensive evaluation, robust deployment

**Per-Class Requirements:**
- **Gunshot:** 500+ independent recordings
  - Comprehensive firearm/caliber coverage
  - Global geographic diversity
  - Multiple recording device types
  - Full environmental and atmospheric coverage
  - Superset of publicly available datasets

- **Chainsaw:** 500+ independent recordings
  - Comprehensive chainsaw type/condition coverage
  - Global forest environment diversity
  - Multiple recording device types
  - Full operational state coverage
  - Integration with RFCx FrugalAI and other public datasets

- **Background:** 1,000+ independent recordings
  - Global forest biome diversity
  - Full seasonal and diurnal coverage
  - Comprehensive weather condition coverage
  - Integration with sensing the forest and other public datasets
  - Anthropogenic gradient (pristine to human-impacted)

**Total:** 2,000+ independent recordings
**Estimated segments:** 8,000-10,000+
**Train/Val/Test split:** 70%/15%/15% by source
**Additional:** Separate field validation dataset (200+ recordings)

---

## Comparison with Current Dataset

| Metric | Current | MV | TR | ID |
|--------|---------|----|----|----|
| **Original Recordings** | 15 | 200 | 800 | 2,000+ |
| **Gunshot Recordings** | 2 | 50 | 200 | 500+ |
| **Chainsaw Recordings** | 3 | 50 | 200 | 500+ |
| **Background Recordings** | 10 | 100 | 400 | 1,000+ |
| **Independent Sources** | 3 | 15+ | 30+ | 50+ |
| **Environments** | 1 | 5+ | 10+ | 20+ |
| **Devices** | 1 | 3+ | 5+ | 10+ |
| **Estimated Segments** | 40 | 800-1,000 | 3,200-4,000 | 8,000-10,000+ |
| **Test Set Size** | 7 | 120-150 | 480-600 | 1,200-1,500+ |

**Gap Analysis:**
- Current dataset is **13x smaller** than Minimum Viable
- Current dataset is **53x smaller** than Target Research
- Current dataset is **133x smaller** than Ideal

---

## Justification Summary

### Literature-Backed Requirements

1. **ESC-50 Benchmark:** 40 samples per class is considered minimum viable
2. **FSC22 Forest Dataset:** 75 samples per class for forest-specific sounds
3. **UrbanSound8K:** 873 samples per class for robust generalization
4. **Bird Classification:** 10-80 samples per class with transfer learning
5. **Deep Learning Requirements:** Large datasets essential for reliable training

### Domain-Specific Requirements

1. **Forest Complexity:** Forest soundscapes require more diverse data
2. **Distance Variation:** Detection at range requires distance-diverse data
3. **Weather Effects:** Robustness requires weather-diverse data
4. **Seasonal Variation:** Year-round deployment requires seasonal data
5. **Edge Deployment:** Real-world deployment requires field validation data

### Research Requirements

1. **Generalization Analysis:** Cross-dataset evaluation requires diverse sources
2. **Ablation Studies:** Meaningful ablations require sufficient data
3. **Robustness Evaluation:** Robustness testing requires condition-diverse data
4. **Publication Quality:** Defensible claims require research-grade data
5. **Reproducibility:** Independent test sets require sufficient size

---

## Recommended Approach

### Phase 1: Minimum Viable Dataset (Immediate Priority)
- **Target:** 200 independent recordings (50 gunshot, 50 chainsaw, 100 background)
- **Timeline:** 4-6 weeks
- **Sources:** Mix of public datasets and initial field collection
- **Purpose:** Enable initial model training and baseline evaluation

### Phase 2: Target Research Dataset (Medium Priority)
- **Target:** 800 independent recordings (200 per class)
- **Timeline:** 3-4 months
- **Sources:** Comprehensive public dataset integration + extensive field collection
- **Purpose:** Support robust model development and publication-quality results

### Phase 3: Ideal Dataset (Long-term Goal)
- **Target:** 2,000+ independent recordings
- **Timeline:** 6-12 months
- **Sources:** Global data collection, comprehensive public dataset integration
- **Purpose:** State-of-the-art model development and comprehensive deployment

---

## Conclusion

Based on comprehensive literature review and domain-specific requirements, the **current dataset (15 recordings, 40 segments) is insufficient** for research-grade model development. The recommended approach is to:

1. **Immediate:** Develop Minimum Viable Dataset (200 recordings)
2. **Medium-term:** Develop Target Research Dataset (800 recordings)
3. **Long-term:** Develop Ideal Dataset (2,000+ recordings)

The **Minimum Viable Dataset** represents the smallest dataset that can support defensible research, while the **Target Research Dataset** provides the scale needed for robust model development and publication-quality results.

---

**Document Version:** 1.0
**Last Updated:** 2026-09-19
**Status:** Research Phase - Dataset Expansion Required
**Next Step:** Public dataset research and field data collection protocol development