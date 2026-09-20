# Failure Analysis

Total test misclassifications (clean condition): 894 / 2119 (42.19%)

## Example misclassified samples

| sample_id | true | predicted | dataset | audio path | likely cause |
|---|---|---|---|---|---|
| c3gd_13-nj_farm_2-savage_magpul_hunter_110-calla_AKG-4fjlchfg107s_3-1_0000 | gunshot | background | c3gd | datasets/processed/c3gd_13-nj_farm_2-savage_magpul_hunter_110-calla_AKG-4fjlchfg107s_3-1_0000.wav | low-energy or short/ambiguous event window misclassified as background |
| fsc22_2_10229_0008 | background | gunshot | fsc22 | datasets/processed/fsc22_2_10229_0008.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10240_0000 | background | gunshot | fsc22 | datasets/processed/fsc22_2_10240_0000.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10240_0001 | background | gunshot | fsc22 | datasets/processed/fsc22_2_10240_0001.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10240_0002 | background | gunshot | fsc22 | datasets/processed/fsc22_2_10240_0002.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10240_0003 | background | gunshot | fsc22 | datasets/processed/fsc22_2_10240_0003.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10240_0004 | background | gunshot | fsc22 | datasets/processed/fsc22_2_10240_0004.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10240_0005 | background | gunshot | fsc22 | datasets/processed/fsc22_2_10240_0005.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10240_0006 | background | gunshot | fsc22 | datasets/processed/fsc22_2_10240_0006.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10240_0007 | background | chainsaw | fsc22 | datasets/processed/fsc22_2_10240_0007.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10240_0008 | background | gunshot | fsc22 | datasets/processed/fsc22_2_10240_0008.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10254_0000 | background | gunshot | fsc22 | datasets/processed/fsc22_2_10254_0000.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10254_0001 | background | gunshot | fsc22 | datasets/processed/fsc22_2_10254_0001.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10272_0002 | background | gunshot | fsc22 | datasets/processed/fsc22_2_10272_0002.wav | background sample with transient/percussive content confused for target event |
| fsc22_2_10272_0005 | background | gunshot | fsc22 | datasets/processed/fsc22_2_10272_0005.wav | background sample with transient/percussive content confused for target event |
