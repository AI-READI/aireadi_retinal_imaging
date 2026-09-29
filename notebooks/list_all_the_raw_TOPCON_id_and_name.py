import csv
import os
import sys
import time
from multiprocessing import Pool

import pydicom
from tqdm import tqdm

ROOT = r"F:\raw\maestro2"
OUT_CSV = "dicom_ids_for_m2.csv"  # or for triton, any csv name that is applicable
WORKERS = os.cpu_count()


def read(args):
    """Read PatientID and PatientName from a DICOM header, plus its two parent folder levels."""
    p, root = args
    try:
        # Read only the needed tags, skip pixel data for speed
        ds = pydicom.dcmread(p, stop_before_pixels=True, specific_tags=["PatientID", "PatientName"])
    except Exception:
        return None  # not a DICOM or unreadable -> skip
    # Folder levels relative to root: root/<batch_folder>/<sub_folder>/file
    parts = os.path.relpath(os.path.dirname(p), root).split(os.sep) + ["", ""]
    return str(ds.get("PatientID", "")), str(ds.get("PatientName", "")), parts[0], parts[1]


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else ROOT
    if not os.path.isdir(root):
        sys.exit(f"Folder not found: {root}")

    # Collect all file paths under root
    t0 = time.time()
    files = []
    for d, _, fs in tqdm(os.walk(root), desc="Scanning folders", unit=" folders"):
        files += [os.path.join(d, f) for f in fs]
    print(f"Total files: {len(files)}  ({time.time() - t0:.1f}s)")

    # Read DICOM headers in parallel across all CPU cores
    with Pool(WORKERS) as pool:
        results = list(tqdm(
            pool.imap_unordered(read, ((p, root) for p in files), chunksize=64),
            total=len(files), desc="Reading DICOMs"))

    ok = [r for r in results if r]
    rows = set(ok)  # remove duplicate rows
    print(f"DICOMs read    : {len(ok)}")
    print(f"Skipped        : {len(files) - len(ok)}")
    print(f"Patients       : {len({r[0] for r in rows})}")
    print(f"Batches        : {len({r[2] for r in rows})}")
    print(f"Unique rows    : {len(rows)}")

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["patient_id", "patient_name", "batch_folder", "sub_folder"])
        w.writerows(sorted(rows))

    print(f"Done -> {OUT_CSV}  (total {time.time() - t0:.1f}s)")
    for r in sorted(rows)[:5]:
        print(r)


if __name__ == "__main__":
    main()