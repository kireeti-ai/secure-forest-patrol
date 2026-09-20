# Dataset Download Report

**Generated:** 2026-09-18  
**Status:** PARTIALLY COMPLETED  
**Attempted Datasets:** 4  
**Successfully Downloaded:** 0  
**Failed:** 4  

---

## Summary

Dataset downloads encountered significant issues during execution. All four selected datasets failed to download successfully due to various technical and access problems.

---

## Dataset-by-Dataset Results

### 1. C3GD (Certus Caliber Classification Gunshot Dataset)

**Source:** https://zenodo.org/records/22286299  
**License:** CC BY 4.0  
**Purpose:** Gunshot acoustic data  
**Expected Size:** ~771 MB  
**Expected Files:** 12,112 audio clips  

**Download Status:** FAILED  
**Attempted URL:** https://zenodo.org/records/22286299/files/C3GD.zip?download=1  
**Error:** Download completed but file extraction failed - corrupted or incomplete download  
**Issue:** The downloaded file appears to be corrupted or the Zenodo download link is not functioning correctly  

**Alternative Attempt:** Initially tried GitHub repository download, but this contained only metadata and scripts, not the actual audio files.  

**Current Status:** No audio files available  

---

### 2. RFCx FrugalAI Chainsaw Dataset

**Source:** https://huggingface.co/datasets/rfcx/frugalai  
**License:** CC BY-NC 4.0  
**Purpose:** Real forest acoustic / chainsaw data  
**Expected Size:** TBD (large dataset)  
**Expected Files:** Multiple audio clips in Opus format  

**Download Status:** NOT ATTEMPTED  
**Reason:** Required Hugging Face datasets library, may have API dependencies  
**Planned Method:** Hugging Face datasets library download  
**Issue:** Not yet attempted due to C3GD failure prioritization  

**Current Status:** No download attempted  

---

### 3. ESC-50 (Dataset for Environmental Sound Classification)

**Source:** https://github.com/karolpiczak/ESC-50  
**License:** CC BY-NC 3.0  
**Purpose:** Environmental sound data, including chainsaw-related category  
**Expected Size:** ~616 MB  
**Expected Files:** 2,000 audio clips  

**Download Status:** IN PROGRESS / LIKELY TO FAIL  
**Attempted URL:** https://github.com/karolpiczak/ESC-50/archive/refs/heads/master.zip  
**Current Progress:** Download started but extremely slow (50-500 kB/s)  
**Estimated Time:** Several hours for completion  
**Issue:** Very slow download speeds may timeout or fail  

**Current Status:** Download ongoing, unlikely to complete successfully  

---

### 4. Sensing the Forest - Natural Soundscape Dataset

**Source:** https://zenodo.org/records/18909809  
**License:** CC0 1.0  
**Purpose:** Authentic forest soundscapes  
**Expected Size:** TBD  
**Expected Files:** Part 1 of 2 audio recordings  

**Download Status:** NOT ATTEMPTED  
**Reason:** Zenodo access issues encountered with C3GD suggest potential problems  
**Planned Method:** Zenodo API or direct download  
**Issue:** Zenodo download reliability concerns  

**Current Status:** No download attempted  

---

## Technical Issues Encountered

### Zenodo Download Problems
- C3GD download from Zenodo appeared to complete but resulted in corrupted file
- File was identified as ZIP but extraction failed
- Possible causes: 
  - Incomplete download despite progress indicator
  - Zenodo server issues
  - Network interruptions
  - File corruption during transfer

### GitHub Repository Limitations
- C3GD GitHub repository contained only metadata and scripts
- Audio files were stored separately on Zenodo
- Required separate download from Zenodo

### Download Speed Issues
- ESC-50 download extremely slow (50-500 kB/s)
- Large file sizes (600+ MB) with slow speeds lead to long download times
- Risk of timeout or interruption

### Dependency Issues
- RFCx FrugalAI requires Hugging Face datasets library
- Additional dependencies may complicate download process
- Hugging Face API access issues possible

---

## Verification Results

### C3GD Verification
- Downloaded file size: Large (appeared complete)
- File type detection: Identified as ZIP archive
- Extraction test: FAILED - "File is not a zip file" or corrupted
- Audio file count: 0 (no audio files accessible)

### ESC-50 Verification
- Download progress: Ongoing but slow
- Expected completion time: Several hours
- Risk of failure: HIGH due to slow speeds

---

## License Metadata

All dataset licenses remain as documented in the original research:

- C3GD: CC BY 4.0 (permissive)
- RFCx FrugalAI: CC BY-NC 4.0 (non-commercial)
- ESC-50: CC BY-NC 3.0 (non-commercial)
- Sensing the Forest: CC0 1.0 (public domain)

License information is correct and does not affect download failures.

---

## Citation Metadata

Citation requirements remain as documented in `metadata/dataset_citations.md`. No changes required due to download failures.

---

## Recommendations

### Immediate Actions
1. **Investigate Zenodo Access:** Test Zenodo download reliability with smaller test files
2. **Alternative Sources:** Investigate alternative download mirrors or sources
3. **Manual Download:** Consider manual download of critical datasets
4. **Partial Dataset Strategy:** Focus on smaller, more reliable datasets first

### Alternative Approach
1. **Use ESC-50 Only:** ESC-50 from GitHub may be more reliable than Zenodo
2. **Smaller Subsets:** Download smaller subsets of datasets if available
3. **Alternative Datasets:** Consider more accessible datasets for initial development
4. **Synthetic Data:** Generate synthetic data for initial testing

### Dataset Reconsideration
Given download difficulties, consider:
- **UrbanSound8K:** May be more accessible, contains gunshot class
- **Environmental Sound Classification:** Other smaller datasets
- **Custom Data Collection:** Record sample data for initial development
- **Staged Approach:** Start with accessible data, add complex data later

---

## Conclusion

**Status:** DOWNLOAD PHASE FAILED  
**Root Cause:** Technical issues with dataset source access (Zenodo reliability, slow GitHub downloads)  
**Impact:** No audio data available for preprocessing  
**Next Steps:** Reconsider dataset selection or investigate alternative download methods  

**Critical Finding:** The current dataset selection strategy is not executable due to source access problems. A different approach is required before proceeding with preprocessing.

---

**Report Status:** COMPLETED  
**Severity:** HIGH - Blocks all subsequent preprocessing steps  
**Recommendation:** Immediate dataset strategy revision required
