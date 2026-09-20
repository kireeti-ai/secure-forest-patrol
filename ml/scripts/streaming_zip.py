#!/usr/bin/env python3
"""
Streaming ZIP reader over HTTP range requests.

Allows listing and selectively extracting members from a ZIP (incl. ZIP64)
file that is hosted on a server supporting Range requests, WITHOUT
downloading the whole archive.  Only the central directory and the
requested members are fetched.
"""
import os, sys, json, struct, argparse, zlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests


class RangeHTTPFile:
    """A seekable, read-only file-like object backed by HTTP Range requests."""

    def __init__(self, url, chunk_size=1024 * 1024, timeout=300):
        self.url = url
        self.chunk_size = chunk_size
        self.timeout = timeout
        r = requests.head(url, allow_redirects=True, timeout=60)
        r.raise_for_status()
        self.size = int(r.headers.get("content-length", 0))
        if "accept-ranges" in r.headers:
            self.ranges_ok = r.headers["accept-ranges"].lower() != "none"
        else:
            self.ranges_ok = True  # assume; will fall back to full
        self.pos = 0

    def seek(self, offset, whence=0):
        if whence == 0:
            self.pos = offset
        elif whence == 1:
            self.pos += offset
        elif whence == 2:
            self.pos = self.size + offset
        return self.pos

    def tell(self):
        return self.pos

    def seekable(self):
        return True

    def readable(self):
        return True

    def writable(self):
        return False

    def read(self, size=-1):
        if size < 0:
            size = self.size - self.pos
        if size <= 0:
            return b""
        end = self.pos + size - 1
        headers = {"Range": f"bytes={self.pos}-{end}"}
        if not self.ranges_ok:
            headers = {}
        r = requests.get(self.url, headers=headers, stream=True,
                         timeout=self.timeout, allow_redirects=True)
        r.raise_for_status()
        data = r.content
        self.pos += len(data)
        return data

    def getvalue(self):
        return self.read()

    def close(self):
        pass


def main():
    import sys, json, argparse, os
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract-names", type=Path, default=None,
                        help="JSON list of member names to extract selectively")
    parser.add_argument("--parallel", type=int, default=1,
                        help="Number of parallel download workers")
    parser.add_argument("--url", type=str, default=None,
                        help="ZIP file URL (overrides default Sensing the Forest)")
    parser.add_argument("--list", action="store_true",
                        help="List all members of the zip")
    parser.add_argument("--extract", nargs="+", default=None,
                        help="Extract specific member names")
    parser.add_argument("--extract-dir", type=Path, default=None,
                        help="Directory to extract into")
    parser.add_argument("--max-wav", type=int, default=None,
                        help="Extract up to N wav files (for selective bg download)")
    parser.add_argument("--out-meta", type=Path, default=None,
                        help="Write a JSON manifest of the zip listing")
    args = parser.parse_args()

    import zipfile
    url = args.url or "https://zenodo.org/api/records/18909809/files/42937__sensingtheforest__natural-soundscape-dataset-part-1.zip/content"
    rf = RangeHTTPFile(url)
    print(f"ZIP total size: {rf.size/1048576:.1f} MB, ranges_ok={rf.ranges_ok}")
    zf = zipfile.ZipFile(rf, "r")

    infos = zf.infolist()
    wavs = [i for i in infos if i.filename.lower().endswith(".wav")]
    others = [i for i in infos if not i.filename.lower().endswith(".wav")]
    total_uncomp = sum(i.file_size for i in infos)
    total_wav = sum(i.file_size for i in wavs)
    print(f"Total members: {len(infos)}")
    print(f"  WAV members: {len(wavs)} ({total_wav/1048576:.1f} MB uncompressed)")
    print(f"  Other members: {len(others)} ({sum(i.file_size for i in others)/1048576:.1f} MB)")
    print(f"  Total uncompressed: {total_uncomp/1048576:.1f} MB")
    print(f"  Compressed: {sum(i.compress_size for i in infos)/1048576:.1f} MB")

    if args.list or args.out_meta:
        listing = []
        for i in infos:
            listing.append({"name": i.filename, "size": i.file_size,
                            "compress_size": i.compress_size,
                            "date_time": list(i.date_time), "method": i.compress_type})
        if args.out_meta:
            args.out_meta.parent.mkdir(parents=True, exist_ok=True)
            json.dump(listing, open(args.out_meta, "w"), indent=2)
            print(f"Listing written to {args.out_meta}")
        for i in wavs[:30]:
            print(f"  WAV: {i.filename}  {i.file_size/1048576:.1f}MB")

    out_dir = args.extract_dir or Path("extracted")
    out_dir.mkdir(parents=True, exist_ok=True)
    to_extract = []
    if args.max_wav:
        to_extract = wavs[:args.max_wav]
    elif args.extract:
        wanted = set(args.extract)
        to_extract = [i for i in infos if i.filename in wanted]
    elif args.extract_names:
        names = set(json.load(open(args.extract_names)))
        to_extract = [i for i in infos if i.filename in names]

    if to_extract:
        print(f"Extracting {len(to_extract)} files -> {out_dir}")
        # Build (filename, local_off, compress_size, file_size, method) tuples
        jobs = [(i.filename, i.header_offset, i.compress_size,
                 i.file_size, i.compress_type) for i in to_extract]

        def fetch_local_header(local_off):
            """Read the local file header to get filename/extra lengths."""
            r = requests.get(url, headers={"Range": f"bytes={local_off}-{local_off+60}"},
                             timeout=120, allow_redirects=True)
            r.raise_for_status()
            hdr = r.content
            if hdr[:4] != b'PK\x03\x04':
                return None
            fname_len = struct.unpack('<H', hdr[26:28])[0]
            extra_len = struct.unpack('<H', hdr[28:30])[0]
            return fname_len, extra_len

        def extract_one(job):
            name, local_off, comp_size, file_size, method = job
            outpath = out_dir / name
            if outpath.exists() and outpath.stat().st_size == file_size:
                return (name, True, "skip")
            try:
                lh = fetch_local_header(local_off)
                if lh is None:
                    return (name, False, "bad local header")
                fname_len, extra_len = lh
                data_off = local_off + 30 + fname_len + extra_len
                # Download compressed data
                r = requests.get(url,
                                 headers={"Range": f"bytes={data_off}-{data_off+comp_size-1}"},
                                 timeout=600, allow_redirects=True)
                r.raise_for_status()
                raw = r.content
                if len(raw) != comp_size:
                    return (name, False, f"size mismatch {len(raw)}!={comp_size}")
                if method == 0:  # stored
                    data = raw
                elif method == 8:  # deflate
                    data = zlib.decompress(raw, -15)
                else:
                    return (name, False, f"unknown method {method}")
                outpath.parent.mkdir(parents=True, exist_ok=True)
                with open(outpath, "wb") as f:
                    f.write(data)
                return (name, True, f"{file_size/1048576:.1f}MB")
            except Exception as e:
                return (name, False, str(e)[:120])

        workers = min(args.parallel, len(to_extract)) if args.parallel else 1
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(extract_one, j): j[0] for j in jobs}
            for fut in as_completed(futures):
                name, ok, msg = fut.result()
                done += 1
                status = "OK" if ok else "FAIL"
                print(f"  [{done}/{len(to_extract)}] {status} {name} {msg}")
    zf.close()


if __name__ == "__main__":
    main()
