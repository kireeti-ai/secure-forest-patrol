# Phase 4.1 Targeted Acquisition Plan

Status: investigated; no external audio was acquired.

## Acquisition decision

The only new source pursued in this phase was Sensing the Forest, because it directly addresses the missing authentic-forest background domain and is published under CC0 1.0 on its official Zenodo record: <https://zenodo.org/records/18911592>. The official record exposes a 24.4 GB archive. Because the mission requires targeted acquisition and the record did not expose a justified small file-level subset, downloading the full archive was not appropriate.

The next acquisition request should be a provider-approved subset of at least 20 distinct forest source recordings, with stable source IDs, original file hashes, recording/device metadata, and permission to create and redistribute derived features for the intended project. Until that is obtained, the gap is documented rather than filled by indiscriminate downloading.

## Existing-source license disposition

- C3GD: CC BY 4.0 according to the official repository; license-eligible for review with attribution, but still label-gated: <https://github.com/Stonewall-Defense/C3GD>
- ESC-50: CC BY-NC 3.0 according to the official repository; research-only for this project unless the intended use is separately cleared: <https://github.com/karolpiczak/ESC-50>
- RFCx FrugalAI: CC BY-NC 4.0 according to the official dataset card; research-only and access/terms must be retained: <https://huggingface.co/datasets/rfcx/frugalai>
- FSC22 and Rodopi: authoritative license terms were not verified in this audit; rows remain quarantined.

No source was promoted to training eligibility solely from a license statement. Label verification and future split isolation are separate mandatory gates.

## Acquisition controls

Any future download must be logged with provider URL, access date, license text, file count, source IDs, SHA-256 hashes, parent recording IDs, and attribution. Only a source-disjoint subset may be added to a future candidate manifest. Do not add Phase 1 frozen-test failures as training data.
