#!/usr/bin/env python3
"""
Praat TextGrid parser for Rodopi annotation files.

Parses the ooTextFile format to extract time intervals with labels.
Used to identify chainsaw events ("saw" labeled) vs background
in the Rodopi chainsaw dataset.
"""
import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class TextGridInterval:
    xmin: float
    xmax: float
    label: str


def parse_textgrid(path) -> List[TextGridInterval]:
    """Parse a Praat TextGrid file and return intervals from all tiers."""
    text = open(path, "r").read()
    # Normalize: remove quotes around string values, trim whitespace per line
    intervals = []
    # Match interval blocks: xmin = X, xmax = Y, text = "..."
    pattern = re.compile(
        r'intervals\s*\[?\d+\]?:\s*xmin\s*=\s*([\d.eE+-]+)\s*xmax\s*=\s*([\d.eE+-]+)\s*text\s*=\s*"([^"]*)"',
        re.DOTALL)
    # Also handle the case where text might be on next line with different format
    # Simpler approach: find all xmin/xmax/text triples
    tokens = re.findall(
        r'(?:xmin|xmax|text)\s*=\s*("?)([^"\n]*?)\1', text, re.DOTALL)

    # Fallback: parse line by line
    lines = text.replace('\t', ' ').split('\n')
    current = {}
    tier_intervals = []
    for line in lines:
        line = line.strip()
        if line.startswith('xmin') or line.startswith('xmax'):
            key, _, val = line.partition('=')
            key = key.strip()
            val = val.strip()
            try:
                current[key] = float(val)
            except ValueError:
                pass
        elif line.startswith('text') or line.startswith('"'):
            key, _, val = line.partition('=')
            val = val.strip().strip('"')
            if current.get('xmin') is not None and current.get('xmax') is not None:
                intervals.append(TextGridInterval(
                    current['xmin'], current['xmax'], val))
                current = {}
    return intervals


def get_chainsaw_intervals(intervals: List[TextGridInterval],
                           labels: Tuple[str, ...] = ("saw",)) -> List[TextGridInterval]:
    """Return intervals labeled as chainsaw events."""
    return [iv for iv in intervals if iv.label.strip().lower() in labels]


def get_background_intervals(intervals: List[TextGridInterval],
                             labels: Tuple[str, ...] = ("saw",)) -> List[TextGridInterval]:
    """Return intervals that are NOT chainsaw (background)."""
    return [iv for iv in intervals if iv.label.strip().lower() not in labels]


if __name__ == "__main__":
    import sys
    from pathlib import Path
    if len(sys.argv) < 2:
        print("Usage: python textgrid.py <file.TextGrid>")
        sys.exit(1)
    ivs = parse_textgrid(sys.argv[1])
    print(f"Total intervals: {len(ivs)}")
    chainsaw = get_chainsaw_intervals(ivs)
    bg = get_background_intervals(ivs)
    dur_saw = sum(iv.xmax - iv.xmin for iv in chainsaw)
    dur_bg = sum(iv.xmax - iv.xmin for iv in bg)
    print(f"Chainsaw intervals: {len(chainsaw)} ({dur_saw:.1f}s)")
    print(f"Background intervals: {len(bg)} ({dur_bg:.1f}s)")
    for iv in chainsaw[:10]:
        print(f"  SAW {iv.xmin:.2f}-{iv.xmax:.2f} ({iv.xmax-iv.xmin:.2f}s)")
