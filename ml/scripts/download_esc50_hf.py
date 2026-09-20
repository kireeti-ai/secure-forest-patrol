#!/usr/bin/env python3
"""
Selective ESC-50 downloader for SECURE FOREST PATROL.

Downloads ONLY the chainsaw class and forest-relevant background classes
from the ESC-50 dataset zip on HuggingFace, avoiding the full 616 MB.

Classes selected (supplementary, per task spec):
  chainsaw              -> CHAINSAW
  chirping_birds        -> background
  rain                  -> background
  wind                  -> background
  crickets              -> background (insects)
  insects               -> background
  footsteps             -> background (human movement)
  thunderstorm          -> background
  water_drops           -> background
  frog                  -> background (forest animal)
  crow                  -> background (forest animal)
  crackling_fire        -> background (forest-related)
  engine                -> background (distant machinery)
"""
import io, csv, json, time, struct
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from tqdm import tqdm

RAW = Path(__file__).resolve().parent.parent / "datasets" / "raw" / "esc50_hf"
RAW.mkdir(parents=True, exist_ok=True)

ZIP_URL = ("https://huggingface.co/datasets/yangwang825/esc50/resolve/"
           "main/ESC-50-master.zip?download=true")

# Classes to download
TARGET_CATEGORIES = {
    "chainsaw", "chirping_birds", "rain", "wind", "crickets", "insects",
    "footsteps", "thunderstorm", "water_drops", "frog", "crow",
    "crackling_fire", "engine",
}

TIMEOUT = 60


def get_zip_info(url):
    """Fetch the End of Central Directory to determine zip layout."""
    # HEAD request for total size
    r = requests.head(url, allow_redirects=True, timeout=60)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))
    # Fetch last 1MB for central directory (and ZIP64 structures if needed)
    tail_size = min(1024 * 1024, total)
    r2 = requests.get(url, headers={"Range": f"bytes={total - tail_size}-"},
                      timeout=120, allow_redirects=True)
    data = r2.content
    return total, data


def parse_central_directory(url, total, tail_data):
    """Parse ZIP central directory from tail bytes. Returns list of entries."""
    eocd_off = tail_data.rfind(b"PK\x05\x06")
    if eocd_off < 0:
        raise RuntimeError("EOCD not found")
    eocd = tail_data[eocd_off:]
    (sig, disk, cd_disk, n_disk, n_rec, cd_size, cd_off,
     comm_len) = struct.unpack("<IHHHHIIH", eocd[:22])
    # ESC-50 zip is < 4GB so not ZIP64; cd_off is absolute
    # Fetch central directory via range request
    headers = {"Range": f"bytes={cd_off}-{cd_off + cd_size - 1}"}
    r = requests.get(url, headers=headers, timeout=300, allow_redirects=True)
    cd_data = r.content

    entries = []
    off = 0
    while off < len(cd_data):
        if cd_data[off:off + 4] != b"PK\x01\x02":
            break
        (sig, ver_made, ver_need, flags, method, mtime, mdate,
         crc, comp_size, uncomp_size, fname_len, extra_len, comm_len,
         disk_start, int_attr, ext_attr, local_off) = struct.unpack(
            "<IHHHHHHIIIHHHHHII", cd_data[off:off + 46])
        fname = cd_data[off + 46:off + 46 + fname_len].decode("utf-8", "replace")
        entries.append({"name": fname, "method": method, "comp_size": comp_size,
                        "uncomp_size": uncomp_size, "local_off": local_off,
                        "crc": crc, "fname_len": fname_len, "extra_len": extra_len})
        off += 46 + fname_len + extra_len + comm_len
    return entries


def read_zip_member(url, entry, dest):
    """Download and extract a single zip member by offset."""
    local_off = entry["local_off"]
    # Fetch local header to get fname_len/extra_len of local header
    r = requests.get(url, headers={"Range": f"bytes={local_off}-{local_off + 60}"},
                     timeout=60, allow_redirects=True)
    hdr = r.content
    if hdr[:4] != b"PK\x03\x04":
        return False, "bad local header"
    (sig, ver, flags, method, mtime, mdate, crc,
     comp_size, uncomp_size, fname_len, extra_len) = struct.unpack(
        "<IHHHHHIIIHH", hdr[:30])
    data_off = local_off + 30 + fname_len + extra_len
    comp_size = entry["comp_size"] or comp_size
    # Download compressed data
    r2 = requests.get(url,
                      headers={"Range": f"bytes={data_off}-{data_off + comp_size - 1}"},
                      timeout=300, allow_redirects=True)
    raw = r2.content
    if len(raw) != comp_size:
        return False, f"size mismatch {len(raw)}!={comp_size}"
    if method == 0:
        data = raw
    elif method == 8:
        import zlib
        data = zlib.decompress(raw, -15)
    else:
        return False, f"method {method}"
    dest_path = Path(dest) / entry["name"]
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(data)
    return True, entry["uncomp_size"]


def main():
    print("=== ESC-50 Selective Download ===")
    print(f"ZIP URL: {ZIP_URL}")
    print(f"Target categories: {TARGET_CATEGORIES}")

    # 1. Get zip info
    total, tail = get_zip_info(ZIP_URL)
    print(f"ZIP size: {total/1048576:.1f} MB")

    # 2. Parse central directory
    entries = parse_central_directory(ZIP_URL, total, tail)
    print(f"Central directory: {len(entries)} entries")

    # 3. Read metadata CSV from zip
    meta_entry = None
    for e in entries:
        if e["name"].endswith("esc50.csv"):
            meta_entry = e
            break
    if not meta_entry:
        print("ERROR: metadata CSV not found")
        return

    ok, msg = read_zip_member(ZIP_URL, meta_entry, RAW)
    if not ok:
        print(f"ERROR reading metadata: {msg}")
        return
    meta_path = RAW / meta_entry["name"]
    reader = csv.DictReader(io.StringIO(meta_path.read_text()))
    rows = list(reader)
    print(f"Metadata: {len(rows)} entries")

    # 4. Map filenames to categories
    file_to_cat = {}
    for r in rows:
        file_to_cat[r["filename"]] = r["category"]

    # 5. Find audio files matching target categories
    want = []
    for e in entries:
        if e["name"].endswith(".wav"):
            basename = Path(e["name"]).name
            cat = file_to_cat.get(basename)
            if cat in TARGET_CATEGORIES:
                want.append((e, cat, basename))
    print(f"Files to download: {len(want)}")
    by_cat = defaultdict(int)
    for _, cat, _ in want:
        by_cat[cat] += 1
    for cat, cnt in sorted(by_cat.items()):
        print(f"  {cat}: {cnt}")

    # 6. Download in parallel
    out_dir = RAW / "ESC-50-master" / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    ok_count = 0
    errors = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {}
        for entry, cat, basename in want:
            # Save to class-specific subfolder
            class_dir = out_dir.parent / cat
            dest = class_dir / basename
            if dest.exists():
                ok_count += 1
                continue
            futures[ex.submit(read_zip_member, ZIP_URL, entry, class_dir)] = (cat, basename)
        for fut in tqdm(as_completed(futures), total=len(futures), desc="ESC-50"):
            cat, basename = futures[fut]
            ok, msg = fut.result()
            if ok:
                ok_count += 1
            else:
                errors.append(f"{basename}: {msg}")
    print(f"\nDone: {ok_count}/{len(want)} files downloaded")
    if errors:
        print(f"Errors ({len(errors)}): {errors[:5]}")
    # Save metadata
    meta = {"dataset_id": "esc50", "url": ZIP_URL, "license": "CC BY-NC 3.0",
            "status": "downloaded", "categories": sorted(by_cat.keys()),
            "file_count": ok_count}
    (RAW / "download_metadata.json").write_text(json.dumps(meta, indent=2))
    print("DONE")


if __name__ == "__main__":
    main()
