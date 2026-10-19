# Belize Tropical-Forest Gunshot Dataset — Access Investigation

Investigation date: 2026-10-19  
Official record: https://data.mendeley.com/datasets/x48cwz364j/3

## Findings

The official public landing page confirms the publisher’s description: tropical-forest recordings from Belize, AudioMoth devices, 4.09-second WAV clips at 8 kHz, 749 gunshot files, more than 35,000 background files, controlled firing at 0–1,000 m, and manual listening/spectrogram inspection. The page states CC BY 4.0.

The public HTML response does not expose a file manifest. The page’s file section remains a loading tree and the only visible dataset action is a disabled `Download All` button. No individual WAV URL, archive size, file hash, site/device table, or source-group file listing was available through the public page.

Mendeley’s official developer documentation describes dataset and file APIs, but the dataset API requires an OAuth bearer token. An unauthenticated request to `https://api.mendeley.com/datasets/x48cwz364j/3` returned HTTP 401. No credentials were supplied and no access control was bypassed. The public page and the documented API therefore do not provide an authorized file-level manifest in this environment.

## Consequence

Selective acquisition of 20–30 source-diverse gunshot recordings and background controls could not be performed safely. The publisher describes the first eight filename characters as a Unix hexadecimal recording timestamp, but without actual filenames and metadata it is not possible to map those values to sites, devices, distances, crops, or source sessions. The Vietnam benchmark is not an independent fallback because it explicitly includes Belize-derived material.

No Belize audio was downloaded. The archive size is not available from the public record response, so no full archive was attempted. The appropriate official alternative route is to request a publisher-provided manifest or a small source-grouped subset from the dataset authors, preserving the CC BY attribution and original annotations.

## Required next evidence

Before any Belize audio enters staging, obtain one of:

1. an official file manifest containing filenames, sizes/hashes, labels, and source/site/device/distance fields; or
2. a publisher-curated small subset with those metadata fields.

Then perform exact SHA-256, audio fingerprint, source-group, and frozen-manifest overlap checks. Until that evidence exists, Belize remains `DEFERRED — FILE_LEVEL_ACCESS_UNVERIFIED`.
