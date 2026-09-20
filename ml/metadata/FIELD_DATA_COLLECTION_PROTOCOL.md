# Field Data Collection Protocol

## Overview

This document defines the standardized protocol for collecting field audio data to supplement public datasets for the SECURE FOREST PATROL acoustic classification system. Field data collection is essential for capturing the domain-specific characteristics of actual forest deployment environments that may not be present in public datasets.

---

## Objectives

1. **Domain Alignment:** Capture audio that matches actual deployment conditions
2. **Environmental Diversity:** Record across different forest types, weather, and seasons
3. **Device Consistency:** Use deployment-compatible recording equipment
4. **Metadata Quality:** Maintain comprehensive, structured metadata for all recordings
5. **Safety Compliance:** Ensure all data collection follows safety and legal requirements

---

## Recording Equipment Specifications

### Primary Microphone
- **Model:** INMP441 (deployment target) or equivalent
- **Type:** Omnidirectional MEMS microphone
- **Sample Rate:** 16,000 Hz (16 kHz)
- **Bit Depth:** 16-bit
- **Channels:** Mono
- **Frequency Response:** 20 Hz - 20 kHz
- **Sensitivity:** -26 dB FS ± 1 dB
- **SNR:** 62 dB

### Alternative Microphones (for comparison)
- **Secondary Option:** High-quality USB microphone
- **Sample Rate:** 44.1 kHz or 48 kHz (downsample to 16 kHz later)
- **Bit Depth:** 16-bit or 24-bit
- **Channels:** Mono or stereo (convert to mono)

### Recording Device
- **Primary:** ESP32-S3 with INMP441 (deployment target)
- **Alternative:** Dedicated audio recorder (Zoom, Tascam, etc.)
- **Storage:** Minimum 32 GB SD card
- **Power:** Battery with solar charging capability
- **Mounting:** Weatherproof enclosure, elevated positioning (3-5m height)

### Calibration Equipment
- **Reference Sound Source:** Calibrated speaker for frequency response testing
- **Sound Level Meter:** For recording ambient noise levels
- **GPS Device:** For precise location tagging

---

## Recording Standards

### Audio Specifications
- **Sample Rate:** 16,000 Hz (16 kHz)
- **Bit Depth:** 16-bit
- **Channels:** Mono
- **Format:** WAV (uncompressed)
- **Duration:** Variable (see specific class requirements)
- **Normalization:** None during recording (preserve original dynamics)

### Quality Requirements
- **Clipping:** No clipping (peak amplitude < -1 dB)
- **Noise Floor:** Record ambient noise floor before/after events
- **Signal-to-Noise Ratio:** Minimum 10 dB for target events
- **Background:** Include representative background in all recordings

### File Naming Convention
```
{CLASS}_{LOCATION}_{DATE}_{TIME}_{DEVICE_ID}_{SESSION_ID}_{TAKE}.wav
```

Example: `gunshot_forest_a_20240919_1430_esp32_001_001.wav`

---

## Class-Specific Collection Protocols

### BACKGROUND CLASS

#### Target Subcategories
1. **Quiet Forest** - Minimal human/animal activity
2. **Wind** - Various wind conditions (calm to strong)
3. **Rain** - Light to heavy rain
4. **Insects** - Cicadas, crickets, other insect sounds
5. **Birds** - Various bird vocalizations
6. **Human Movement** - Footsteps, walking, running
7. **Vehicles** - Distant vehicles, forest machinery
8. **Machinery** - Equipment operation, maintenance
9. **Distant Human Activity** - Voices, tools, other anthropogenic sounds
10. **Night Sounds** - Nocturnal animals, insects, ambient night noise

#### Recording Protocol
- **Duration:** 5-10 minutes per recording
- **Quantity:** Minimum 10 recordings per subcategory
- **Time of Day:** Cover dawn, day, dusk, night
- **Weather:** Record in various weather conditions
- **Season:** Cover all seasons where possible
- **Location:** Multiple forest types and densities

#### Distance Variations
- **Immediate:** 0-10m from microphone
- **Near:** 10-50m from microphone
- **Far:** 50-100m from microphone
- **Distant:** 100m+ from microphone

### CHAINSAW CLASS

#### Target Subcategories
1. **Idle** - Chainsaw running but not cutting
2. **Acceleration** - Revving up from idle
3. **Continuous Cutting** - Steady cutting operation
4. **Intermittent Cutting** - Start-stop cutting patterns
5. **Different Tree Species** - Cutting various wood types
6. **Different Operations** - Felling, limbing, bucking

#### Recording Protocol
- **Duration:** 30 seconds - 5 minutes per recording
- **Quantity:** Minimum 20 recordings per subcategory
- **Safety:** Only record with proper authorization and safety equipment
- **Distance:** 10m, 25m, 50m, 100m from source
- **Direction:** Record from multiple angles relative to source
- **Background:** Include representative forest background

#### Environmental Variations
- **Forest Type:** Different forest densities and compositions
- **Weather:** Various weather conditions
- **Time of Day:** Different acoustic conditions
- **Ground Conditions:** Dry, wet, snowy, leaf-covered

#### Safety Requirements
- **Authorization:** Only on authorized logging operations or controlled demonstrations
- **Safety Equipment:** Proper PPE (hearing protection, safety glasses, etc.)
- **Personnel:** Only trained operators should handle chainsaws
- **Permits:** Required for any recording in protected areas

### GUNSHOT CLASS

#### Target Subcategories
1. **Different Calibers** - Various firearm calibers
2. **Different Firearms** - Handguns, rifles, shotguns
3. **Different Distances** - 10m, 25m, 50m, 100m+
4. **Different Environments** - Open forest, dense forest, edge habitat
5. **Atmospheric Conditions** - Various weather and temperature conditions

#### Recording Protocol
- **Duration:** 5-30 seconds per recording (include pre/post event)
- **Quantity:** Minimum 10 recordings per subcategory
- **Safety:** ONLY use authorized shooting ranges or controlled demonstrations
- **Distance:** 10m, 25m, 50m, 100m from source
- **Background:** Include representative forest background

#### Safety and Legal Requirements
- **Authorization:** ONLY at authorized shooting ranges or with proper permits
- **Legal Compliance:** Follow all local, state, and federal regulations
- **Personnel:** Only trained firearms handlers
- **Safety Zones:** Maintain safe distances and follow range protocols
- **Permits:** Required for any recording outside authorized ranges
- **Notification:** Inform local authorities if recording in non-range areas

**IMPORTANT:** Do NOT perform unsafe or unauthorized firearm experiments. Use only legally obtained public/authorized recordings or controlled authorized data collection.

---

## Metadata Requirements

### Required Metadata Fields

#### Recording Information
- **recording_id:** Unique identifier (matches filename)
- **session_id:** Collection session identifier
- **date:** YYYY-MM-DD format
- **time:** HH:MM:SS format (local time)
- **timezone:** UTC offset
- **duration:** Recording duration in seconds
- **sample_rate:** Sample rate in Hz
- **bit_depth:** Bit depth (16, 24, etc.)
- **channels:** Number of channels (1 for mono)

#### Location Information
- **location_id:** Unique location identifier
- **latitude:** Decimal degrees
- **longitude:** Decimal degrees
- **elevation:** Meters above sea level
- **forest_type:** Forest classification (coniferous, deciduous, mixed, etc.)
- **canopy_density:** Percentage canopy cover
- **terrain:** Terrain description (flat, sloped, valley, ridge)
- **distance_to_water:** Meters to nearest water body

#### Environmental Conditions
- **weather:** Current weather (clear, cloudy, rain, snow, etc.)
- **temperature:** Temperature in Celsius
- **humidity:** Relative humidity percentage
- **wind_speed:** Wind speed in km/h
- **wind_direction:** Wind direction (N, NE, E, SE, S, SW, W, NW)
- **precipitation:** Current precipitation (none, light, moderate, heavy)
- **visibility:** Visibility distance in meters
- **atmospheric_pressure:** Atmospheric pressure in hPa

#### Acoustic Conditions
- **ambient_noise_level:** Ambient noise level in dB
- **noise_floor:** Noise floor in dB
- **signal_to_noise_ratio:** Estimated SNR in dB
- **reverberation:** Subjective reverberation assessment (low, medium, high)
- **background_description:** Description of background sounds

#### Equipment Information
- **device_id:** Unique device identifier
- **microphone_model:** Microphone model
- **microphone_orientation:** Microphone orientation relative to source
- **microphone_height:** Microphone height above ground in meters
- **recording_device:** Recording device model
- **firmware_version:** Device firmware version if applicable

#### Event Information (for target events)
- **event_type:** Type of event (gunshot, chainsaw, etc.)
- **event_start_time:** Event start time within recording
- **event_duration:** Event duration in seconds
- **event_distance:** Distance to event source in meters
- **event_direction:** Direction to event source (compass bearing)
- **event_description:** Detailed description of event

#### Personnel Information
- **recorder_name:** Name of person recording
- **recorder_contact:** Contact information
- **organization:** Organization responsible for collection
- **operator_name:** Name of event operator (if applicable)

#### Quality Assessment
- **audio_quality:** Subjective quality assessment (excellent, good, fair, poor)
- **clipping_present:** Boolean indicating clipping
- **interference:** Any interference present (yes/no, description)
- **notes:** Additional notes about the recording

#### Legal and Safety
- **collection_permission:** Permission status for collection
- **permit_number:** Permit number if applicable
- **safety_clearance:** Safety clearance status
- **data_usage_rights:** Usage rights for the data

### Metadata Format

#### CSV Format
```csv
recording_id,session_id,date,time,timezone,duration,sample_rate,bit_depth,channels,location_id,latitude,longitude,elevation,forest_type,canopy_density,terrain,distance_to_water,weather,temperature,humidity,wind_speed,wind_direction,precipitation,visibility,atmospheric_pressure,ambient_noise_level,noise_floor,signal_to_noise_ratio,reverberation,background_description,device_id,microphone_model,microphone_orientation,microphone_height,recording_device,firmware_version,event_type,event_start_time,event_duration,event_distance,event_direction,event_description,recorder_name,recorder_contact,organization,operator_name,audio_quality,clipping_present,interference,notes,collection_permission,permit_number,safety_clearance,data_usage_rights
```

#### JSON Format (Alternative)
```json
{
  "recording_id": "gunshot_forest_a_20240919_1430_esp32_001_001",
  "session_id": "session_20240919_001",
  "date": "2024-09-19",
  "time": "14:30:00",
  "timezone": "UTC-5",
  "duration": 15.5,
  "sample_rate": 16000,
  "bit_depth": 16,
  "channels": 1,
  "location_id": "forest_a",
  "latitude": 45.1234,
  "longitude": -93.1234,
  "elevation": 300,
  "forest_type": "mixed",
  "canopy_density": 75,
  "terrain": "sloped",
  "distance_to_water": 500,
  "weather": "clear",
  "temperature": 22,
  "humidity": 65,
  "wind_speed": 5,
  "wind_direction": "NW",
  "precipitation": "none",
  "visibility": 1000,
  "atmospheric_pressure": 1013,
  "ambient_noise_level": 45,
  "noise_floor": 35,
  "signal_to_noise_ratio": 25,
  "reverberation": "medium",
  "background_description": "Bird calls, light wind",
  "device_id": "esp32_001",
  "microphone_model": "INMP441",
  "microphone_orientation": "omnidirectional",
  "microphone_height": 4,
  "recording_device": "ESP32-S3",
  "firmware_version": "1.0",
  "event_type": "gunshot",
  "event_start_time": 2.5,
  "event_duration": 0.5,
  "event_distance": 50,
  "event_direction": 180,
  "event_description": "Rifle shot, .308 caliber",
  "recorder_name": "John Doe",
  "recorder_contact": "john@example.com",
  "organization": "Forest Patrol Project",
  "operator_name": "Jane Smith",
  "audio_quality": "excellent",
  "clipping_present": false,
  "interference": "none",
  "notes": "Clear recording, good signal",
  "collection_permission": "granted",
  "permit_number": "FP-2024-001",
  "safety_clearance": "approved",
  "data_usage_rights": "research_and_commercial"
}
```

---

## Collection Procedures

### Pre-Collection Preparation

#### Equipment Setup
1. **Calibration:** Calibrate microphone using reference sound source
2. **Testing:** Test recording equipment in controlled environment
3. **Battery Check:** Ensure sufficient battery power for session
4. **Storage Check:** Verify sufficient storage space on SD card
5. **Mounting:** Install microphone at appropriate height and orientation
6. **Weather Protection:** Ensure weatherproof enclosure is properly sealed

#### Location Assessment
1. **Survey:** Assess location for safety and suitability
2. **GPS:** Record precise GPS coordinates
3. **Environment:** Document environmental conditions
4. **Background:** Note background noise sources
5. **Permissions:** Verify all necessary permissions are obtained

#### Safety Check
1. **Weather:** Check weather forecast for safe conditions
2. **Terrain:** Assess terrain for safe equipment placement
3. **Wildlife:** Be aware of local wildlife and take precautions
4. **Emergency:** Plan emergency procedures and communication
5. **Authorization:** Verify authorization for target events

### During Collection

#### Recording Process
1. **Background Recording:** Record 30 seconds of ambient background before events
2. **Event Recording:** Record target event with appropriate duration
3. **Post-Event Recording:** Record 30 seconds of ambient background after events
4. **Quality Check:** Monitor recording levels to prevent clipping
5. **Real-time Notes:** Take real-time notes about conditions and events

#### Metadata Recording
1. **Real-time Entry:** Enter metadata in real-time when possible
2. **Field Notes:** Keep detailed field notes as backup
3. **Photos:** Take photos of setup and conditions
4. **GPS Logging:** Log GPS track if moving between locations
5. **Time Synchronization:** Ensure device time is synchronized

### Post-Collection Processing

#### Data Management
1. **File Organization:** Organize files by session and class
2. **Backup:** Create immediate backup of all recordings
3. **Quality Check:** Listen to recordings for quality issues
4. **Metadata Verification:** Verify metadata completeness and accuracy
5. **File Integrity:** Check file integrity (checksums)

#### Data Transfer
1. **Secure Transfer:** Transfer data using secure methods
2. **Verification:** Verify transfer completeness
3. **Storage:** Store in organized directory structure
4. **Cataloging:** Add to master catalog/database
5. **Backup:** Create secondary backup

---

## Quality Assurance

### Audio Quality Checks

#### Technical Quality
- **No Clipping:** Verify no clipping in recordings
- **Adequate SNR:** Minimum 10 dB SNR for target events
- **Consistent Levels:** Consistent recording levels across session
- **No Artifacts:** No electrical or mechanical artifacts
- **Proper Sample Rate:** Verify sample rate is correct

#### Content Quality
- **Clear Events:** Target events are clearly audible
- **Representative Background:** Background is representative of deployment
- **Appropriate Duration:** Recording duration is appropriate for class
- **Complete Metadata:** All required metadata is present
- **Accurate Labels:** Event labels are accurate

### Metadata Quality Checks

#### Completeness
- **Required Fields:** All required metadata fields are present
- **Valid Formats:** All fields follow specified formats
- **Consistent Units:** Units are consistent across recordings
- **Accurate Values:** Values are accurate and reasonable
- **No Missing Data:** No critical missing information

#### Accuracy
- **GPS Accuracy:** GPS coordinates are accurate
- **Time Accuracy:** Time stamps are accurate
- **Environmental Accuracy:** Environmental conditions are accurately recorded
- **Equipment Accuracy:** Equipment information is correct
- **Event Accuracy:** Event information is accurate

---

## Safety and Legal Requirements

### Safety Protocols

#### General Safety
- **Weather Monitoring:** Monitor weather conditions continuously
- **Emergency Communication:** Maintain emergency communication capability
- **First Aid:** Carry first aid kit and know emergency procedures
- **Buddy System:** Use buddy system when possible
- **Equipment Safety:** Ensure equipment is safely installed and operated

#### Firearms Safety (Gunshot Collection)
- **Authorized Ranges Only:** Only record at authorized shooting ranges
- **Trained Personnel:** Only trained firearms handlers
- **Safety Equipment:** Use appropriate safety equipment
- **Range Protocols:** Follow all range safety protocols
- **Never Unauthorized:** Never record unauthorized firearm use

#### Chainsaw Safety (Chainsaw Collection)
- **Authorized Operations Only:** Only record authorized logging operations
- **Trained Operators:** Only trained chainsaw operators
- **Safety Equipment:** Use appropriate PPE (hearing protection, safety glasses, etc.)
- **Safe Distances:** Maintain safe distances from operating equipment
- **Never Unauthorized:** Never record unauthorized chainsaw use

### Legal Requirements

#### Permissions and Permits
- **Landowner Permission:** Obtain permission from landowners
- **Government Permits:** Obtain required government permits
- **Forest Service Permits:** Obtain forest service permits if applicable
- **Shooting Range Authorization:** Obtain range authorization for gunshot recording
- **Logging Authorization:** Obtain authorization for chainsaw recording

#### Data Collection Regulations
- **Privacy Laws:** Comply with privacy laws (avoid recording identifiable conversations)
- **Environmental Regulations:** Comply with environmental protection regulations
- **Wildlife Regulations:** Comply with wildlife protection regulations
- **Local Ordinances:** Comply with local noise and recording ordinances
- **Indigenous Rights:** Respect indigenous land rights and regulations

#### Data Usage Rights
- **Clear Documentation:** Document data usage rights clearly
- **License Specification:** Specify license for collected data
- **Attribution Requirements:** Document attribution requirements
- **Commercial Use:** Specify commercial use permissions
- **Sharing Restrictions:** Document any sharing restrictions

---

## Storage and Backup

### Primary Storage
- **Location:** Secure, climate-controlled storage
- **Format:** Original WAV files + metadata
- **Organization:** Organized by date, session, and class
- **Access:** Controlled access with proper authentication
- **Redundancy:** RAID storage for data protection

### Backup Storage
- **Primary Backup:** Offsite backup with different geographic location
- **Secondary Backup:** Cloud backup with encryption
- **Frequency:** Regular backup schedule (daily/weekly)
- **Verification:** Regular backup verification and testing
- **Retention:** Long-term retention policy

### Data Management
- **Cataloging:** Maintain master catalog of all recordings
- **Version Control:** Track versions and changes
- **Access Logs:** Maintain access logs for security
- **Data Lifecycle:** Define data lifecycle and retention policies
- **Disposal:** Secure disposal when data is no longer needed

---

## Documentation and Reporting

### Collection Reports
- **Session Reports:** Report for each collection session
- **Summary Reports:** Summary reports by time period
- **Quality Reports:** Quality assessment reports
- **Issue Reports:** Report any issues or problems encountered
- **Completion Reports:** Report completion of collection goals

### Metadata Documentation
- **Data Dictionary:** Document all metadata fields and formats
- **Collection Standards:** Document collection standards and procedures
- **Quality Standards:** Document quality standards and criteria
- **Procedural Changes:** Document any changes to procedures
- **Lessons Learned:** Document lessons learned and best practices

### Technical Documentation
- **Equipment Documentation:** Document all equipment and configurations
- **Software Documentation:** Document software and versions used
- **Processing Documentation:** Document any processing applied to data
- **Format Documentation:** Document file formats and specifications
- **API Documentation:** Document any APIs or tools used for data management

---

## Timeline and Phasing

### Phase 1: Pilot Collection (2-4 weeks)
- **Objective:** Test collection protocols and equipment
- **Target:** 50 recordings (mixed classes)
- **Focus:** Background and chainsaw (easier to obtain safely)
- **Locations:** 2-3 accessible forest locations
- **Evaluation:** Assess protocols, equipment, and data quality

### Phase 2: Minimum Viable Dataset (4-8 weeks)
- **Objective:** Achieve minimum viable dataset (200 recordings)
- **Target:** 200 recordings (50 gunshot, 50 chainsaw, 100 background)
- **Locations:** 5-10 forest locations
- **Conditions:** Various weather and time conditions
- **Evaluation:** Assess dataset quality and completeness

### Phase 3: Target Research Dataset (3-6 months)
- **Objective:** Achieve target research dataset (800 recordings)
- **Target:** 800 recordings (200 per class)
- **Locations:** 15-20 forest locations
- **Conditions:** Comprehensive environmental coverage
- **Evaluation:** Comprehensive quality and diversity assessment

### Phase 4: Ideal Dataset (6-12 months)
- **Objective:** Achieve ideal dataset (2,000+ recordings)
- **Target:** 2,000+ recordings (500+ per class)
- **Locations:** 30+ forest locations
- **Conditions:** Complete environmental and geographic coverage
- **Evaluation:** Final quality and deployment readiness assessment

---

## Success Criteria

### Technical Success
- **Audio Quality:** 95% of recordings meet quality standards
- **Metadata Completeness:** 100% of recordings have complete metadata
- **File Integrity:** 100% of files pass integrity checks
- **Format Compliance:** 100% of files meet format specifications
- **Backup Success:** 100% of files successfully backed up

### Collection Success
- **Target Achievement:** Meet or exceed recording targets for each phase
- **Class Balance:** Achieve balanced representation across classes
- **Environmental Diversity:** Achieve diverse environmental conditions
- **Geographic Diversity:** Achieve diverse geographic coverage
- **Seasonal Coverage:** Achieve coverage across seasons

### Quality Success
- **SNR Achievement:** 90% of target events achieve 10+ dB SNR
- **Clipping Avoidance:** 95% of recordings have no clipping
- **Background Quality:** 90% of backgrounds are representative
- **Event Clarity:** 90% of target events are clearly audible
- **Metadata Accuracy:** 95% of metadata is accurate

---

**Document Version:** 1.0
**Last Updated:** 2026-09-19
**Status:** Research Phase - Protocol Development
**Next Step:** Begin pilot collection phase after protocol review and approval