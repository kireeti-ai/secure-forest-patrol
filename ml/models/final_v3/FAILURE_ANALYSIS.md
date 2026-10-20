# Failure Analysis

Total test misclassifications (clean condition): 399 / 2119 (18.83%)

## Example misclassified samples

| sample_id | true | predicted | dataset | audio path | likely cause |
|---|---|---|---|---|---|
| c3gd_13-nj_farm_2-savage_magpul_hunter_110-calla_AKG-4fjlchfg107s_3-1_0000 | gunshot | background | c3gd | datasets/processed/c3gd_13-nj_farm_2-savage_magpul_hunter_110-calla_AKG-4fjlchfg107s_3-1_0000.wav | low-energy or short/ambiguous event window misclassified as background |
| fsc22_3_10310_0007 | background | gunshot | fsc22 | datasets/processed/fsc22_3_10310_0007.wav | background sample with transient/percussive content confused for target event |
| fsc22_3_10310_0008 | background | gunshot | fsc22 | datasets/processed/fsc22_3_10310_0008.wav | background sample with transient/percussive content confused for target event |
| fsc22_3_10333_0000 | background | chainsaw | fsc22 | datasets/processed/fsc22_3_10333_0000.wav | background sample with transient/percussive content confused for target event |
| fsc22_3_10333_0001 | background | chainsaw | fsc22 | datasets/processed/fsc22_3_10333_0001.wav | background sample with transient/percussive content confused for target event |
| fsc22_3_10333_0002 | background | chainsaw | fsc22 | datasets/processed/fsc22_3_10333_0002.wav | background sample with transient/percussive content confused for target event |
| fsc22_3_10333_0003 | background | chainsaw | fsc22 | datasets/processed/fsc22_3_10333_0003.wav | background sample with transient/percussive content confused for target event |
| fsc22_3_10333_0004 | background | chainsaw | fsc22 | datasets/processed/fsc22_3_10333_0004.wav | background sample with transient/percussive content confused for target event |
| fsc22_3_10333_0007 | background | chainsaw | fsc22 | datasets/processed/fsc22_3_10333_0007.wav | background sample with transient/percussive content confused for target event |
| fsc22_3_10333_0008 | background | chainsaw | fsc22 | datasets/processed/fsc22_3_10333_0008.wav | background sample with transient/percussive content confused for target event |
| fsc22_3_10353_0000 | background | gunshot | fsc22 | datasets/processed/fsc22_3_10353_0000.wav | background sample with transient/percussive content confused for target event |
| fsc22_3_10353_0001 | background | gunshot | fsc22 | datasets/processed/fsc22_3_10353_0001.wav | background sample with transient/percussive content confused for target event |
| fsc22_3_10353_0002 | background | gunshot | fsc22 | datasets/processed/fsc22_3_10353_0002.wav | background sample with transient/percussive content confused for target event |
| fsc22_3_10353_0003 | background | gunshot | fsc22 | datasets/processed/fsc22_3_10353_0003.wav | background sample with transient/percussive content confused for target event |
| fsc22_4_10411_0007 | background | gunshot | fsc22 | datasets/processed/fsc22_4_10411_0007.wav | background sample with transient/percussive content confused for target event |
