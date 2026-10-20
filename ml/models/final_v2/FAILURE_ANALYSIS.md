# Failure Analysis

Total test misclassifications (clean condition): 269 / 2119 (12.69%)

## Example misclassified samples

| sample_id | true | predicted | dataset | audio path | likely cause |
|---|---|---|---|---|---|
| fsc22_3_10313_0002 | background | gunshot | fsc22 | datasets/processed/fsc22_3_10313_0002.wav | background sample with transient/percussive content confused for target event |
| fsc22_3_10313_0003 | background | gunshot | fsc22 | datasets/processed/fsc22_3_10313_0003.wav | background sample with transient/percussive content confused for target event |
| fsc22_3_10313_0004 | background | gunshot | fsc22 | datasets/processed/fsc22_3_10313_0004.wav | background sample with transient/percussive content confused for target event |
| fsc22_3_10313_0007 | background | gunshot | fsc22 | datasets/processed/fsc22_3_10313_0007.wav | background sample with transient/percussive content confused for target event |
| fsc22_4_10414_0006 | background | gunshot | fsc22 | datasets/processed/fsc22_4_10414_0006.wav | background sample with transient/percussive content confused for target event |
| fsc22_11_11101_0000 | chainsaw | background | fsc22 | datasets/processed/fsc22_11_11101_0000.wav | low-energy or short/ambiguous event window misclassified as background |
| fsc22_11_11101_0001 | chainsaw | background | fsc22 | datasets/processed/fsc22_11_11101_0001.wav | low-energy or short/ambiguous event window misclassified as background |
| fsc22_11_11101_0003 | chainsaw | background | fsc22 | datasets/processed/fsc22_11_11101_0003.wav | low-energy or short/ambiguous event window misclassified as background |
| fsc22_11_11101_0004 | chainsaw | gunshot | fsc22 | datasets/processed/fsc22_11_11101_0004.wav | acoustic similarity between chainsaw/gunshot spectral envelope |
| fsc22_11_11101_0006 | chainsaw | background | fsc22 | datasets/processed/fsc22_11_11101_0006.wav | low-energy or short/ambiguous event window misclassified as background |
| fsc22_11_11101_0007 | chainsaw | background | fsc22 | datasets/processed/fsc22_11_11101_0007.wav | low-energy or short/ambiguous event window misclassified as background |
| fsc22_11_11107_0000 | chainsaw | background | fsc22 | datasets/processed/fsc22_11_11107_0000.wav | low-energy or short/ambiguous event window misclassified as background |
| fsc22_11_11107_0001 | chainsaw | background | fsc22 | datasets/processed/fsc22_11_11107_0001.wav | low-energy or short/ambiguous event window misclassified as background |
| fsc22_11_11107_0002 | chainsaw | background | fsc22 | datasets/processed/fsc22_11_11107_0002.wav | low-energy or short/ambiguous event window misclassified as background |
| fsc22_11_11142_0001 | chainsaw | background | fsc22 | datasets/processed/fsc22_11_11142_0001.wav | low-energy or short/ambiguous event window misclassified as background |
