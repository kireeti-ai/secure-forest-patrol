# Data Collection Plan

## Overview

This document outlines the comprehensive data collection strategy for the SECURE FOREST PATROL acoustic classification system. The plan integrates public dataset acquisition with targeted field data collection to achieve a research-grade dataset that supports robust model development and defensible edge deployment claims.

---

## Current Status Assessment

### Existing Dataset (Pipeline Validation Only)
- **Original Recordings:** 15
- **Generated Segments:** 40
- **Classes:** 3 (background, chainsaw, gunshot)
- **Distribution:** 29 train, 4 validation, 7 test
- **Assessment:** Insufficient for research-grade model development

### Gap Analysis
- **Scale Gap:** Current dataset is 13x smaller than minimum viable target
- **Diversity Gap:** Limited source, environment, and device diversity
- **Domain Gap:** Public datasets may not match deployment conditions
- **Geographic Gap:** Limited geographic representation
- **License Gap:** Some datasets have non-commercial restrictions

---

## Collection Strategy

### Hybrid Approach

The data collection strategy employs a **hybrid approach** combining:

1. **Public Dataset Integration:** Leverage existing high-quality public datasets
2. **Targeted Field Collection:** Collect domain-specific field data
3. **Strategic Augmentation:** Apply data augmentation to increase diversity
4. **Quality Validation:** Rigorous quality control and validation processes

### Rationale for Hybrid Approach

**Public Dataset Advantages:**
- Immediate availability of large-scale data
- Academic credibility and citation support
- Diverse geographic and environmental coverage
- Established quality standards and documentation
- Cost-effective compared to pure field collection

**Field Collection Advantages:**
- Domain alignment with deployment conditions
- Control over recording equipment and conditions
- Comprehensive metadata collection
- License clarity and control
- Specific environmental and geographic targeting

**Combined Benefits:**
- Scale and diversity from public datasets
- Domain alignment from field collection
- Robustness through source diversity
- Cross-dataset generalization capability
- Deployment readiness validation

---

## Phase 1: Minimum Viable Dataset (Immediate Priority)

### Target Specifications
- **Total Recordings:** 200 independent recordings
- **Distribution:** 50 gunshot, 50 chainsaw, 100 background
- **Timeline:** 4-6 weeks
- **Purpose:** Enable initial model training and baseline evaluation

### Public Dataset Component (150 recordings)

#### Gunshot Data (30 recordings)
- **C3GD:** 20 recordings
  - Source: Certus Caliber Classification Gunshot Dataset
  - License: CC BY 4.0 (commercial use allowed)
  - Selection: Diverse calibers and firearms
  - Priority: HIGH

- **Vietnam Passive Monitoring:** 10 recordings
  - Source: Chu Mom Ray National Park
  - License: Open (verification needed)
  - Selection: Forest-context gunshots
  - Priority: HIGH

#### Chainsaw Data (40 recordings)
- **RFCx FrugalAI:** 30 recordings
  - Source: Rainforest Connection Guardian devices
  - License: CC BY-NC 4.0 (research only)
  - Selection: Forest deployment recordings
  - Priority: HIGH

- **Greece Chainsaw Dataset:** 10 recordings
  - Source: Rodopi Mountain-Range National Park
  - License: Open (verification needed)
  - Selection: Different geographic region
  - Priority: MEDIUM

#### Background Data (80 recordings)
- **FSD50K:** 40 recordings
  - Source: Freesound Dataset 50K
  - License: CC BY 4.0 (commercial use allowed)
  - Selection: Diverse environmental sounds
  - Priority: VERY HIGH

- **ESC-50:** 20 recordings
  - Source: Environmental Sound Classification
  - License: CC BY-NC 3.0 (research only)
  - Selection: Well-structured environmental classes
  - Priority: HIGH

- **DataSEC:** 20 recordings
  - Source: Environmental noise dataset
  - License: Open (verification needed)
  - Selection: Authentic outdoor recordings
  - Priority: HIGH

### Field Collection Component (50 recordings)

#### Background Field Data (30 recordings)
- **Quiet Forest:** 5 recordings
- **Wind Conditions:** 5 recordings
- **Bird Sounds:** 5 recordings
- **Insect Sounds:** 5 recordings
- **Human Movement:** 5 recordings
- **Night Sounds:** 5 recordings

#### Chainsaw Field Data (10 recordings)
- **Authorized Logging Operations:** 10 recordings
- **Various Distances:** 10m, 25m, 50m
- **Different Operations:** Idle, cutting, revving
- **Safety:** Only authorized operations with proper permits

#### Gunshot Field Data (10 recordings)
- **Authorized Shooting Range:** 10 recordings
- **Various Calibers:** Different firearm types
- **Various Distances:** 10m, 25m, 50m
- **Safety:** Only authorized ranges with proper permits

### Success Criteria
- [ ] All public datasets successfully downloaded and verified
- [ ] Field collection equipment tested and calibrated
- [ ] 50 field recordings collected with complete metadata
- [ ] Quality validation passes for all recordings
- [ ] Dataset balanced across classes and conditions
- [ ] All licensing documentation completed

---

## Phase 2: Target Research Dataset (Medium Priority)

### Target Specifications
- **Total Recordings:** 800 independent recordings
- **Distribution:** 200 gunshot, 200 chainsaw, 400 background
- **Timeline:** 3-4 months
- **Purpose:** Support robust model development and publication-quality results

### Public Dataset Component (500 recordings)

#### Gunshot Data (150 recordings)
- **Certus DCASE 2026:** 100 recordings
  - Source: Largest open gunshot dataset
  - License: Likely CC BY (verification needed)
  - Diversity: 85 firearms, 21 calibers
  - Priority: VERY HIGH

- **C3GD:** 30 recordings
  - Additional diverse recordings from C3GD
  - Priority: HIGH

- **Vietnam Dataset:** 20 recordings
  - Additional forest-context recordings
  - Priority: HIGH

#### Chainsaw Data (130 recordings)
- **RFCx FrugalAI:** 100 recordings
  - Extensive forest deployment recordings
  - Priority: VERY HIGH

- **Greece Dataset:** 20 recordings
  - Additional geographic diversity
  - Priority: MEDIUM

- **FSC22 Chainsaw:** 10 recordings
  - Forest-specific chainsaw data
  - Priority: MEDIUM

#### Background Data (220 recordings)
- **FSD50K:** 100 recordings
  - Extensive environmental diversity
  - Priority: VERY HIGH

- **ESC-50:** 50 recordings
  - Additional environmental classes
  - Priority: HIGH

- **DataSEC:** 40 recordings
  - Additional outdoor recordings
  - Priority: HIGH

- **FSC22 Background:** 30 recordings
  - Forest-specific background sounds
  - Priority: MEDIUM

### Field Collection Component (300 recordings)

#### Background Field Data (150 recordings)
- **Comprehensive Environmental Coverage:**
  - Weather: Clear, cloudy, rain, snow (20 each)
  - Time of Day: Dawn, day, dusk, night (15 each)
  - Season: Spring, summer, fall, winter (10 each)
  - Forest Type: Coniferous, deciduous, mixed (15 each)
  - Distance Variations: Various distances from sound sources (30 total)

#### Chainsaw Field Data (70 recordings)
- **Comprehensive Operating Conditions:**
  - Different Operations: Idle, acceleration, cutting (20 each)
  - Different Distances: 10m, 25m, 50m, 100m (15 each)
  - Different Tree Species: Various wood types (10 each)
  - Weather Conditions: Various weather (10 each)
  - Time of Day: Different acoustic conditions (5 each)

#### Gunshot Field Data (80 recordings)
- **Comprehensive Firearm Coverage:**
  - Different Calibers: Various firearm calibers (30 each)
  - Different Distances: 10m, 25m, 50m, 100m (20 each)
  - Different Environments: Open forest, dense forest, edge (15 each)
  - Atmospheric Conditions: Various weather and temperature (15 each)

### Success Criteria
- [ ] All public datasets integrated and validated
- [ ] 300 field recordings collected with comprehensive metadata
- [ ] Geographic diversity achieved (5+ locations)
- [ ] Environmental diversity achieved (weather, seasons, times)
- [ ] Source diversity achieved (10+ independent sources per class)
- [ ] Cross-dataset leakage prevention verified
- [ ] Quality validation passes for all recordings

---

## Phase 3: Ideal Dataset (Long-term Goal)

### Target Specifications
- **Total Recordings:** 2,000+ independent recordings
- **Distribution:** 500+ gunshot, 500+ chainsaw, 1,000+ background
- **Timeline:** 6-12 months
- **Purpose:** State-of-the-art model development and comprehensive deployment

### Public Dataset Component (1,200+ recordings)

#### Gunshot Data (400+ recordings)
- **Certus DCASE 2026:** 300 recordings
- **C3GD:** 50 recordings
- **Vietnam Dataset:** 30 recordings
- **Gabon Dataset:** 20+ recordings
- **Additional Public Sources:** 20+ recordings

#### Chainsaw Data (400+ recordings)
- **RFCx FrugalAI:** 300 recordings
- **Greece Dataset:** 50 recordings
- **FSC22 Chainsaw:** 30 recordings
- **Additional Public Sources:** 20+ recordings

#### Background Data (400+ recordings)
- **FSD50K:** 200 recordings
- **ESC-50:** 100 recordings
- **DataSEC:** 50 recordings
- **FSC22 Background:** 50 recordings
- **Sensing the Forest:** 50+ recordings
- **GESMA:** 50+ recordings
- **Additional Public Sources:** 20+ recordings

### Field Collection Component (800+ recordings)

#### Background Field Data (400+ recordings)
- **Global Geographic Diversity:** Multiple continents/regions
- **Complete Seasonal Coverage:** Full year across all seasons
- **Complete Diurnal Coverage:** 24-hour coverage
- **Complete Weather Coverage:** All weather conditions
- **Complete Forest Type Coverage:** All major forest biomes
- **Anthropogenic Gradient:** Pristine to human-impacted forests

#### Chainsaw Field Data (200+ recordings)
- **Global Geographic Diversity:** Multiple regions
- **Complete Operating State Coverage:** All chainsaw operations
- **Complete Environmental Coverage:** All forest and weather conditions
- **Complete Distance Coverage:** Full distance range
- **Various Tree Species:** Comprehensive tree type coverage

#### Gunshot Field Data (200+ recordings)
- **Global Geographic Diversity:** Multiple regions
- **Complete Firearm Coverage:** Comprehensive caliber/type coverage
- **Complete Environmental Coverage:** All forest and weather conditions
- **Complete Distance Coverage:** Full distance range
- **Atmospheric Variation:** All atmospheric conditions

### Success Criteria
- [ ] Global geographic diversity achieved (10+ locations)
- [ ] Complete seasonal and diurnal coverage
- [ ] Complete environmental and weather coverage
- [ ] Source diversity achieved (20+ independent sources per class)
- [ ] Cross-dataset generalization capability demonstrated
- [ ] Field validation dataset established
- [ ] Deployment readiness comprehensively validated

---

## Data Integration Strategy

### Preprocessing Pipeline
1. **Format Standardization:** Convert all audio to 16 kHz, mono, 16-bit WAV
2. **Quality Control:** Remove corrupted, clipped, or low-quality recordings
3. **Duplicate Detection:** Remove duplicates using SHA256 hashing
4. **Metadata Standardization:** Standardize metadata across all sources
5. **Source Tracking:** Maintain source attribution for all recordings

### Dataset Splitting Strategy
- **Method:** Source-level splitting (no leakage across splits)
- **Ratio:** 70% train, 15% validation, 15% test
- **Cross-Dataset:** Ensure cross-dataset representation in all splits
- **Field Validation:** Maintain separate field validation dataset

### Metadata Integration
- **Unified Schema:** Standardized metadata schema across all sources
- **Source Attribution:** Maintain source information for provenance
- **Quality Flags:** Quality assessment flags for each recording
- **License Tracking:** License information for each recording
- **Usage Restrictions:** Document any usage restrictions

---

## Quality Assurance Plan

### Automated Quality Checks
- **Audio Quality:** Automated clipping detection, SNR measurement
- **Format Validation:** Sample rate, bit depth, channel validation
- **Metadata Completeness:** Required field presence validation
- **Duplicate Detection:** SHA256 hash-based duplicate detection
- **File Integrity:** Checksum verification

### Manual Quality Review
- **Audio Quality:** Human listening assessment
- **Label Accuracy:** Verification of event labels
- **Metadata Accuracy:** Verification of metadata accuracy
- **Representativeness:** Assessment of environmental representativeness
- **Safety/Legal:** Verification of safety and legal compliance

### Statistical Quality Assessment
- **Class Distribution:** Analysis of class balance
- **Source Diversity:** Analysis of source diversity
- **Environmental Diversity:** Analysis of environmental coverage
- **Geographic Diversity:** Analysis of geographic coverage
- **Temporal Diversity:** Analysis of temporal coverage

---

## Risk Mitigation

### Public Dataset Risks
- **Download Failures:** Alternative sources, manual download, contact authors
- **License Issues:** Legal review, alternative datasets, license negotiation
- **Quality Issues:** Quality filtering, augmentation, alternative sources
- **Format Issues:** Format conversion, resampling, format validation

### Field Collection Risks
- **Safety Incidents:** Comprehensive safety protocols, emergency procedures
- **Equipment Failure:** Redundant equipment, backup plans, rapid replacement
- **Weather Interruption:** Flexible scheduling, weather monitoring, alternative timing
- **Permission Issues:** Early permission acquisition, alternative locations, legal support

### Integration Risks
- **Format Incompatibility:** Comprehensive preprocessing pipeline
- **Metadata Inconsistency:** Standardized schema, manual review
- **Source Leakage:** Rigorous splitting validation, cross-checking
- **Quality Variance:** Quality assessment, filtering, weighting

---

## Resource Requirements

### Equipment Requirements
- **Recording Devices:** ESP32-S3 with INMP441 (primary), alternative recorders
- **Storage:** 1TB+ storage for raw and processed data
- **Computing:** Workstation for preprocessing and quality control
- **Calibration Equipment:** Reference sound source, sound level meter
- **Field Equipment:** Weatherproof enclosures, mounting hardware, power systems

### Personnel Requirements
- **Audio Engineers:** Recording setup and quality control
- **Field Technicians:** Field data collection and equipment operation
- **Data Scientists:** Data integration and quality assessment
- **Legal/Safety:** Permission acquisition and safety compliance
- **Project Management:** Coordination and timeline management

### Budget Requirements
- **Equipment:** Recording devices, storage, calibration equipment
- **Travel:** Field site travel and accommodation
- **Permits:** Land access permits, shooting range fees
- **Personnel:** Personnel time and expertise
- **Infrastructure:** Storage, computing, backup systems

---

## Timeline and Milestones

### Phase 1: Minimum Viable Dataset (Weeks 1-6)
- **Week 1-2:** Public dataset acquisition and validation
- **Week 3-4:** Field collection setup and pilot recordings
- **Week 5-6:** Complete field collection and integration

**Milestone:** 200 recordings with quality validation complete

### Phase 2: Target Research Dataset (Months 2-4)
- **Month 2:** Extended public dataset integration
- **Month 3:** Comprehensive field collection
- **Month 4:** Data integration and quality validation

**Milestone:** 800 recordings with comprehensive diversity

### Phase 3: Ideal Dataset (Months 5-12)
- **Months 5-8:** Global data collection and integration
- **Months 9-10:** Quality validation and refinement
- **Months 11-12:** Final validation and deployment readiness

**Milestone:** 2,000+ recordings with global diversity

---

## Success Metrics

### Quantitative Metrics
- **Recording Count:** Meet or exceed target recording counts
- **Class Balance:** Balanced representation across classes
- **Source Diversity:** Multiple independent sources per class
- **Environmental Diversity:** Coverage of environmental conditions
- **Geographic Diversity:** Coverage of geographic regions
- **Quality Metrics:** 95%+ recordings pass quality checks

### Qualitative Metrics
- **Domain Alignment:** Field data matches deployment conditions
- **License Clarity:** Clear licensing for all data sources
- **Metadata Quality:** Complete and accurate metadata
- **Safety Compliance:** All safety protocols followed
- **Legal Compliance:** All legal requirements met

### Research Metrics
- **Cross-Dataset Generalization:** Demonstrated generalization capability
- **Publication Readiness:** Dataset supports publication-quality research
- **Deployment Readiness:** Dataset supports edge deployment claims
- **Reproducibility:** Dataset supports reproducible research
- **Citation Potential:** Dataset has strong citation potential

---

## Next Steps

### Immediate Actions (Week 1)
1. **Download C3GD dataset** (CC BY 4.0, highest priority)
2. **Download FSD50K dataset** (CC BY 4.0, highest priority)
3. **Contact RFCx for FrugalAI access** (document NC restriction)
4. **Set up field collection equipment** (ESP32-S3 with INMP441)
5. **Obtain initial permissions** for field collection sites

### Short-term Actions (Weeks 2-4)
1. **Verify Certus DCASE 2026 license** and download if appropriate
2. **Begin pilot field collection** (background data first)
3. **Implement quality control pipeline**
4. **Integrate initial public datasets**
5. **Validate preprocessing pipeline**

### Medium-term Actions (Months 2-4)
1. **Comprehensive public dataset integration**
2. **Extended field collection**
3. **Cross-dataset generalization testing**
4. **Quality validation and refinement**
5. **Publication documentation preparation**

---

**Document Version:** 1.0
**Last Updated:** 2026-09-19
**Status:** Research Phase - Data Collection Strategy
**Next Step:** Begin Phase 1 data collection execution