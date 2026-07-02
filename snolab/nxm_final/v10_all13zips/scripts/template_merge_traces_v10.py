#!/usr/bin/env python3
# coding: utf-8
# Merge per-series partial pkl files into traces_cache_zip{det}.pkl
# which template_single_zip_v10.py loads (CACHE_VERSION=10).
#
# Merges in ALL_SERIES order (identical to the original sequential loop).
#
# Usage: python template_merge_traces_v10.py --det N

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--det', type=int, required=True)
args = parser.parse_args()

import os, pickle

RUN_DIR = os.environ.get("R4_RUN_DIR", "").strip()
if not RUN_DIR:
    raise RuntimeError("R4_RUN_DIR not set")
RUN_DIR   = os.path.abspath(RUN_DIR)
CACHE_DIR = os.path.join(RUN_DIR, "cache")

det = args.det

ALL_SERIES = [
    "24260617_063934", "24260617_175849", "24260617_190838", "24260617_234805",
    "24260618_013000", "24260618_062713", "24260618_073543", "24260618_202553",
    "24260619_023225", "24260619_061249", "24260619_075448", "24260619_093653",
    "24260619_144815", "24260619_174938", "24260619_210312", "24260619_230219",
    "24260620_032928", "24260621_021444", "24260621_041432", "24260621_075659",
    "24260621_111527", "24260621_145024", "24260622_022708", "24260622_042718",
    "24260622_073439", "24260622_210215", "24260622_232541", "24260623_012553",
    "24260623_035656", "24260623_064608",
]

ALL_CHANS     = ['PAS1','PBS1','PCS1','PDS1','PES1','PFS1',
                 'PAS2','PBS2','PCS2','PDS2','PES2','PFS2']
RAW_SAMPLE_N  = 5
CACHE_VERSION = 10

channel_traces    = {c: [] for c in ALL_CHANS}
pf_traces         = []
raw_sample        = {c: [] for c in ALL_CHANS}
negative_rejected = {c: 0 for c in ALL_CHANS}

n_missing = 0
# Iterate in ALL_SERIES order — identical to the original sequential loop
for series in ALL_SERIES:
    path = os.path.join(CACHE_DIR, f"traces_partial_zip{det}_{series}.pkl")
    if not os.path.exists(path):
        print(f"WARNING: partial file missing for series {series} — skipping")
        n_missing += 1
        continue
    with open(path, 'rb') as f:
        part = pickle.load(f)
    if part.get('excluded'):
        print(f"  {series}: excluded")
        continue
    n = sum(len(v) for v in part['channel_traces'].values())
    print(f"  {series}: {n} traces, {len(part['pf_traces'])} pf_traces")
    for c in ALL_CHANS:
        channel_traces[c].extend(part['channel_traces'].get(c, []))
        negative_rejected[c] += part['negative_rejected'].get(c, 0)
        needed = RAW_SAMPLE_N - len(raw_sample[c])
        if needed > 0:
            raw_sample[c].extend(part['raw_sample'].get(c, [])[:needed])
    pf_traces.extend(part['pf_traces'])

if n_missing > 0:
    print(f"\nWARNING: {n_missing} series partial files were missing.")

print(f"\nMerge summary for Zip{det}:")
for c in ALL_CHANS:
    print(f"  {c}: {len(channel_traces[c])} traces, {negative_rejected[c]} rejected")
print(f"  pf_traces: {len(pf_traces)}")

cache_path = os.path.join(CACHE_DIR, f"traces_cache_zip{det}.pkl")
with open(cache_path, 'wb') as f:
    pickle.dump({'cache_version': CACHE_VERSION,
                 'channel_traces': channel_traces,
                 'pf_traces': pf_traces,
                 'raw_sample': raw_sample,
                 'negative_rejected': negative_rejected,
                 'alignment': 'PTOFdelay'}, f)
print(f"\nSaved: {cache_path}")
print(f"Done. Zip{det} merge complete.")
