# Dataset Sources Research

This document catalogs publicly available datasets researched for the SECURE FOREST PATROL acoustic event classification project.

## Target Classes
- GUNSHOT
- CHAINSAW  
- BACKGROUND / NON-THREAT

---

## GUNSHOT DATASETS

### 1. C3GD (Certus Caliber Classification Gunshot Dataset)

**Source:** Stonewall Defense / Certus Innovations  
**URL:** https://github.com/Stonewall-Defense/C3GD  
**DOI:** https://doi.org/10.5281/zenodo.20274400  
**License:** Creative Commons Attribution 4.0 (CC BY 4.0)  
**License URL:** https://creativecommons.org/licenses/by/4.0/

**Dataset Details:**
- Size: 8,015 audio clips
- Firearms: 28 firearms across 16 calibers
- Recording conditions: Field-collected outdoor gunshots
- Audio format: WAV files
- Metadata: Detailed (class, event, platform, microphone, file ID)
- Sample rate: Not specified in initial research
- Channels: Not specified in initial research
- Label quality: High - field-collected with detailed metadata
- Source diversity: High - multiple firearms, calibers, microphones, locations
- Download size: ~430 MB

**Relevant Classes:**
- Gunshot (multiple calibers)
- Can be used for gunshot detection

**Potential Problems:**
- Focused on caliber classification rather than detection
- May be primarily outdoor range conditions
- Sample rate and channel format need verification

**Suitability:** HIGH - Purpose-built for gunshot analysis, high-quality metadata, permissive license

### 2. Certus DCASE 2026 Gunshot Classification Audio Dataset

**Source:** Certus Innovations  
**URL:** https://doi.org/10.5281/zenodo.20737298  
**License:** Likely CC BY (based on Certus practices)  
**Publication:** DCASE 2026 Challenge submission

**Dataset Details:**
- Size: Largest-known general-purpose open-access gunshot dataset
- Composition: 4 existing datasets + ~4,800 new samples
- Component datasets:
  - Gunshot/Gunfire Audio Dataset
  - Gunshot Audio Forensics Dataset
  - The Free Firearm Sound Library
  - C3GD
- Total: ~22,306 recordings across 21 calibers
- Firearms: 85 unique firearms
- Purpose: DCASE 2026 submission

**Relevant Classes:**
- Gunshot (comprehensive coverage)

**Potential Problems:**
- License needs verification
- Combines multiple datasets with potentially different licenses
- Very large dataset may be challenging to download

**Suitability:** HIGH - Most comprehensive gunshot dataset, but license verification needed

### 3. Gunshot sound files from passive acoustic monitoring data in Vietnam

**Source:** Chu Mom Ray National Park, Vietnam + Belize dataset  
**URL:** https://doi.org/10.5281/zenodo.13893977  
**License:** Open (Zenodo default)  
**Publication:** 2024

**Dataset Details:**
- Size: Multiple recordings (exact count not specified)
- Format: WAV audio files + spectrogram images
- Recording method: Passive acoustic monitoring
- Location: Chu Mom Ray National Park, Vietnam + Belize
- Purpose: Benchmarking automated gunshot detection models
- Publication: Vu, T. T., et al. (2024)

**Relevant Classes:**
- Gunshot events in forest environments
- Background forest noise

**Potential Problems:**
- Specific sample count and audio quality details need verification
- License terms need verification
- Geographic specificity (Vietnam/Belize only)

**Suitability:** HIGH for forest deployment - Real forest conditions, authentic monitoring context

### 4. Dataset of Gunshot Sounds from Gabon

**Source:** Yoh et al. 2024 study  
**URL:** https://doi.org/10.5281/zenodo.11192704  
**License:** Open (Zenodo default)  
**Publication:** "Impacts of logging, hunting, and conservation on vocalizing biodiversity in Gabon"

**Dataset Details:**
- Size: Hundreds of audio recordings
- Training data: 203 + 223 gunshot annotations
- Non-gunshot data: 8,614 annotations (branch snaps, tree falls, monkey calls, ambient noise)
- Format: WAV audio files + Raven Pro selection tables
- Location: Gabon (forest environment)
- Purpose: Gun-hunting pattern analysis

**Relevant Classes:**
- Gunshot events
- Forest background sounds
- Non-gunshot forest events

**Potential Problems:**
- License needs verification
- Specific geographic location (Gabon only)
- Requires Raven Pro for annotation processing

**Suitability:** HIGH for forest deployment - Authentic forest conditions, comprehensive background data

---

### 2. Gunshot Audio Forensics Dataset

**Source:** CADRE Forensics / NIJ Grant 2016-DN-BX-0183  
**URL:** https://cadreforensics.com/audio/  
**License:** Research use "as-is" (no explicit license specified)  
**Citation:** NIJ Grant 2016-DN-BX-0183 "Development of Computational Methods for the Audio Analysis of Gunshots"

**Dataset Details:**
- Size: ~10,000 individual gunshot recordings
- Firearms: 20 firearms
- Recording positions: 20 different positions per firearm
- Recording devices: 4 different recording devices
- Recording conditions: Summer 2017, rural Arizona
- Audio format: Not specified
- Sample rate: Not specified
- Channels: Not specified
- Label quality: High - controlled field recordings
- Source diversity: High - multiple devices, positions, firearms

**Relevant Classes:**
- Gunshot (multiple firearms and conditions)

**Potential Problems:**
- License unclear for redistribution/commercial use
- "As-is" provision with no guarantees
- Limited geographic diversity (Arizona only)
- Audio specifications need verification

**Suitability:** MEDIUM - High quality data but license restrictions

---

### 3. Certus DCASE 2026 Gunshot Classification Audio Dataset

**Source:** Certus Innovations  
**URL:** https://doi.org/10.5281/zenodo.20737299  
**License:** Not specified in initial research (likely CC BY based on Certus practices)

**Dataset Details:**
- Size: Largest-known general-purpose open-access gunshot dataset
- Composition: 4 existing datasets + ~4,800 new samples
- Component datasets:
  - Gunshot/Gunfire Audio Dataset
  - Gunshot Audio Forensics Dataset
  - The Free Firearm Sound Library
  - C3GD
- Total: ~22,306 recordings across 21 calibers
- Firearms: 85 unique firearms
- Purpose: DCASE 2026 submission

**Relevant Classes:**
- Gunshot (comprehensive coverage)

**Potential Problems:**
- License needs verification
- Combines multiple datasets with potentially different licenses
- Very large dataset may be challenging to download

**Suitability:** HIGH - Most comprehensive gunshot dataset, but license verification needed

---

### 4. Gunshot/Gunfire Audio Dataset

**Source:** Zenodo  
**URL:** https://zenodo.org/records/7004819  
**License:** Open (likely CC-BY based on Zenodo defaults)

**Dataset Details:**
- Size: Not specified
- Recording conditions: Outdoor firearm range
- Devices: Multiple edge devices positioned around shooter
- Purpose: Gunshot detection, firearm classification, direction of arrival
- Applications: Internet-of-Battlefield-Things (IoBT) systems

**Relevant Classes:**
- Gunshot/Gunfire

**Potential Problems:**
- Specific size and audio quality details need verification
- License terms need verification

**Suitability:** MEDIUM - Relevant but needs detailed investigation

---

## CHAINSAW DATASETS

### 1. RFCx FrugalAI Chainsaw Dataset

**Source:** Rainforest Connection (RFCx)  
**URL:** https://huggingface.co/datasets/rfcx/frugalai  
**License:** Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0)  
**License URL:** https://creativecommons.org/licenses/by-nc/4.0/

**Dataset Details:**
- Size: Large set of short audio clips (94.6M total dataset size)
- Duration: 3 seconds per clip
- Sample rate: Typically 12 kHz (original Guardian device recordings)
- Format: Opus format (lossy compression) for upload
- Source: Guardian devices deployed in forests (South America, Southeast Asia)
- Time period: 2015-2022
- Classes: Binary classification (chainsaw=0, environment=1)
- Label quality: High - field recordings from actual forest deployments
- Source diversity: High - multiple geographic regions, real forest conditions
- Last updated: January 31, 2025

**Relevant Classes:**
- Chainsaw (positive class)
- Environment/Background (negative class)

**Potential Problems:**
- Non-commercial license (CC BY-NC 4.0) restricts commercial use
- Lossy compression (Opus) may affect audio quality
- 12 kHz sample rate requires resampling to 16 kHz
- Human voices removed (may not represent all forest scenarios)

**Suitability:** HIGH for research - Real forest conditions, purpose-built for chainsaw detection in forests

---

### 2. Environmental Audio Recordings with Chainsaw Events (Greece)

**Source:** Zenodo  
**URL:** https://doi.org/10.5281/zenodo.5824433  
**License:** Open (likely CC-BY based on Zenodo defaults)

**Dataset Details:**
- Size: Multiple recordings (exact count not specified)
- Duration: Various durations
- Sample rate: 8 kHz
- Format: WAV
- Recording devices: 8 Cornell University SWIFT Autonomous Recording Units (ARUs)
- Location: Rodopi Mountain-Range National Park, Greece
- Time period: 2018-2019, different seasons
- Metadata: TextGrid files with temporal locations of chainsaw events
- Label quality: High - manually located by human listeners
- Source diversity: Medium - single national park, multiple seasons

**Relevant Classes:**
- Chainsaw events (marked in TextGrid files)
- Background environmental sounds

**Potential Problems:**
- 8 kHz sample rate requires resampling to 16 kHz
- Requires TextGrid parsing to extract chainsaw segments
- Limited geographic diversity (single national park)
- License needs verification

**Suitability:** MEDIUM - High quality but requires preprocessing and license verification

---

### 3. FSC22 Forest Environmental Sound Classification Dataset

**Source:** IEEE DataPort  
**URL:** https://ieee-dataport.org/documents/fsc22-dataset  
**License:** Not specified in initial research

**Dataset Details:**
- Size: 2,025 labeled sound clips
- Duration: 5 seconds per clip
- Source: FreeSound.org API
- Classes: 6 parent classes, 34 total classes
- Parent classes:
  - Mechanical sounds
  - Animal sounds
  - Environmental Sounds
  - Vehicle Sounds
  - Forest Threat Sounds
  - Human Sounds
- Label quality: High - manually validated through listening
- Source diversity: High - from FreeSound global community

**Relevant Classes:**
- Chainsaw (likely under Forest Threat Sounds or Mechanical sounds)
- Various environmental/background sounds
- Other forest-relevant sounds

**Potential Problems:**
- License needs verification
- From FreeSound - may have diverse individual licenses
- 5-second duration may need segmentation
- Dataset created from FreeSound API queries

**Suitability:** MEDIUM - Contains chainsaw and environmental sounds but license complexity

---

## ENVIRONMENTAL/BACKGROUND DATASETS

### 1. ESC-50 (Dataset for Environmental Sound Classification)

**Source:** Karol Piczak  
**URL:** https://github.com/karolpiczak/ESC-50  
**License:** Creative Commons Attribution-NonCommercial 3.0 (CC BY-NC 3.0)  
**License URL:** http://creativecommons.org/licenses/by-nc/3.0/  
**Citation:** Piczak, K. (2015). ESC: Dataset for Environmental Sound Classification

**Dataset Details:**
- Size: 2,000 environmental audio recordings
- Classes: 50 classes
- Duration: 5 seconds per clip
- Sample rate: 44.1 kHz
- Format: WAV
- Source: Freesound.org public field recordings
- Folds: 5 pre-arranged folds (no source leakage across folds)
- Label quality: High - manually extracted and labeled
- Source diversity: High - from global Freesound community

**Relevant Classes:**
- Chainsaw (class 40)
- Gunshot (not directly present)
- Background: rain, wind, birds, insects, thunderstorm, etc.
- Environmental: natural soundscapes, water sounds
- Human non-speech: footsteps, clapping, etc.
- Urban: siren, car horn, engine, etc.

**Potential Problems:**
- Non-commercial license (CC BY-NC 3.0)
- No direct gunshot class
- 44.1 kHz requires downsampling to 16 kHz
- 5-second duration may need segmentation

**Suitability:** HIGH for background - Excellent environmental diversity, well-structured, permissive for research

### 2. FSD50K (Freesound Dataset 50K)

**Source:** Music Technology Group, Universitat Pompeu Fabra  
**URL:** https://zenodo.org/records/4060432  
**License:** Creative Commons Attribution 4.0 (CC BY 4.0)  
**License URL:** https://creativecommons.org/licenses/by/4.0/

**Dataset Details:**
- Size: 51,197 Freesound clips
- Duration: 108.3 hours of multi-labeled audio
- Classes: 200 sound classes (144 leaf nodes, 56 intermediate nodes)
- Source: Freesound.org
- Organization: Hierarchically organized with AudioSet Ontology
- Label quality: High - manually labeled using Freesound Annotator platform
- Source diversity: Very high - global Freesound community
- Multi-label: Clips can have multiple labels

**Relevant Classes:**
- Gunshot / Gunfire (present in AudioSet ontology)
- Chainsaw (present in AudioSet ontology)
- Extensive environmental/background classes
- Mechanical, natural, human, animal sounds

**Potential Problems:**
- Large dataset size (108.3 hours)
- Multi-label complexity may require processing
- Some classes may have limited samples
- Audio quality varies across Freesound contributors

**Suitability:** VERY HIGH - Largest open environmental dataset, permissive license, comprehensive class coverage

### 3. DataSEC - Dataset for Sound Event Classification

**Source:** Environmental noise research  
**URL:** https://zenodo.org/records/17033970  
**License:** Open (Zenodo default)  
**Publication:** Scientific Data, 2025

**Dataset Details:**
- Size: 4,292 audio samples
- Duration: 18 hours 26 minutes total
- Sample rate: 44.1 kHz
- Format: Mono-channel WAV
- Classes: 22 defined sound classes, 28 subclasses
- Source: Sound level measurements + online repositories
- Environment: Urban to rural settings
- Label quality: High - meticulously gathered and analyzed
- Authenticity: Non-synthesized, authentic outdoor recordings

**Relevant Classes:**
- Thunder, fireworks, and gunshot (subclass)
- Birds, cicadas, crickets
- Various environmental and mechanical sounds
- Urban and rural environmental noise

**Potential Problems:**
- Gunshot grouped with thunder/fireworks (may need separation)
- Geographic diversity not specified
- License needs verification

**Suitability:** HIGH - Authentic environmental noise, recent publication, comprehensive classes

### 4. UN15 Urban Noise Dataset

**Source:** Urban acoustic research  
**URL:** https://doi.org/10.3390/app15158413  
**License:** Open (likely CC BY based on publication)  
**Publication:** Applied Sciences, 2025

**Dataset Details:**
- Size: Large urban noise dataset (exact count not specified)
- Purpose: Urban acoustic management and environmental sound classification
- Focus: Time-frequency attention for ESC
- Context: Smart cities, ecological monitoring, public safety
- Publication: Recent (2025)

**Relevant Classes:**
- Urban environmental sounds
- Traffic and transportation noise
- Human activity sounds
- Background urban ambience

**Potential Problems:**
- Urban focus may not represent forest environments
- Specific size and class details need verification
- License needs verification

**Suitability:** MEDIUM - Comprehensive urban data but may not match forest deployment conditions

---

### 2. UrbanSound8K

**Source:** NYU / Zenodo  
**URL:** https://zenodo.org/records/1203745  
**License:** Not specified in initial research (likely research use)  
**Citation:** Salamon, J., Jacoby, C., & Bello, J. P. (2014). A Dataset and Taxonomy for Urban Sound Research

**Dataset Details:**
- Size: 8,732 labeled sound excerpts
- Duration: ≤4 seconds per excerpt
- Classes: 10 classes
- Sample rate: Variable (same as original Freesound uploads)
- Format: WAV
- Source: Freesound.org field recordings
- Folds: 10 pre-arranged folds
- Metadata: Detailed (fsID, start/end times, salience, fold)

**Relevant Classes:**
- gun_shot (class 6)
- Background: air_conditioner, children_playing, dog_bark, drilling, engine_idling, jackhammer, siren, street_music
- Environmental: various urban sounds

**Potential Problems:**
- License needs verification
- Variable sample rates require standardization
- Urban focus may not represent forest environments
- Gunshot class present but may be urban context

**Suitability:** MEDIUM - Contains gunshot but urban context, needs license verification

---

### 3. Sensing the Forest - Natural Soundscape Dataset

**Source:** AHRC Sensing the Forest Project  
**URL:** https://zenodo.org/records/18909809  
**License:** Creative Commons 0 (CC0 1.0 - Public Domain)  
**License URL:** https://creativecommons.org/publicdomain/zero/1.0/

**Dataset Details:**
- Size: Part 1 of 2 (August 2024 - March 2025)
- Duration: 4 recordings per day (sunrise, solar noon, sunset, midpoint)
- Format: WAV
- Sample rate: Not specified
- Location: Alice Holt Lodge Pond, Surrey, UK
- Habitat: Corsican pine with mixed broadleaf species
- Wildlife: Roe deer, muntjac deer, bats, various bird species
- Recording method: Automatic solar-powered recording

**Relevant Classes:**
- Realistic forest background sounds
- Birds, wind, natural ambience
- No specific threat events

**Potential Problems:**
- No labeled threat events (gunshot, chainsaw)
- Primarily background/environmental
- Part 1 only (need Part 2 for complete dataset)
- Sample rate needs verification

**Suitability:** HIGH for background - Authentic forest conditions, public domain license

---

### 4. dB@risoux Forest Soundscape Dataset

**Source:** Parc Naturel Régional du Haut-Jura  
**URL:** https://doi.org/10.5281/zenodo.14856482  
**License:** Not specified in initial research

**Dataset Details:**
- Size: 35,023 1-minute audio recordings
- Duration: 1 minute per recording
- Time period: Full year 2019 (1 min every 15 min, day and night)
- Format: Not specified
- Sample rate: Not specified
- Location: Risoux Forest, Jura Mountains, France (46°31'60.0"N 6°05'03.8"E)
- Habitat: Cold temperate climax forest, European spruce dominated
- Recording device: SongMeter 4 (Wildlife Acoustics Inc.)
- Soundscape composition: Biophony (birds, insects, deer), geophony (rain, wind), technophony (planes, chainsaws, gun shots, sheep bells)

**Relevant Classes:**
- Comprehensive forest background
- Contains occasional chainsaws and gunshots (not labeled)
- Year-round coverage (seasonal variation)

**Potential Problems:**
- Threat events not explicitly labeled
- Very large dataset (35,023 files)
- License needs verification
- Requires manual annotation or detection of threat events

**Suitability:** MEDIUM - Excellent forest background but threat events unlabeled

---

### 5. Large-scale Acoustic Forest Soundscape Dataset (Avian Vocalizations)

**Source:** Northeastern USA Parks Research  
**URL:** https://zenodo.org/records/20038954  
**License:** Not specified in initial research

**Dataset Details:**
- Size: 1,302 10-minute soundscape recordings
- Annotations: ~183,000 vocalizations labeled for 96 bird species
- Duration: 10 minutes per recording
- Sample rate: 32 kHz
- Resolution: 16-bit
- Locations: 4 parks in Northeastern USA (Acadia, Hubbard Brook, Katahdin Woods, Marsh-Billings-Rockefeller)
- Time period: May-July 2022-2023 (breeding season)
- Recording device: SwiftOne recorders with omnidirectional microphone
- Microphone sensitivity: -25 dB re 1V/Pa, SNR: 62 dB

**Relevant Classes:**
- Rich bird vocalizations (96 species)
- Forest background sounds
- No gunshot or chainsaw events

**Potential Problems:**
- Focus on bird vocalizations, not threat detection
- No threat event labels
- License needs verification
- Breeding season only (no seasonal diversity)

**Suitability:** LOW for threat detection - Excellent for bird sounds but no threat events

---

## COMBINED DATASETS

### AudioSet

**Source:** Google Research  
**URL:** https://research.google.com/audioset/  
**License:** Creative Commons Attribution 4.0 (CC BY 4.0) for dataset, CC BY-SA 4.0 for ontology  
**License URL:** https://creativecommons.org/licenses/by/4.0/

**Dataset Details:**
- Size: 2,084,320 YouTube videos with 527 labels
- Duration: 10-second clips
- Source: YouTube videos
- Classes: 527 sound event classes
- Includes: Gunshot, Chainsaw, and many environmental sounds
- Strong labeling available for subset (120,459 clips with temporal annotations)

**Relevant Classes:**
- Gunshot / Gunshot sounds
- Chainsaw
- Extensive environmental/background classes

**Potential Problems:**
- Cannot redistribute audio (YouTube Terms of Service violation)
- Only features/annotations legally downloadable
- Audio quality varies (YouTube compression)
- Requires YouTube API access for original audio
- Mixed licenses from YouTube content creators

**Suitability:** LOW for this project - License restrictions prevent audio redistribution, critical limitation

### GESMA (Ghanaian Environmental Soundscapes for Machine Learning)

**Source:** Ghanaian environmental research  
**URL:** https://doi.org/10.1016/j.dib.2026.112732  
**License:** Open (likely CC BY based on publication)  
**Publication:** Data in Brief, 2026

**Dataset Details:**
- Size: 22,193 uncompressed recordings
- Sample rate: 44.1 kHz, 16-bit
- Format: WAV
- Duration: Various durations
- Environments: Urban spaces, educational institutions, marketplaces, transport hubs, human non-verbal settings
- Recording method: Mobile devices under natural field conditions
- Geographic: Sub-Saharan Africa (Ghana)
- Metadata: Category, class, subclass, location, context
- Label quality: High - manually verified

**Relevant Classes:**
- Environmental soundscapes
- Background noise diversity
- Human and environmental sounds
- Geographic diversity (Sub-Saharan Africa)

**Potential Problems:**
- Geographic specificity (Ghana only)
- Urban/educational focus may not match forest deployment
- License needs verification
- No specific threat event classes

**Suitability:** MEDIUM - Excellent geographic diversity and authentic conditions, but urban focus

---

## DATASET SELECTION CRITERIA

### Priorities:
1. **Relevance to forest acoustic detection**
2. **Label quality and reliability**
3. **Class availability (gunshot, chainsaw, background)**
4. **Audio quality and standardization potential**
5. **Source diversity (environments, devices, conditions)**
6. **Licensing (redistribution and commercial use)**
7. **Dataset size and trainability**
8. **Suitability for edge deployment (16kHz, mono)**
9. **Research evaluation support**
10. **Ability to combine multiple datasets**

### License Analysis:
- **CC BY 4.0**: C3GD, AudioSet - Permissive, requires attribution
- **CC BY-NC 4.0**: RFCx FrugalAI, ESC-50 - Non-commercial only
- **CC0 1.0**: Sensing the Forest - Public domain, most permissive
- **Unknown/Research-only**: Several datasets need license verification

### Key Findings:
1. **Gunshot data**: C3GD provides high-quality, licensed gunshot data
2. **Chainsaw data**: RFCx FrugalAI provides real forest chainsaw data but non-commercial
3. **Background data**: ESC-50 provides diverse environmental sounds, Sensing the Forest provides authentic forest ambience
4. **Combined gunshot**: Certus DCASE 2026 provides largest collection but license verification needed
5. **License complexity**: Multiple datasets have NC restrictions or unclear terms

### Recommended Approach:
Combine datasets with compatible licenses for research use, document restrictions clearly, and prioritize datasets that can be legally redistributed where possible.

---

## UPDATED DATASET RECOMMENDATIONS (2024-2025)

### Priority 1: High-Value Public Datasets (Immediate Action)

#### Gunshot Data
1. **C3GD** (8,015 clips) - HIGH PRIORITY
   - License: CC BY 4.0 (commercial use allowed)
   - Quality: Field-collected, detailed metadata
   - Diversity: 28 firearms, 16 calibers
   - Download: ~430 MB from Zenodo

2. **Certus DCASE 2026** (~22,306 clips) - HIGH PRIORITY
   - License: Likely CC BY (verification needed)
   - Quality: Largest open gunshot dataset
   - Diversity: 85 firearms, 21 calibers
   - Comprehensive coverage

3. **Vietnam Passive Monitoring** - HIGH PRIORITY for forest deployment
   - License: Open (verification needed)
   - Quality: Real forest conditions
   - Context: Authentic monitoring setup
   - Geographic: Vietnam + Belize

#### Chainsaw Data
1. **RFCx FrugalAI** - HIGH PRIORITY for research
   - License: CC BY-NC 4.0 (non-commercial only)
   - Quality: Real forest deployments
   - Diversity: South America, Southeast Asia
   - Context: Illegal logging detection

2. **Greece Chainsaw Dataset** - MEDIUM PRIORITY
   - License: Open (verification needed)
   - Quality: Manual annotation, TextGrid metadata
   - Context: National park monitoring
   - Geographic: Rodopi Mountain-Range, Greece

#### Background/Environmental Data
1. **FSD50K** (51,197 clips) - VERY HIGH PRIORITY
   - License: CC BY 4.0 (commercial use allowed)
   - Quality: Largest open environmental dataset
   - Diversity: 200 classes, global sources
   - Multi-label support

2. **ESC-50** (2,000 clips) - HIGH PRIORITY
   - License: CC BY-NC 3.0 (non-commercial only)
   - Quality: Well-established benchmark
   - Diversity: 50 environmental classes
   - Structured folds for validation

3. **DataSEC** (4,292 clips) - HIGH PRIORITY
   - License: Open (verification needed)
   - Quality: Authentic outdoor recordings
   - Diversity: 22 classes, 28 subclasses
   - Recent publication (2025)

### Priority 2: Forest-Specific Datasets (Medium Priority)

1. **FSC22** (2,025 clips) - FOREST-SPECIFIC
   - License: Open (verification needed)
   - Quality: Purpose-built for forest sounds
   - Diversity: 27 forest-specific classes
   - Context: Illegal activity detection

2. **Sensing the Forest** - FOREST-SPECIFIC
   - License: CC0 1.0 (public domain)
   - Quality: Authentic forest soundscapes
   - Context: Long-term monitoring
   - Geographic: United Kingdom

### Priority 3: Geographic Diversity (Long-term Priority)

1. **Gabon Gunshot Dataset** - AFRICAN FOREST
   - License: Open (verification needed)
   - Quality: Real forest hunting context
   - Diversity: Gunshot + comprehensive background
   - Geographic: Gabon

2. **GESMA** - SUB-SAHARAN AFRICA
   - License: Open (verification needed)
   - Quality: Authentic field conditions
   - Diversity: Urban to rural environments
   - Geographic: Ghana

---

## DATASET INTEGRATION STRATEGY

### Phase 1: Minimum Viable Dataset (200 recordings)
**Gunshot (50 recordings):**
- C3GD: 30 recordings (diverse calibers)
- Vietnam dataset: 20 recordings (forest context)

**Chainsaw (50 recordings):**
- RFCx FrugalAI: 40 recordings (forest conditions)
- Greece dataset: 10 recordings (different geography)

**Background (100 recordings):**
- FSD50K: 50 recordings (diverse environments)
- ESC-50: 30 recordings (well-structured)
- DataSEC: 20 recordings (authentic outdoor)

### Phase 2: Target Research Dataset (800 recordings)
**Gunshot (200 recordings):**
- C3GD: 100 recordings
- Certus DCASE 2026: 80 recordings
- Vietnam dataset: 20 recordings

**Chainsaw (200 recordings):**
- RFCx FrugalAI: 150 recordings
- Greece dataset: 30 recordings
- FSC22 chainsaw class: 20 recordings

**Background (400 recordings):**
- FSD50K: 200 recordings
- ESC-50: 100 recordings
- DataSEC: 50 recordings
- FSC22 background classes: 50 recordings

### Phase 3: Ideal Dataset (2,000+ recordings)
**Gunshot (500+ recordings):**
- Certus DCASE 2026: 300 recordings
- C3GD: 150 recordings
- Vietnam dataset: 30 recordings
- Gabon dataset: 20+ recordings

**Chainsaw (500+ recordings):**
- RFCx FrugalAI: 400 recordings
- Greece dataset: 50 recordings
- FSC22 chainsaw: 30 recordings
- Additional field collection: 20+ recordings

**Background (1,000+ recordings):**
- FSD50K: 500 recordings
- ESC-50: 200 recordings
- DataSEC: 100 recordings
- FSC22: 100 recordings
- Sensing the Forest: 50+ recordings
- GESMA: 50+ recordings

---

## LICENSE COMPATIBILITY MATRIX

| Dataset | License | Commercial Use | Research Use | Redistribution |
|---------|---------|----------------|--------------|----------------|
| C3GD | CC BY 4.0 | ✅ Yes | ✅ Yes | ✅ Yes |
| Certus DCASE 2026 | Likely CC BY | ⚠️ Verify | ✅ Yes | ⚠️ Verify |
| Vietnam Gunshot | Open | ⚠️ Verify | ✅ Yes | ⚠️ Verify |
| Gabon Gunshot | Open | ⚠️ Verify | ✅ Yes | ⚠️ Verify |
| RFCx FrugalAI | CC BY-NC 4.0 | ❌ No | ✅ Yes | ⚠️ With attribution |
| Greece Chainsaw | Open | ⚠️ Verify | ✅ Yes | ⚠️ Verify |
| FSD50K | CC BY 4.0 | ✅ Yes | ✅ Yes | ✅ Yes |
| ESC-50 | CC BY-NC 3.0 | ❌ No | ✅ Yes | ⚠️ With attribution |
| DataSEC | Open | ⚠️ Verify | ✅ Yes | ⚠️ Verify |
| FSC22 | Open | ⚠️ Verify | ✅ Yes | ⚠️ Verify |
| Sensing the Forest | CC0 1.0 | ✅ Yes | ✅ Yes | ✅ Yes |
| GESMA | Open | ⚠️ Verify | ✅ Yes | ⚠️ Verify |

**License Strategy:**
- **Research Phase:** All datasets can be used
- **Commercial Deployment:** Prioritize CC BY and CC0 datasets
- **Non-commercial datasets:** Use for research, plan commercial alternatives for production

---

## CRITICAL NEXT STEPS

1. **Immediate:** Download and verify C3GD dataset (CC BY 4.0)
2. **Immediate:** Download and verify FSD50K dataset (CC BY 4.0)
3. **High Priority:** Verify Certus DCASE 2026 license terms
4. **High Priority:** Access RFCx FrugalAI for research (document NC restriction)
5. **Medium Priority:** Contact dataset authors for license clarifications
6. **Medium Priority:** Begin field data collection protocol development
7. **Long-term:** Plan commercial license alternatives for production deployment
