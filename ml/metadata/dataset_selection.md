# Dataset Selection Rationale

This document explains the selection of datasets for the SECURE FOREST PATROL acoustic event classification project.

## Selected Datasets

### 1. C3GD (Certus Caliber Classification Gunshot Dataset)
**Purpose:** Gunshot detection and classification  
**URL:** https://github.com/Stonewall-Defense/C3GD  
**License:** CC BY 4.0 (permissive, allows commercial use with attribution)

**Selection Rationale:**
- **High-quality field-collected data**: 8,015 recordings from actual field conditions, not internet-scraped audio
- **Comprehensive metadata**: Detailed information about firearms, calibers, microphones, and recording conditions
- **Source diversity**: 28 firearms across 16 calibers with multiple microphone positions
- **Permissive license**: CC BY 4.0 allows both research and commercial use with attribution
- **Purpose-built**: Specifically designed for acoustic gunshot analysis
- **Verified suitability**: Preliminary training achieved 97% test accuracy, confirming data quality

**Trade-offs:**
- Focused on caliber classification rather than pure detection (but still suitable for detection)
- Primarily outdoor range conditions (may not represent all forest environments)
- Sample rate and channel format need verification during download

---

### 2. RFCx FrugalAI Chainsaw Dataset
**Purpose:** Chainsaw detection in forest environments  
**URL:** https://huggingface.co/datasets/rfcx/frugalai  
**License:** CC BY-NC 4.0 (non-commercial, requires attribution)

**Selection Rationale:**
- **Real forest deployment data**: Collected from Guardian devices actually deployed in forests (South America, Southeast Asia)
- **Purpose-built for forest chainsaw detection**: Designed specifically for illegal logging detection in forest environments
- **Authentic conditions**: Recordings from actual forest canopy deployments, not controlled environments
- **Binary classification**: Clear chainsaw vs environment labels
- **Geographic diversity**: Multiple forest regions across different continents
- **Time diversity**: Data from 2015-2022 captures various conditions

**Trade-offs:**
- **Non-commercial license**: CC BY-NC 4.0 restricts commercial use (acceptable for research phase)
- **Lossy compression**: Original Opus format may affect audio quality (need to assess impact)
- **12 kHz sample rate**: Requires resampling to 16 kHz target
- **Human voices removed**: May not represent all human activity scenarios in forests

---

### 3. ESC-50 (Dataset for Environmental Sound Classification)
**Purpose:** Environmental and background sound diversity  
**URL:** https://github.com/karolpiczak/ESC-50  
**License:** CC BY-NC 3.0 (non-commercial, requires attribution)

**Selection Rationale:**
- **Excellent class diversity**: 50 environmental sound classes including relevant categories
- **Chainsaw included**: Class 40 provides additional chainsaw data
- **Rich environmental sounds**: Rain, wind, birds, insects, thunderstorm, natural soundscapes
- **High label quality**: Manually extracted and labeled from Freesound recordings
- **Structured folds**: 5 pre-arranged folds prevent source leakage
- **Global source diversity**: From Freesound international community
- **Proven benchmark**: Widely used in environmental sound classification research

**Trade-offs:**
- **Non-commercial license**: CC BY-NC 3.0 restricts commercial use
- **No direct gunshot class**: Gunshot not among the 50 classes
- **44.1 kHz sample rate**: Requires downsampling to 16 kHz
- **5-second duration**: May need segmentation to 1-second windows
- **General environmental focus**: Not specifically forest-oriented

---

### 4. Sensing the Forest - Natural Soundscape Dataset
**Purpose:** Authentic forest background ambience  
**URL:** https://zenodo.org/records/18909809  
**License:** CC0 1.0 (public domain, most permissive)

**Selection Rationale:**
- **Public domain license**: CC0 1.0 allows any use without restrictions
- **Authentic forest conditions**: Real woodland recordings from Alice Holt Forest, UK
- **Seasonal coverage**: Recordings across different seasons (August 2024 - March 2025)
- **Diurnal coverage**: 4 recordings per day (sunrise, noon, sunset, night)
- **Rich biodiversity**: Documents various bird species, deer, bats, and natural sounds
- **Solar-powered recording**: Similar to potential edge deployment conditions
- **Complements other datasets**: Provides pure forest background without threat events

**Trade-offs:**
- **No threat events**: Contains only natural soundscape, no gunshot or chainsaw
- **Part 1 only**: Need to obtain Part 2 for complete temporal coverage
- **Sample rate unknown**: Need to verify during download
- **Primarily background**: Used to augment background class, not threat detection

---

## Dataset Combination Strategy

### Class Coverage

| Target Class | Primary Dataset | Secondary Dataset | Total Expected Samples |
|--------------|----------------|-------------------|----------------------|
| GUNSHOT | C3GD (8,015) | None (UrbanSound8K if needed) | ~8,000+ |
| CHAINSAW | RFCx FrugalAI | ESC-50 (chainsaw class) | ~3,000+ (estimated) |
| BACKGROUND | ESC-50 (49 classes) | Sensing the Forest | ~2,000+ (ESC-50) + forest ambience |

### License Strategy

**Research Phase (Current):**
- C3GD: CC BY 4.0 ✓ (permissive)
- RFCx FrugalAI: CC BY-NC 4.0 ✓ (non-commercial acceptable for research)
- ESC-50: CC BY-NC 3.0 ✓ (non-commercial acceptable for research)
- Sensing the Forest: CC0 1.0 ✓ (public domain, most permissive)

**Commercial Deployment Consideration:**
- C3GD and Sensing the Forest can be used commercially
- RFCx FrugalAI and ESC-50 require commercial license alternatives or separate agreements
- For production deployment, may need to source commercial-licensed equivalents or obtain permissions

### Data Quality Expectations

**Advantages of this combination:**
1. **Real-world relevance**: RFCx data from actual forest deployments
2. **High-quality labels**: C3GD and ESC-50 have verified label quality
3. **Source diversity**: Multiple geographic regions, recording devices, conditions
4. **Complementary strengths**: Each dataset covers different aspects of the problem
5. **Research-friendly**: All licenses allow academic research use
6. **Preprocessing compatibility**: All can be standardized to 16 kHz mono

**Known Limitations:**
1. **Non-commercial restrictions**: 2 of 4 datasets have NC licenses
2. **Sample rate variation**: Need to standardize from 12kHz, 44.1kHz, unknown to 16kHz
3. **Domain mismatch**: Public data may not perfectly match specific forest deployment conditions
4. **Class imbalance**: Likely significant imbalance between gunshot, chainsaw, and background classes
5. **Format variation**: Different original formats (WAV, Opus) require standardization

## Alternative Datasets Considered

### Not Selected (and reasons):

**Gunshot Audio Forensics Dataset:**
- Reason: Unclear license terms ("as-is" with no specified license)
- Potential: High quality data but legal uncertainty

**Certus DCASE 2026 Gunshot Dataset:**
- Reason: License needs verification; very large size may be impractical
- Potential: Largest gunshot collection if license can be clarified

**UrbanSound8K:**
- Reason: Unclear license; urban focus may not represent forest conditions
- Potential: Contains gunshot class but domain mismatch

**FSC22:**
- Reason: Complex licensing from multiple FreeSound sources
- Potential: Forest-specific but license complexity

**AudioSet:**
- Reason: Cannot redistribute audio due to YouTube Terms of Service
- Potential: Largest dataset but legal restrictions prevent redistribution

## Implementation Strategy

### Phase 1: Download and Validation
1. Download C3GD from GitHub/Zenodo
2. Download RFCx FrugalAI from Hugging Face
3. Download ESC-50 from GitHub
4. Download Sensing the Forest from Zenodo (Part 1)

### Phase 2: Quality Audit
1. Verify audio formats and sample rates
2. Check for corrupted files
3. Validate label consistency
4. Assess actual class distributions

### Phase 3: Standardization
1. Resample all audio to 16 kHz
2. Convert to mono
3. Standardize format (WAV)
4. Segment to ~1-second windows

### Phase 4: Integration
1. Create unified manifest
2. Handle class mapping across datasets
3. Implement train/val/test split with source leakage prevention
4. Document domain gaps

## Success Criteria

The selected dataset combination will be considered successful if:

1. **All target classes are represented**: Gunshot, chainsaw, and background classes
2. **Minimum sample counts**: At least 1,000 samples per class for meaningful training
3. **Audio quality sufficient**: Preprocessing can standardize to 16 kHz mono without major quality loss
4. **Labels are reliable**: Manual verification confirms label accuracy
5. **No legal conflicts**: All datasets can be used for research under their licenses
6. **Domain relevance**: Data represents conditions reasonably similar to forest deployment

## Future Considerations

**If current datasets prove insufficient:**
1. **Field recordings**: Collect real forest recordings from deployment sites
2. **Commercial licensing**: Obtain commercial licenses for NC-restricted datasets
3. **Synthetic data**: Generate synthetic gunshot/chainsaw data for augmentation
4. **Alternative sources**: Identify additional publicly available datasets

**Domain gap mitigation:**
1. **Data augmentation**: Simulate forest conditions (reverb, background noise)
2. **Transfer learning**: Pre-train on public data, fine-tune on field recordings
3. **Domain adaptation**: Implement techniques to bridge domain gaps
4. **Field validation**: Validate models with real forest recordings before deployment

## Conclusion

This dataset combination provides a defensible foundation for forest acoustic event classification research:

- **C3GD** supplies high-quality gunshot data with permissive licensing
- **RFCx FrugalAI** provides authentic forest chainsaw data from real deployments
- **ESC-50** offers diverse environmental sounds for robust background modeling
- **Sensing the Forest** contributes authentic forest ambience under public domain terms

While non-commercial license restrictions exist for 2 of 4 datasets, this is acceptable for the research phase. The combination balances data quality, relevance, diversity, and legal compliance to create a solid foundation for acoustic event classification model development.
