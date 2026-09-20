# Failure Analysis

Total test misclassifications (clean condition): 1184 / 2119 (55.88%)

## Example misclassified samples

| sample_id | true | predicted | dataset | audio path | likely cause |
|---|---|---|---|---|---|
| c3gd_1-nj_farm_2-radical_ar15_upper-lilypad_SAMSON-3qq3r3ac4nkr_11-4_0000 | gunshot | chainsaw | c3gd | datasets/processed/c3gd_1-nj_farm_2-radical_ar15_upper-lilypad_SAMSON-3qq3r3ac4nkr_11-4_0000.wav | acoustic similarity between chainsaw/gunshot spectral envelope |
| c3gd_13-nj_farm_2-savage_magpul_hunter_110-calla_AKG-4fjlchfg107s_3-1_0000 | gunshot | chainsaw | c3gd | datasets/processed/c3gd_13-nj_farm_2-savage_magpul_hunter_110-calla_AKG-4fjlchfg107s_3-1_0000.wav | acoustic similarity between chainsaw/gunshot spectral envelope |
| fsc22_2_10206_0000 | background | chainsaw | fsc22 | datasets/processed/fsc22_2_10206_0000.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10206_0001 | background | chainsaw | fsc22 | datasets/processed/fsc22_2_10206_0001.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10206_0002 | background | chainsaw | fsc22 | datasets/processed/fsc22_2_10206_0002.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10206_0003 | background | chainsaw | fsc22 | datasets/processed/fsc22_2_10206_0003.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10206_0004 | background | chainsaw | fsc22 | datasets/processed/fsc22_2_10206_0004.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10206_0005 | background | chainsaw | fsc22 | datasets/processed/fsc22_2_10206_0005.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10206_0006 | background | chainsaw | fsc22 | datasets/processed/fsc22_2_10206_0006.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10206_0007 | background | chainsaw | fsc22 | datasets/processed/fsc22_2_10206_0007.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10206_0008 | background | chainsaw | fsc22 | datasets/processed/fsc22_2_10206_0008.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10229_0000 | background | chainsaw | fsc22 | datasets/processed/fsc22_2_10229_0000.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10229_0001 | background | chainsaw | fsc22 | datasets/processed/fsc22_2_10229_0001.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10229_0002 | background | chainsaw | fsc22 | datasets/processed/fsc22_2_10229_0002.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10229_0003 | background | chainsaw | fsc22 | datasets/processed/fsc22_2_10229_0003.wav | background sample with transient/percussive content confused for target event |
