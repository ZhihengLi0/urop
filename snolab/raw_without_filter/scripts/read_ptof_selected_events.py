x#!/usr/bin/env python3
"""Save raw MIDAS traces for events selected only by the configured PTOFamps range.

This intentionally does not low-pass filter, normalize, fit, align, apply
fit_ok/nrmse cuts, or require all channels to be present. If a selected event
has only some channels in raw MIDAS, the available channels are saved and the
missing ones are recorded in event_stats.
"""

import argparse
import datetime
import os
import pickle

import numpy as np
import uproot

try:
    import rawio
except ImportError:
    rawio = None


PROCESSED_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Processed/Prompt/Prompt_V07-02_C0.4.5/Submerged"
RAW_DIR = "/projects/standard/yanliusp/shared/data/CDMS/SNOLAB/R4/Raw"
PROD_TAG = "Prompt_V07-02_C0.4.5"
CACHE_DIR_DEFAULT = "/projects/standard/yanliusp/shared/zhiheng/snolab/raw_without_filter/run/cache"

PAYLOAD_SCHEMA_VERSION = "raw_ptof_selected_event_v1"

ALL_CHANS = [
    "PAS1", "PBS1", "PCS1", "PDS1", "PES1", "PFS1",
    "PAS2", "PBS2", "PCS2", "PDS2", "PES2", "PFS2",
]

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

SERIES_EXCLUSIONS = {
     1: ["24260621_075659"],
    13: ["24260617_063934"],
    15: ["24260619_093653", "24260619_144815", "24260619_230219"],
    18: ["24260617_063934", "24260617_175849", "24260617_190838",
         "24260617_234805", "24260618_013000", "24260618_062713",
         "24260618_073543"],
    22: ["24260620_032928", "24260621_021444", "24260621_041432",
         "24260621_075659", "24260621_111527", "24260621_145024"],
}

PTOF_RANGES = {
     1: (2.96e-7, 5.40e-7),
     4: (4.44e-7, 8.10e-7),
     6: (3.33e-7, 6.08e-7),
     7: (1.48e-6, 2.70e-6),
     9: (5.93e-7, 1.08e-6),
    10: (5.93e-7, 1.08e-6),
    13: (1.19e-6, 2.16e-6),
    15: (7.41e-6, 1.35e-5),
    16: (1.33e-6, 2.43e-6),
    18: (1.04e-6, 1.89e-6),
    19: (4.44e-7, 8.10e-7),
    22: (3.70e-7, 6.75e-7),
    24: (4.44e-7, 8.10e-7),
}


def ordered_unique(values):
    return list(dict.fromkeys(int(v) for v in values))


def select_events_for_series(det, series, ptof_lo, ptof_hi):
    root_path = os.path.join(PROCESSED_DIR, f"{PROD_TAG}_{series}.root")
    if not os.path.exists(root_path):
        print(f"  {series}: processed ROOT missing, skip")
        return None

    with uproot.open(root_path) as handle:
        event_numbers = handle["rqDir/eventTree/EventNumber"].array(library="np").astype(int)
        trigger_types = handle["rqDir/eventTree/TriggerType"].array(library="np").astype(int)
        ptofamps = handle[f"rqDir/zip{det}/PTOFamps"].array(library="np")
        mask = (ptofamps != -999999) & (ptofamps > ptof_lo) & (ptofamps < ptof_hi)

        selected_events = ordered_unique(event_numbers[mask])
        selected_set = set(selected_events)
        ptof_by_event = {}
        trigger_by_event = {}
        for event_number, trigger_type, ptofamp in zip(event_numbers[mask], trigger_types[mask], ptofamps[mask]):
            event = int(event_number)
            if event not in ptof_by_event:
                ptof_by_event[event] = float(ptofamp)
                trigger_by_event[event] = int(trigger_type)

        baselines = {}
        for channel in ALL_CHANS:
            try:
                baseline_array = handle[f"rqDir/zip{det}/{channel}bs"].array(library="np")
                baselines[channel] = {
                    int(event_number): float(baseline)
                    for event_number, baseline in zip(event_numbers[mask], baseline_array[mask])
                    if int(event_number) in selected_set
                }
            except Exception:
                baselines[channel] = {}

    print(f"  {series}: selected {len(selected_events)} unique events in PTOFamps range")
    return {
        "event_numbers": selected_events,
        "event_set": selected_set,
        "ptofamps": ptof_by_event,
        "trigger_types": trigger_by_event,
        "baselines": baselines,
        "n_selected_rows": int(np.sum(mask)),
        "n_selected_unique": len(selected_events),
    }


def build_payload_from_raw(det, series, selection):
    if rawio is None:
        raise RuntimeError("rawio is required to read raw MIDAS data")

    raw_dir = os.path.join(RAW_DIR, series)
    if not os.path.isdir(raw_dir):
        print(f"  {series}: raw directory missing, skip")
        return None

    reader = rawio.RawDataReader(raw_dir)
    nb_events = reader.get_nb_events()
    total_events = nb_events.get("NbEventsNotEmpty", nb_events.get("NbEvents", 50000))
    events = reader.read_events(
        output_format=2,
        skip_empty=True,
        nb_events=total_events,
        detector_nums=[det],
        channel_names=ALL_CHANS,
    )

    raw_traces = {channel: [] for channel in ALL_CHANS}
    event_numbers_ch = {channel: [] for channel in ALL_CHANS}
    ptofamps_ch = {channel: [] for channel in ALL_CHANS}
    baselines_ch = {channel: [] for channel in ALL_CHANS}
    event_stats = []
    seen_events = set()
    z_key = f"Z{det}"

    for event in events:
        event_number = int(event["event"]["EventNumber"])
        if event_number not in selection["event_set"] or event_number in seen_events:
            continue
        seen_events.add(event_number)

        event_record = {
            "event_number": event_number,
            "trigger_type": selection["trigger_types"].get(event_number),
            "ptofamp": selection["ptofamps"].get(event_number),
            "channels": {},
        }

        for channel in ALL_CHANS:
            channel_record = {
                "raw_present": False,
                "trace_saved": False,
                "baseline_rq": selection["baselines"].get(channel, {}).get(event_number, np.nan),
                "reason": None,
            }
            try:
                trace = np.asarray(event[z_key][channel])
            except KeyError:
                channel_record["reason"] = "missing_channel"
                event_record["channels"][channel] = channel_record
                continue

            raw_traces[channel].append(trace)
            event_numbers_ch[channel].append(event_number)
            ptofamps_ch[channel].append(selection["ptofamps"].get(event_number))
            baseline = channel_record["baseline_rq"]
            baselines_ch[channel].append(float(baseline) if np.isfinite(baseline) else np.nan)
            channel_record["raw_present"] = True
            channel_record["trace_saved"] = True
            channel_record["trace_length"] = int(len(trace))
            channel_record["dtype"] = str(trace.dtype)
            event_record["channels"][channel] = channel_record

        event_stats.append(event_record)

    print(f"  {series}: found {len(seen_events)}/{len(selection['event_set'])} selected events in raw MIDAS")
    return {
        "payload_schema_version": PAYLOAD_SCHEMA_VERSION,
        "det": det,
        "series": series,
        "ptof_range": tuple(PTOF_RANGES[det]),
        "channels": list(ALL_CHANS),
        "selection": "PTOFamps range only; no low-pass, no fit, no channel-completeness filter",
        "n_selected_rows": selection["n_selected_rows"],
        "n_selected_unique": selection["n_selected_unique"],
        "n_found_unique": len(seen_events),
        "selected_event_numbers": selection["event_numbers"],
        "found_event_numbers": sorted(seen_events),
        "missing_event_numbers": [event for event in selection["event_numbers"] if event not in seen_events],
        "selected_ptofamps": selection["ptofamps"],
        "selected_trigger_types": selection["trigger_types"],
        "raw_traces": raw_traces,
        "event_numbers_ch": event_numbers_ch,
        "ptofamps_ch": ptofamps_ch,
        "baselines_ch": baselines_ch,
        "event_stats": event_stats,
        "created_at": datetime.datetime.now().isoformat(),
    }


def atomic_save(payload, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "wb") as handle:
        pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp_path, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--det", type=int, required=True)
    parser.add_argument("--series", nargs="*", default=None)
    parser.add_argument("--cache-dir", default=CACHE_DIR_DEFAULT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    det = args.det
    if det not in PTOF_RANGES:
        raise ValueError(f"zip{det} not in PTOF_RANGES")

    excluded = set(SERIES_EXCLUSIONS.get(det, []))
    series_list = [series for series in ALL_SERIES if series not in excluded]
    if args.series:
        requested = set(args.series)
        unknown = sorted(requested - set(ALL_SERIES))
        if unknown:
            raise ValueError(f"unknown series: {unknown}")
        series_list = [series for series in series_list if series in requested]

    ptof_lo, ptof_hi = PTOF_RANGES[det]
    output_dir = os.path.join(args.cache_dir, f"zip{det}_series")
    os.makedirs(output_dir, exist_ok=True)

    print(f"=== zip{det} raw PTOF-selected event cache ===")
    print(f"PTOFamps range : [{ptof_lo:.3e}, {ptof_hi:.3e}]")
    print(f"Output dir     : {output_dir}")
    print(f"Series count   : {len(series_list)}")
    if args.dry_run:
        print("*** DRY RUN: no files will be written ***")

    n_written = n_skipped = n_no_selection = 0
    for series in series_list:
        output_path = os.path.join(output_dir, f"{series}.pkl")
        if os.path.exists(output_path) and not args.overwrite:
            print(f"  {series}: exists, skip ({output_path})")
            n_skipped += 1
            continue

        selection = select_events_for_series(det, series, ptof_lo, ptof_hi)
        if not selection or not selection["event_numbers"]:
            n_no_selection += 1
            continue

        if args.dry_run:
            n_written += 1
            continue

        payload = build_payload_from_raw(det, series, selection)
        if payload is None:
            continue
        atomic_save(payload, output_path)
        print(f"  {series}: saved {output_path}")
        n_written += 1

    print("\n=== summary ===")
    print(f"written_or_would_write : {n_written}")
    print(f"skipped_existing       : {n_skipped}")
    print(f"no_selection           : {n_no_selection}")


if __name__ == "__main__":
    main()
